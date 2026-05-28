"""
Servicio de procesamiento de audio: extrae biomarcadores acústicos de Parkinson.

Responsabilidad única: dado un buffer de bytes de audio, devuelve el vector de
biomarcadores y la lista de variables que no pudieron calcularse.

El manejo de estado (DB) y el control de flujo del pipeline son responsabilidad
exclusiva de audio_pipeline.py.
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import librosa
    import librosa.core
    import librosa.feature
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logging.warning("Librosa no está disponible. El procesamiento de audio será limitado.")

try:
    import parselmouth
    PRAAT_AVAILABLE = True
except ImportError:
    PRAAT_AVAILABLE = False
    logging.warning("Parselmouth (Praat) no está disponible. El análisis avanzado de voz será limitado.")

try:
    import scipy
    import scipy.signal
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logging.warning("SciPy no está disponible. El procesamiento de señales será limitado.")

from app.services.audio_utils import decode_audio_bytes
from app.services.constants import PARKINSON_FEATURE_ORDER
from app.services.nonlinear_features import compute_nonlinear_features

logger = logging.getLogger(__name__)


class AudioProcessingError(Exception):
    """Excepción para errores de procesamiento de audio."""
    pass


def extract_features_from_audio(
    audio_bytes: bytes,
    sample_rate: int = 22050,
    source_name: Optional[str] = None,
) -> Tuple[Dict[str, float], List[str]]:
    """
    Extrae biomarcadores acústicos de Parkinson desde bytes de audio.

    Retorna
    -------
    features : Dict[str, float]
        Biomarcadores calculados con éxito.
    missing : List[str]
        Nombres de las variables que no pudieron calcularse.
        El llamador decide si rechazar la muestra, marcarla como parcial
        o continuar con inferencia explícitamente parcial.
    """
    if not LIBROSA_AVAILABLE:
        raise AudioProcessingError("Librosa es requerido para extraer biomarcadores de audio")

    y, sr = decode_audio_bytes(audio_bytes, source_name=source_name, sample_rate=sample_rate)

    duration = librosa.get_duration(y=y, sr=sr)
    if duration < 0.5:
        raise AudioProcessingError(f"Audio demasiado corto: {duration:.2f}s; mínimo requerido: 0.5s")

    f0 = extract_fundamental_frequency(y, sr)
    if f0 is None or len(f0) == 0:
        raise AudioProcessingError("No se pudo extraer la frecuencia fundamental del audio")

    jitter_features = calculate_jitter(f0, sr)
    shimmer_features = calculate_shimmer(y, f0, sr)
    hnr_features = calculate_hnr(y, sr)
    nonlinear_features, missing_nonlinear = compute_nonlinear_features(y=y, f0=f0)

    features: Dict[str, float] = {
        "MDVP:Fo(Hz)": float(np.nanmedian(f0)) if len(f0) > 0 else 0.0,
        "MDVP:Fhi(Hz)": float(np.nanmax(f0)) if len(f0) > 0 else 0.0,
        "MDVP:Flo(Hz)": float(np.nanmin(f0)) if len(f0) > 0 else 0.0,
        **jitter_features,
        **shimmer_features,
        **hnr_features,
        **nonlinear_features,
    }

    # Detectar qué variables del esquema completo no están en el dict.
    missing_features = missing_nonlinear + [
        f for f in PARKINSON_FEATURE_ORDER
        if f not in features and f not in missing_nonlinear
    ]

    if missing_features:
        logger.warning("Biomarcadores no calculados: %s", missing_features)

    return features, missing_features


def extract_fundamental_frequency(
    y: np.ndarray, sr: int, fmin: float = 75.0, fmax: float = 300.0
) -> np.ndarray:
    """
    Extrae F0 con estrategia escalonada: pYIN → Praat → autocorrelación.

    Registra qué ruta fue usada para facilitar auditoría.
    """
    # Método 1: pYIN (librosa) — ruta principal.
    if LIBROSA_AVAILABLE:
        try:
            f0_pyin, _, _ = librosa.pyin(
                y,
                fmin=fmin,
                fmax=fmax,
                sr=sr,
                frame_length=2048,
                hop_length=512,
                fill_na=np.nan,
            )
            if f0_pyin is not None:
                valid = f0_pyin[~np.isnan(f0_pyin)]
                if len(valid) > 0:
                    logger.debug("F0 extraída con pYIN (%d frames válidos)", len(valid))
                    return valid
        except Exception as exc:
            logger.debug("pYIN falló: %s", exc)

    # Método 2: Parselmouth/Praat — respaldo clínico recomendado.
    if PRAAT_AVAILABLE:
        try:
            sound = parselmouth.Sound(y, sr)
            pitch = sound.to_pitch(time_step=0.01, pitch_floor=fmin, pitch_ceiling=fmax)
            f0_praat = pitch.selected_array["frequency"]
            f0_praat[f0_praat == 0] = np.nan
            valid = f0_praat[~np.isnan(f0_praat)]
            if len(valid) > 0:
                logger.debug("F0 extraída con Praat (%d frames válidos)", len(valid))
                return valid
        except Exception as exc:
            logger.debug("Praat falló: %s", exc)

    # Método 3: autocorrelación — último recurso.
    if SCIPY_AVAILABLE:
        try:
            frame_length = 2048
            hop_length = 512
            f0_ac = []
            for i in range(0, len(y) - frame_length, hop_length):
                frame = y[i : i + frame_length] * np.hanning(frame_length)
                autocorr = np.correlate(frame, frame, mode="full")
                autocorr = autocorr[autocorr.size // 2 :]
                peaks, _ = scipy.signal.find_peaks(autocorr[: len(autocorr) // 2])
                if len(peaks) > 0 and peaks[0] > 0:
                    f0_frame = sr / peaks[0]
                    f0_ac.append(f0_frame if fmin <= f0_frame <= fmax else np.nan)
                else:
                    f0_ac.append(np.nan)
            arr = np.array(f0_ac)
            valid = arr[~np.isnan(arr)]
            if len(valid) > 0:
                logger.debug("F0 extraída con autocorrelación (%d frames válidos)", len(valid))
                return valid
        except Exception as exc:
            logger.debug("Autocorrelación falló: %s", exc)

    logger.warning("No se pudo extraer F0 con ningún método disponible")
    return np.array([])


def calculate_jitter(f0: np.ndarray, sr: int) -> Dict[str, float]:
    """Calcula biomarcadores de jitter (perturbación de pitch)."""
    zeros: Dict[str, float] = {
        "MDVP:Jitter(%)": 0.0,
        "MDVP:Jitter(Abs)": 0.0,
        "MDVP:RAP": 0.0,
        "MDVP:PPQ": 0.0,
        "Jitter:DDP": 0.0,
    }

    f0_clean = f0[~np.isnan(f0)] if len(f0) >= 2 else np.array([])
    if len(f0_clean) < 2:
        return zeros

    diffs = np.abs(np.diff(f0_clean))
    mean_f0 = np.mean(f0_clean)
    if mean_f0 <= 0:
        return zeros

    jitter_percent = (np.mean(diffs) / mean_f0) * 100
    jitter_abs = np.mean(diffs)

    rap = 0.0
    if len(f0_clean) >= 3:
        rap_values = [
            np.abs(f0_clean[i] - np.mean(f0_clean[i - 1 : i + 2]))
            for i in range(1, len(f0_clean) - 1)
        ]
        rap = np.mean(rap_values) / mean_f0 * 100

    ppq = 0.0
    if len(f0_clean) >= 5:
        ppq_values = [
            np.abs(f0_clean[i] - np.mean(f0_clean[i - 2 : i + 3]))
            for i in range(2, len(f0_clean) - 2)
        ]
        ppq = np.mean(ppq_values) / mean_f0 * 100

    ddp = 0.0
    if len(diffs) >= 2:
        ddp = np.mean(np.abs(np.diff(diffs))) / mean_f0 * 100

    return {
        "MDVP:Jitter(%)": float(jitter_percent),
        "MDVP:Jitter(Abs)": float(jitter_abs),
        "MDVP:RAP": float(rap),
        "MDVP:PPQ": float(ppq),
        "Jitter:DDP": float(ddp),
    }


def calculate_shimmer(y: np.ndarray, f0: np.ndarray, sr: int) -> Dict[str, float]:
    """Calcula biomarcadores de shimmer (perturbación de amplitud)."""
    zeros: Dict[str, float] = {
        "MDVP:Shimmer": 0.0,
        "MDVP:Shimmer(dB)": 0.0,
        "Shimmer:APQ3": 0.0,
        "Shimmer:APQ5": 0.0,
        "MDVP:APQ": 0.0,
        "Shimmer:DDA": 0.0,
    }

    f0_clean = f0[~np.isnan(f0)] if len(f0) >= 2 else np.array([])
    if len(f0_clean) < 2 or len(y) < sr * 0.1:
        return zeros

    periods = (sr / f0_clean).astype(int)
    periods = periods[(periods > 0) & (periods < len(y) // 2)]
    if len(periods) < 2:
        return zeros

    amplitudes = []
    start_idx = 0
    for period in periods:
        if start_idx + period >= len(y):
            break
        window = y[start_idx : start_idx + period]
        if len(window) > 0:
            amplitudes.append(np.max(np.abs(window)))
        start_idx += period

    amplitudes = np.array(amplitudes)
    if len(amplitudes) < 2:
        return zeros

    amp_diffs = np.abs(np.diff(amplitudes))
    mean_amp = np.mean(amplitudes)
    if mean_amp <= 0:
        return zeros

    shimmer = (np.mean(amp_diffs) / mean_amp) * 100
    shimmer_db = 20 * np.log10(1 + shimmer / 100) if shimmer > 0 else 0.0

    apq3 = 0.0
    if len(amplitudes) >= 3:
        apq3 = np.mean([
            np.abs(amplitudes[i] - np.mean(amplitudes[i - 1 : i + 2]))
            for i in range(1, len(amplitudes) - 1)
        ]) / mean_amp * 100

    apq5 = 0.0
    if len(amplitudes) >= 5:
        apq5 = np.mean([
            np.abs(amplitudes[i] - np.mean(amplitudes[i - 2 : i + 3]))
            for i in range(2, len(amplitudes) - 2)
        ]) / mean_amp * 100

    dda = 0.0
    if len(amp_diffs) >= 2:
        dda = np.mean(np.abs(np.diff(amp_diffs))) / mean_amp * 100

    return {
        "MDVP:Shimmer": float(shimmer),
        "MDVP:Shimmer(dB)": float(shimmer_db),
        "Shimmer:APQ3": float(apq3),
        "Shimmer:APQ5": float(apq5),
        "MDVP:APQ": float(apq5),  # APQ11 aproximado con APQ5
        "Shimmer:DDA": float(dda),
    }


def calculate_hnr(y: np.ndarray, sr: int) -> Dict[str, float]:
    """Calcula NHR y HNR mediante análisis cepstral."""
    try:
        spectrum = np.abs(np.fft.rfft(y))
        log_spectrum = np.log(spectrum + 1e-10)
        cepstrum = np.abs(np.fft.irfft(log_spectrum))
        quefrencies = np.arange(len(cepstrum)) / sr

        mask = (quefrencies >= 1 / 400) & (quefrencies <= 1 / 80)
        if np.any(mask):
            cepstrum_range = cepstrum[mask]
            peak_value = cepstrum_range[np.argmax(cepstrum_range)]
            total_energy = np.sum(cepstrum_range ** 2)
            harmonic_energy = peak_value ** 2
            noise_energy = total_energy - harmonic_energy

            if noise_energy > 0:
                nhr = noise_energy / harmonic_energy
                hnr = 10 * np.log10(harmonic_energy / noise_energy)
            else:
                nhr = 0.0
                hnr = 100.0
        else:
            nhr, hnr = 1.0, 0.0
    except Exception as exc:
        logger.debug("Cálculo de HNR falló: %s", exc)
        nhr, hnr = 1.0, 0.0

    return {"NHR": float(nhr), "HNR": float(hnr)}

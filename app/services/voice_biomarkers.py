"""
Servicio de extracción de biomarcadores de voz para integración MVP de Parkinson.

Este módulo provee un pipeline ligero de preprocesamiento + Parselmouth
que normaliza audio cargado a mono/16 kHz/WAV y extrae un conjunto pequeño
de biomarcadores de voz sin alterar el flujo general de persistencia de audio.
"""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np
import soundfile as sf
from parselmouth import Sound
from parselmouth.praat import call

try:
    import librosa

    LIBROSA_AVAILABLE = True
except ImportError:  # pragma: no cover - dependency is declared in requirements.txt
    LIBROSA_AVAILABLE = False

try:
    from pydub import AudioSegment

    PYDUB_AVAILABLE = True
except ImportError:  # pragma: no cover - dependency is declared in requirements.txt
    PYDUB_AVAILABLE = False

from app.model_predict import PARK_FEATURE_ORDER, predict_parkinson
from app.services.audio_processing import AudioProcessingError, extract_features_from_audio
from app.utils.validators import validate_required_features

TARGET_SAMPLE_RATE_HZ = 16000
TARGET_CHANNELS = 1
TARGET_WAV_FORMAT = "wav"
DEFAULT_PITCH_FLOOR_HZ = 75.0
DEFAULT_PITCH_CEILING_HZ = 300.0
PARKINSON_MODEL_FILENAME = "parkinsons_model.sav"
PARKINSON_POSITIVE_MESSAGE = "La persona puede tener Parkinson, consulte a su médico."
PARKINSON_NEGATIVE_MESSAGE = "La persona no tiene Parkinson."
MIN_PERIOD_SECONDS = 0.0001
MAX_PERIOD_SECONDS = 0.02
MAX_PERIOD_FACTOR = 1.3
MAX_AMPLITUDE_FACTOR = 1.6

logger = logging.getLogger(__name__)


class VoiceBiomarkerError(Exception):
    """Se lanza cuando el audio de entrada no puede convertirse o analizarse."""


@dataclass
class PreparedVoiceAudio:
    """Audio normalizado listo para análisis con Parselmouth."""

    temp_wav_path: str
    sample_rate_hz: int
    channels: int
    duration_seconds: float


def _guess_suffix(source_name: Optional[str]) -> str:
    if not source_name:
        return ".wav"

    suffix = os.path.splitext(source_name)[1].lower().strip()
    return suffix if suffix else ".wav"


def _decode_audio_bytes(
    audio_bytes: bytes,
    source_name: Optional[str],
    sample_rate_hz: int,
) -> Tuple[np.ndarray, int]:
    if not LIBROSA_AVAILABLE:
        raise VoiceBiomarkerError("librosa es requerido para decodificar el audio cargado.")

    suffix = _guess_suffix(source_name)

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_input:
        temp_input.write(audio_bytes)
        temp_input_path = temp_input.name

    try:
        try:
            waveform, sr = librosa.load(temp_input_path, sr=sample_rate_hz, mono=True)
            return waveform, sr
        except Exception as decode_error:
            if not PYDUB_AVAILABLE:
                raise VoiceBiomarkerError(f"No se pudo decodificar el audio: {decode_error}") from decode_error

            try:
                segment = AudioSegment.from_file(temp_input_path)
                segment = segment.set_frame_rate(sample_rate_hz).set_channels(TARGET_CHANNELS)
                samples = np.array(segment.get_array_of_samples(), dtype=np.float32)

                if samples.size == 0:
                    raise VoiceBiomarkerError("El audio cargado no contiene muestras legibles.")

                scale = float(1 << (8 * segment.sample_width - 1))
                if scale > 0:
                    samples /= scale

                return samples, segment.frame_rate
            except Exception as pydub_error:
                raise VoiceBiomarkerError(f"No se pudo decodificar el audio: {pydub_error}") from decode_error
    finally:
        try:
            os.remove(temp_input_path)
        except OSError:
            pass


def prepare_audio_for_voice_biomarkers(
    audio_bytes: bytes,
    source_name: Optional[str] = None,
) -> PreparedVoiceAudio:
    """Normaliza el audio cargado a mono/16 kHz y persiste un WAV temporal."""

    if not audio_bytes:
        raise VoiceBiomarkerError("El archivo de audio cargado está vacío.")

    waveform, sample_rate_hz = _decode_audio_bytes(
        audio_bytes=audio_bytes,
        source_name=source_name,
        sample_rate_hz=TARGET_SAMPLE_RATE_HZ,
    )

    if waveform.size == 0:
        raise VoiceBiomarkerError("El audio cargado no contiene datos de forma de onda válidos.")

    duration_seconds = float(len(waveform) / sample_rate_hz)
    if duration_seconds <= 0:
        raise VoiceBiomarkerError("El audio cargado tiene una duración inválida.")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
        temp_wav_path = temp_wav.name

    sf.write(temp_wav_path, waveform, sample_rate_hz, format="WAV", subtype="PCM_16")

    return PreparedVoiceAudio(
        temp_wav_path=temp_wav_path,
        sample_rate_hz=sample_rate_hz,
        channels=TARGET_CHANNELS,
        duration_seconds=duration_seconds,
    )


def cleanup_prepared_audio(prepared_audio: Optional[PreparedVoiceAudio]) -> None:
    """Elimina el WAV temporal creado durante el preprocesamiento."""

    if not prepared_audio:
        return

    try:
        os.remove(prepared_audio.temp_wav_path)
    except OSError:
        pass


def _read_normalized_audio_bytes(prepared_audio: PreparedVoiceAudio) -> bytes:
    try:
        with open(prepared_audio.temp_wav_path, "rb") as temp_wav:
            return temp_wav.read()
    except OSError as exc:
        raise VoiceBiomarkerError(f"No se pudo leer el audio normalizado para análisis: {exc}") from exc


def _ensure_finite_metric(value: float, metric_name: str) -> float:
    metric_value = float(value)
    if not np.isfinite(metric_value):
        raise VoiceBiomarkerError(
            f"No se pudo calcular un valor estable para '{metric_name}' desde el audio cargado."
        )
    return metric_value


def extract_voice_biomarkers(
    prepared_audio: PreparedVoiceAudio,
    pitch_floor_hz: float = DEFAULT_PITCH_FLOOR_HZ,
    pitch_ceiling_hz: float = DEFAULT_PITCH_CEILING_HZ,
) -> Dict[str, float]:
    """Extrae los biomarcadores Parselmouth solicitados desde audio WAV normalizado."""

    try:
        sound = Sound(prepared_audio.temp_wav_path)
        pitch = sound.to_pitch(
            pitch_floor=pitch_floor_hz,
            pitch_ceiling=pitch_ceiling_hz,
        )
        pitch_values = pitch.selected_array["frequency"]
        voiced_pitch = pitch_values[pitch_values > 0]

        if voiced_pitch.size == 0:
            raise VoiceBiomarkerError(
                "No se detectaron tramas con voz. Cargue una muestra de voz más clara."
            )

        point_process = call(sound, "To PointProcess (periodic, cc)", pitch_floor_hz, pitch_ceiling_hz)
        harmonicity = call(sound, "To Harmonicity (cc)", 0.01, pitch_floor_hz, 0.1, 1.0)

        biomarkers = {
            "pitch_mean": _ensure_finite_metric(np.mean(voiced_pitch), "pitch_mean"),
            "pitch_min": _ensure_finite_metric(np.min(voiced_pitch), "pitch_min"),
            "pitch_max": _ensure_finite_metric(np.max(voiced_pitch), "pitch_max"),
            "jitter_local": _ensure_finite_metric(
                call(point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3),
                "jitter_local",
            ),
            "shimmer_local": _ensure_finite_metric(
                call([sound, point_process], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6),
                "shimmer_local",
            ),
            "hnr_mean": _ensure_finite_metric(
                call(harmonicity, "Get mean", 0, 0),
                "hnr_mean",
            ),
        }
    except VoiceBiomarkerError:
        raise
    except Exception as exc:
        raise VoiceBiomarkerError(f"No se pudieron extraer biomarcadores de voz: {exc}") from exc

    return biomarkers


def extract_parkinson_model_features(prepared_audio: PreparedVoiceAudio) -> Dict[str, float]:
    """
    Construye el vector completo de 22 características de Parkinson desde el audio normalizado.

    Reutiliza el extractor actual del proyecto para mantener la inferencia directa
    alineada con el contrato del modelo de Parkinson existente.
    """

    return build_parkinson_features_parselmouth_primary(prepared_audio)


def extract_parkinson_core_features(
    prepared_audio: PreparedVoiceAudio,
    pitch_floor_hz: float = DEFAULT_PITCH_FLOOR_HZ,
    pitch_ceiling_hz: float = DEFAULT_PITCH_CEILING_HZ,
) -> Dict[str, float]:
    """
    Extract clinically relevant Parkinson features using Parselmouth as primary source.
    """
    try:
        sound = Sound(prepared_audio.temp_wav_path)
        pitch = sound.to_pitch(
            pitch_floor=pitch_floor_hz,
            pitch_ceiling=pitch_ceiling_hz,
        )
        pitch_values = pitch.selected_array["frequency"]
        voiced_pitch = pitch_values[pitch_values > 0]
        if voiced_pitch.size == 0:
            raise VoiceBiomarkerError(
                "No voiced frames were detected. Please upload a clearer voice sample."
            )

        point_process = call(sound, "To PointProcess (periodic, cc)", pitch_floor_hz, pitch_ceiling_hz)
        harmonicity = call(sound, "To Harmonicity (cc)", 0.01, pitch_floor_hz, 0.1, 1.0)

        jitter_local = _ensure_finite_metric(
            call(
                point_process,
                "Get jitter (local)",
                0,
                0,
                MIN_PERIOD_SECONDS,
                MAX_PERIOD_SECONDS,
                MAX_PERIOD_FACTOR,
            ),
            "MDVP:Jitter(%)",
        )
        jitter_abs = _ensure_finite_metric(
            call(
                point_process,
                "Get jitter (local, absolute)",
                0,
                0,
                MIN_PERIOD_SECONDS,
                MAX_PERIOD_SECONDS,
                MAX_PERIOD_FACTOR,
            ),
            "MDVP:Jitter(Abs)",
        )
        jitter_rap = _ensure_finite_metric(
            call(
                point_process,
                "Get jitter (rap)",
                0,
                0,
                MIN_PERIOD_SECONDS,
                MAX_PERIOD_SECONDS,
                MAX_PERIOD_FACTOR,
            ),
            "MDVP:RAP",
        )
        jitter_ppq5 = _ensure_finite_metric(
            call(
                point_process,
                "Get jitter (ppq5)",
                0,
                0,
                MIN_PERIOD_SECONDS,
                MAX_PERIOD_SECONDS,
                MAX_PERIOD_FACTOR,
            ),
            "MDVP:PPQ",
        )

        shimmer_local = _ensure_finite_metric(
            call(
                [sound, point_process],
                "Get shimmer (local)",
                0,
                0,
                MIN_PERIOD_SECONDS,
                MAX_PERIOD_SECONDS,
                MAX_PERIOD_FACTOR,
                MAX_AMPLITUDE_FACTOR,
            ),
            "MDVP:Shimmer",
        )
        shimmer_db = _ensure_finite_metric(
            call(
                [sound, point_process],
                "Get shimmer (local_dB)",
                0,
                0,
                MIN_PERIOD_SECONDS,
                MAX_PERIOD_SECONDS,
                MAX_PERIOD_FACTOR,
                MAX_AMPLITUDE_FACTOR,
            ),
            "MDVP:Shimmer(dB)",
        )
        shimmer_apq3 = _ensure_finite_metric(
            call(
                [sound, point_process],
                "Get shimmer (apq3)",
                0,
                0,
                MIN_PERIOD_SECONDS,
                MAX_PERIOD_SECONDS,
                MAX_PERIOD_FACTOR,
                MAX_AMPLITUDE_FACTOR,
            ),
            "Shimmer:APQ3",
        )
        shimmer_apq5 = _ensure_finite_metric(
            call(
                [sound, point_process],
                "Get shimmer (apq5)",
                0,
                0,
                MIN_PERIOD_SECONDS,
                MAX_PERIOD_SECONDS,
                MAX_PERIOD_FACTOR,
                MAX_AMPLITUDE_FACTOR,
            ),
            "Shimmer:APQ5",
        )
        shimmer_apq11 = _ensure_finite_metric(
            call(
                [sound, point_process],
                "Get shimmer (apq11)",
                0,
                0,
                MIN_PERIOD_SECONDS,
                MAX_PERIOD_SECONDS,
                MAX_PERIOD_FACTOR,
                MAX_AMPLITUDE_FACTOR,
            ),
            "MDVP:APQ",
        )
        hnr = _ensure_finite_metric(
            call(harmonicity, "Get mean", 0, 0),
            "HNR",
        )
    except VoiceBiomarkerError:
        raise
    except Exception as exc:
        raise VoiceBiomarkerError(f"Failed to extract Parselmouth core Parkinson features: {exc}") from exc

    nhr = 10 ** (-hnr / 10.0) if np.isfinite(hnr) else float("nan")
    return {
        "MDVP:Fo(Hz)": _ensure_finite_metric(np.mean(voiced_pitch), "MDVP:Fo(Hz)"),
        "MDVP:Fhi(Hz)": _ensure_finite_metric(np.max(voiced_pitch), "MDVP:Fhi(Hz)"),
        "MDVP:Flo(Hz)": _ensure_finite_metric(np.min(voiced_pitch), "MDVP:Flo(Hz)"),
        # Parselmouth returns jitter local as a ratio; the model expects percentage.
        "MDVP:Jitter(%)": float(jitter_local * 100.0),
        "MDVP:Jitter(Abs)": float(jitter_abs),
        "MDVP:RAP": float(jitter_rap),
        "MDVP:PPQ": float(jitter_ppq5),
        "Jitter:DDP": float(jitter_rap * 3.0),
        # Parselmouth local shimmer is also a ratio; convert to percentage.
        "MDVP:Shimmer": float(shimmer_local * 100.0),
        "MDVP:Shimmer(dB)": float(shimmer_db),
        "Shimmer:APQ3": float(shimmer_apq3),
        "Shimmer:APQ5": float(shimmer_apq5),
        "MDVP:APQ": float(shimmer_apq11),
        "Shimmer:DDA": float(shimmer_apq3 * 3.0),
        "NHR": float(nhr),
        "HNR": float(hnr),
    }


def build_parkinson_features_parselmouth_primary(prepared_audio: PreparedVoiceAudio) -> Dict[str, float]:
    """
    Build a 22-feature Parkinson vector where clinically key perturbation/noise
    metrics come from Parselmouth and remaining features are completed by the
    support extractor.
    """
    try:
        core_features = extract_parkinson_core_features(prepared_audio)
        normalized_audio_bytes = _read_normalized_audio_bytes(prepared_audio)
        support_features = extract_features_from_audio(
            normalized_audio_bytes,
            sample_rate=prepared_audio.sample_rate_hz,
            source_name="normalized.wav",
        )
    except AudioProcessingError as exc:
        raise VoiceBiomarkerError(f"Failed to extract Parkinson model features: {exc}") from exc
    except ValueError as exc:
        raise VoiceBiomarkerError(f"Incomplete Parkinson model feature vector: {exc}") from exc
    except Exception as exc:
        raise VoiceBiomarkerError(f"No se pudo construir el vector del modelo de Parkinson: {exc}") from exc

    merged_features = dict(support_features)
    merged_features.update(core_features)

    # Explicitly mark missing features as non-finite so inference validation can decide.
    for feature in PARK_FEATURE_ORDER:
        if feature not in merged_features:
            merged_features[feature] = float("nan")
            logger.warning("Feature %s missing after Parselmouth-first extraction", feature)

    validate_required_features(merged_features, PARK_FEATURE_ORDER)
    return {feature: float(merged_features[feature]) for feature in PARK_FEATURE_ORDER}


def build_parkinson_model_bridge(biomarkers: Dict[str, float]) -> Dict[str, object]:
    """
    Construye una carga puente conservadora hacia el modelo actual de Parkinson.

    El modelo actual espera el vector Oxford completo de 22 características.
    Este puente expone solo el subconjunto directamente mapeable desde los
    biomarcadores solicitados y deja el resto explícito como faltante.
    """

    mapped_features = {
        "MDVP:Fo(Hz)": biomarkers["pitch_mean"],
        "MDVP:Fhi(Hz)": biomarkers["pitch_max"],
        "MDVP:Flo(Hz)": biomarkers["pitch_min"],
        "HNR": biomarkers["hnr_mean"],
    }

    missing_features = [feature for feature in PARK_FEATURE_ORDER if feature not in mapped_features]

    return {
        "model_name": PARKINSON_MODEL_FILENAME,
        "mapped_features": mapped_features,
        "missing_features": missing_features,
        "ready_for_direct_inference": len(missing_features) == 0,
        "note": (
            "Este puente parcial mapea solo los biomarcadores Parselmouth solicitados. "
            "La inferencia directa requiere el vector completo de 22 características de Parkinson."
        ),
    }


def build_parkinson_model_input(features: Dict[str, float]) -> Dict[str, object]:
    return {
        "model_name": PARKINSON_MODEL_FILENAME,
        "features": {feature: float(features[feature]) for feature in PARK_FEATURE_ORDER},
        "feature_count": len(features),
        "required_feature_count": len(PARK_FEATURE_ORDER),
        "ready_for_direct_inference": True,
        "note": (
            "Este vector de características se genera desde el audio normalizado usando "
            "el mismo servicio de extracción que alimenta el pipeline actual de Parkinson."
        ),
    }


def run_parkinson_direct_inference(features: Dict[str, float]) -> Dict[str, object]:
    try:
        prediction, probability = predict_parkinson(features)
    except Exception as exc:
        raise VoiceBiomarkerError(f"No se pudo ejecutar la inferencia de Parkinson: {exc}") from exc

    return {
        "model_name": PARKINSON_MODEL_FILENAME,
        "disease_code": "PARK",
        "prediction": int(prediction),
        "probability": float(probability),
        "message": PARKINSON_POSITIVE_MESSAGE if prediction == 1 else PARKINSON_NEGATIVE_MESSAGE,
    }

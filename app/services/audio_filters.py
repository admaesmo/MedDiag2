"""
Preprocesamiento DSP para señales de voz orientadas a biomarcadores de Parkinson.

Cascada de operaciones (orden fijo):
  1. Filtro paso-alto  — elimina rumble, ruido grave y DC offset implícito
  2. Filtro paso-bajo  — elimina ruido de alta frecuencia irrelevante para la voz
  3. VAD (trim)        — recorta silencios de inicio/fin para aislar la fonación
  4. Normalización RMS — homogeneiza amplitud sin introducir distorsión por clipping

Parámetros acordados:
  - High-pass : 70 Hz, Butterworth orden 4, fase cero (sosfiltfilt)
  - Low-pass  : 5000 Hz, Butterworth orden 4, fase cero (sosfiltfilt)
  - VAD       : librosa.effects.trim, top_db=40
  - Ganancia  : limitada por RMS objetivo Y por pico máximo (sin clip posterior)
"""

from __future__ import annotations

import logging
from typing import Tuple

import numpy as np
import scipy.signal as signal

try:
    import librosa
    _LIBROSA_AVAILABLE = True
except ImportError:
    _LIBROSA_AVAILABLE = False

logger = logging.getLogger(__name__)

# Longitud mínima que sosfiltfilt necesita para el padding interno.
# Para orden 4 (2 secciones SOS): padlen = 3 * (2*2*2 - 1) = 21.
# En la práctica nunca se alcanza (QC garantiza ≥ 0.8 s), pero protege
# contra llamadas directas a apply_bandpass_filters con señales muy cortas.
_MIN_FILTER_SAMPLES = 22


class AudioPreprocessorError(Exception):
    pass


class AudioPreprocessor:
    """
    Preprocesador DSP configurable para señales de voz.

    Diseñado para uso con vocales sostenidas /a/ y biomarcadores acústicos
    del dataset UCI Oxford Parkinson (22 variables).
    """

    def __init__(
        self,
        sr: int,
        highpass_fc: float = 70.0,
        lowpass_fc: float = 5000.0,
        filter_order: int = 4,
    ) -> None:
        """
        Parameters
        ----------
        sr : int
            Tasa de muestreo de la señal de entrada (Hz).
        highpass_fc : float
            Frecuencia de corte del filtro paso-alto (Hz).
            70 Hz da margen sobre fmin=75 Hz de pYIN/Praat para voces graves
            con Parkinson (bradifonía documentada hasta ~70-75 Hz).
        lowpass_fc : float
            Frecuencia de corte del filtro paso-bajo (Hz).
            5000 Hz conserva todos los formantes relevantes (F1-F3 de /a/ < 3 kHz)
            y armónicos útiles para medidas de disfonía.
        filter_order : int
            Orden del filtro Butterworth (efectivo 2× con sosfiltfilt).
        """
        if sr <= 0:
            raise AudioPreprocessorError(f"Tasa de muestreo inválida: {sr}")

        self.sr = sr
        self.nyquist = sr / 2.0

        if highpass_fc >= self.nyquist:
            raise AudioPreprocessorError(
                f"fc paso-alto ({highpass_fc} Hz) ≥ Nyquist ({self.nyquist} Hz)"
            )
        if lowpass_fc >= self.nyquist:
            raise AudioPreprocessorError(
                f"fc paso-bajo ({lowpass_fc} Hz) ≥ Nyquist ({self.nyquist} Hz)"
            )
        if highpass_fc >= lowpass_fc:
            raise AudioPreprocessorError(
                f"fc paso-alto ({highpass_fc} Hz) debe ser menor que fc paso-bajo ({lowpass_fc} Hz)"
            )

        self.highpass_fc = highpass_fc
        self.lowpass_fc = lowpass_fc
        self.filter_order = filter_order

        # Pre-diseñar filtros en formato SOS (numericamente estable para orden ≥ 3)
        self._sos_hp = signal.butter(
            filter_order, highpass_fc / self.nyquist, btype="high", output="sos"
        )
        self._sos_lp = signal.butter(
            filter_order, lowpass_fc / self.nyquist, btype="low", output="sos"
        )

        logger.debug(
            "AudioPreprocessor listo: sr=%d Hz, HP=%.0f Hz, LP=%.0f Hz, orden=%d (efectivo %d con sosfiltfilt)",
            sr, highpass_fc, lowpass_fc, filter_order, filter_order * 2,
        )

    # ------------------------------------------------------------------
    # Paso 1 — Filtrado paso banda
    # ------------------------------------------------------------------

    def apply_bandpass_filters(self, y: np.ndarray) -> np.ndarray:
        """
        Aplica HP y LP en cascada con fase cero (sosfiltfilt).

        sosfiltfilt filtra hacia adelante y hacia atrás, eliminando
        completamente el desfase de fase. Esto preserva la alineación
        temporal de los ciclos de pitch, crítica para Jitter.

        El HP a 70 Hz elimina implícitamente el DC offset (0 Hz queda
        a -∞ dB respecto al corte), por lo que no se necesita un paso
        adicional de resta de media.
        """
        if len(y) < _MIN_FILTER_SAMPLES:
            logger.warning(
                "Señal demasiado corta (%d muestras) para filtrar; se devuelve sin cambios.",
                len(y),
            )
            return y

        y_hp = signal.sosfiltfilt(self._sos_hp, y)
        y_bp = signal.sosfiltfilt(self._sos_lp, y_hp)
        return y_bp

    # ------------------------------------------------------------------
    # Paso 2 — VAD (Voice Activity Detection) por trim
    # ------------------------------------------------------------------

    def apply_vad_trim(
        self,
        y: np.ndarray,
        top_db: float = 40.0,
    ) -> np.ndarray:
        """
        Recorta silencios de inicio y fin usando umbral energético.

        Para vocales sostenidas /a/, el patrón habitual es:
          [silencio] → [ataque] → [fonación estable] → [decaimiento] → [silencio]
        El trim elimina las regiones externas sin modificar la fonación interna.

        top_db=40 significa: recortar tramas con energía ≥ 40 dB por debajo
        del máximo de la señal. Es más conservador que el default de librosa
        (60 dB) para no perder ataques suaves.
        """
        if not _LIBROSA_AVAILABLE:
            logger.warning("Librosa no disponible; VAD omitido.")
            return y

        if len(y) == 0:
            return y

        y_trimmed, _ = librosa.effects.trim(y, top_db=top_db, frame_length=2048, hop_length=512)

        reduction_pct = (1.0 - len(y_trimmed) / max(len(y), 1)) * 100
        logger.debug(
            "VAD trim: %d → %d muestras (%.1f%% recortado)",
            len(y), len(y_trimmed), reduction_pct,
        )
        return y_trimmed

    # ------------------------------------------------------------------
    # Paso 3 — Normalización RMS adaptativa (sin clipping)
    # ------------------------------------------------------------------

    def normalize_rms(
        self,
        y: np.ndarray,
        target_rms: float = 0.1,
        max_gain: float = 10.0,
        peak_limit: float = 0.95,
    ) -> np.ndarray:
        """
        Normaliza la amplitud de la señal sin introducir distorsión por clipping.

        La ganancia final es la más restrictiva entre tres límites:
          - gain_rms  : ganancia para alcanzar target_rms
          - gain_peak : ganancia máxima que mantiene el pico bajo peak_limit
          - max_gain  : techo absoluto (evita amplificar ruido en grabaciones
                        extremadamente silenciosas)

        Al limitar por pico en lugar de clipear después, se preserva la forma
        de onda original y no se introducen armónicos espurios que afectarían
        HNR, D2 y PPE.
        """
        if len(y) == 0:
            return y

        current_rms = float(np.sqrt(np.mean(y ** 2)))
        if current_rms < 1e-12:
            logger.warning("RMS de la señal es prácticamente cero; normalización omitida.")
            return y

        current_peak = float(np.max(np.abs(y)))

        gain_rms = target_rms / current_rms
        gain_peak = peak_limit / current_peak if current_peak > 0 else max_gain
        gain = min(gain_rms, gain_peak, max_gain)

        logger.debug(
            "Normalización: gain_rms=%.2f, gain_peak=%.2f → gain_final=%.2f",
            gain_rms, gain_peak, gain,
        )
        return y * gain

    # ------------------------------------------------------------------
    # Pipeline completo
    # ------------------------------------------------------------------

    def preprocess(
        self,
        y: np.ndarray,
        apply_vad: bool = True,
        vad_top_db: float = 40.0,
        target_rms: float = 0.1,
        max_gain: float = 10.0,
        peak_limit: float = 0.95,
        min_duration_s: float = 0.5,
    ) -> np.ndarray:
        """
        Cascada completa: filtros → VAD → normalización.

        Parameters
        ----------
        y : np.ndarray
            Señal de entrada decodificada (mono, float32).
        apply_vad : bool
            Si False, omite el paso de VAD (útil para pruebas).
        vad_top_db : float
            Umbral VAD en dB debajo del pico (40 = conservador).
        target_rms : float
            Valor RMS objetivo post-normalización.
        max_gain : float
            Ganancia máxima permitida.
        peak_limit : float
            Amplitud de pico máxima permitida post-normalización.
        min_duration_s : float
            Duración mínima de señal útil tras VAD para continuar.

        Returns
        -------
        np.ndarray
            Señal preprocesada lista para extracción de biomarcadores.

        Raises
        ------
        AudioPreprocessorError
            Si la señal de entrada está vacía o el resultado del VAD
            es más corto que min_duration_s.
        """
        if len(y) == 0:
            raise AudioPreprocessorError("La señal de entrada está vacía.")

        # 1. Filtrado paso banda (elimina ruido fuera de la banda vocal)
        y = self.apply_bandpass_filters(y)

        # 2. VAD: recortar silencios de inicio/fin
        if apply_vad:
            y = self.apply_vad_trim(y, top_db=vad_top_db)

        # 3. Validar duración mínima del segmento vocal
        duration_s = len(y) / self.sr
        if duration_s < min_duration_s:
            raise AudioPreprocessorError(
                f"Señal vocal útil insuficiente tras VAD: {duration_s:.2f}s "
                f"(mínimo requerido: {min_duration_s}s). "
                "Verifique que el audio contenga fonación activa."
            )

        # 4. Normalización RMS sobre el segmento vocal (no sobre silencios)
        y = self.normalize_rms(
            y,
            target_rms=target_rms,
            max_gain=max_gain,
            peak_limit=peak_limit,
        )

        final_rms = float(np.sqrt(np.mean(y ** 2)))
        logger.debug(
            "Preprocesamiento completo: %.2f s, RMS=%.4f",
            len(y) / self.sr, final_rms,
        )
        return y

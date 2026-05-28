"""
Servicio de extracción de biomarcadores de voz para integración MVP de Parkinson.

Este módulo provee un pipeline ligero de preprocesamiento + Parselmouth
que normaliza audio cargado a mono/16 kHz/WAV y extrae un conjunto pequeño
de biomarcadores de voz sin alterar el flujo general de persistencia de audio.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np
import soundfile as sf
from parselmouth import Sound
from parselmouth.praat import call

from app.model_predict import (
    PARK_FEATURE_ORDER,
    predict_parkinson,
)
from app.services.audio_processing import AudioProcessingError, extract_features_from_audio
from app.services.audio_utils import decode_audio_bytes

TARGET_SAMPLE_RATE_HZ = 16000
TARGET_CHANNELS = 1
TARGET_WAV_FORMAT = "wav"
DEFAULT_PITCH_FLOOR_HZ = 75.0
DEFAULT_PITCH_CEILING_HZ = 300.0
PARKINSON_MODEL_FILENAME = "parkinsons_model.sav"
PARKINSON_POSITIVE_MESSAGE = "La persona puede tener Parkinson, consulte a su médico."
PARKINSON_NEGATIVE_MESSAGE = "La persona no tiene Parkinson."


class VoiceBiomarkerError(Exception):
    """Se lanza cuando el audio de entrada no puede convertirse o analizarse."""


@dataclass
class PreparedVoiceAudio:
    """Audio normalizado listo para análisis con Parselmouth."""

    temp_wav_path: str
    sample_rate_hz: int
    channels: int
    duration_seconds: float


def prepare_audio_for_voice_biomarkers(
    audio_bytes: bytes,
    source_name: Optional[str] = None,
) -> PreparedVoiceAudio:
    """Normaliza el audio cargado a mono/16 kHz y persiste un WAV temporal."""

    if not audio_bytes:
        raise VoiceBiomarkerError("El archivo de audio cargado está vacío.")

    try:
        waveform, sample_rate_hz = decode_audio_bytes(
            audio_bytes=audio_bytes,
            source_name=source_name,
            sample_rate=TARGET_SAMPLE_RATE_HZ,
        )
    except Exception as exc:
        raise VoiceBiomarkerError(f"No se pudo decodificar el audio: {exc}") from exc

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

    try:
        normalized_audio_bytes = _read_normalized_audio_bytes(prepared_audio)
        features, missing = extract_features_from_audio(
            normalized_audio_bytes,
            sample_rate=prepared_audio.sample_rate_hz,
            source_name="normalized.wav",
        )
        if missing:
            raise ValueError(f"Features no calculadas: {missing}")
    except AudioProcessingError as exc:
        raise VoiceBiomarkerError(f"No se pudieron extraer características para el modelo de Parkinson: {exc}") from exc
    except ValueError as exc:
        raise VoiceBiomarkerError(f"Vector incompleto para el modelo de Parkinson: {exc}") from exc
    except Exception as exc:
        raise VoiceBiomarkerError(f"No se pudo construir el vector del modelo de Parkinson: {exc}") from exc

    return {feature: float(features[feature]) for feature in PARK_FEATURE_ORDER}


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


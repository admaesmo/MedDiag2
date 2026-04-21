"""
Voice biomarker extraction service for Parkinson MVP integration.

This module provides a lightweight audio preprocessing + Parselmouth pipeline
that normalizes uploaded audio to mono/16 kHz/WAV and extracts a small set of
voice biomarkers without altering the broader audio persistence workflow.
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

from app.model_predict import PARK_FEATURE_ORDER

TARGET_SAMPLE_RATE_HZ = 16000
TARGET_CHANNELS = 1
TARGET_WAV_FORMAT = "wav"
DEFAULT_PITCH_FLOOR_HZ = 75.0
DEFAULT_PITCH_CEILING_HZ = 300.0


class VoiceBiomarkerError(Exception):
    """Raised when the input audio cannot be converted or analyzed."""


@dataclass
class PreparedVoiceAudio:
    """Normalized audio ready for Parselmouth analysis."""

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
        raise VoiceBiomarkerError("librosa is required to decode uploaded audio.")

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
                raise VoiceBiomarkerError(f"Failed to decode audio: {decode_error}") from decode_error

            try:
                segment = AudioSegment.from_file(temp_input_path)
                segment = segment.set_frame_rate(sample_rate_hz).set_channels(TARGET_CHANNELS)
                samples = np.array(segment.get_array_of_samples(), dtype=np.float32)

                if samples.size == 0:
                    raise VoiceBiomarkerError("The uploaded audio does not contain readable samples.")

                scale = float(1 << (8 * segment.sample_width - 1))
                if scale > 0:
                    samples /= scale

                return samples, segment.frame_rate
            except Exception as pydub_error:
                raise VoiceBiomarkerError(f"Failed to decode audio: {pydub_error}") from decode_error
    finally:
        try:
            os.remove(temp_input_path)
        except OSError:
            pass


def prepare_audio_for_voice_biomarkers(
    audio_bytes: bytes,
    source_name: Optional[str] = None,
) -> PreparedVoiceAudio:
    """Normalize uploaded audio to mono/16 kHz and persist a temporary WAV file."""

    if not audio_bytes:
        raise VoiceBiomarkerError("The uploaded audio file is empty.")

    waveform, sample_rate_hz = _decode_audio_bytes(
        audio_bytes=audio_bytes,
        source_name=source_name,
        sample_rate_hz=TARGET_SAMPLE_RATE_HZ,
    )

    if waveform.size == 0:
        raise VoiceBiomarkerError("The uploaded audio does not contain valid waveform data.")

    duration_seconds = float(len(waveform) / sample_rate_hz)
    if duration_seconds <= 0:
        raise VoiceBiomarkerError("The uploaded audio has an invalid duration.")

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
    """Delete the temporary WAV file created during preprocessing."""

    if not prepared_audio:
        return

    try:
        os.remove(prepared_audio.temp_wav_path)
    except OSError:
        pass


def _ensure_finite_metric(value: float, metric_name: str) -> float:
    metric_value = float(value)
    if not np.isfinite(metric_value):
        raise VoiceBiomarkerError(
            f"Could not compute a stable value for '{metric_name}' from the uploaded audio."
        )
    return metric_value


def extract_voice_biomarkers(
    prepared_audio: PreparedVoiceAudio,
    pitch_floor_hz: float = DEFAULT_PITCH_FLOOR_HZ,
    pitch_ceiling_hz: float = DEFAULT_PITCH_CEILING_HZ,
) -> Dict[str, float]:
    """Extract the requested Parselmouth biomarkers from normalized WAV audio."""

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
        raise VoiceBiomarkerError(f"Failed to extract voice biomarkers: {exc}") from exc

    return biomarkers


def build_parkinson_model_bridge(biomarkers: Dict[str, float]) -> Dict[str, object]:
    """
    Build a conservative bridge payload toward the current Parkinson model.

    The current model still expects the full 22-feature Oxford vector. This
    bridge exposes only the directly mappable subset from the requested
    biomarker set and leaves the rest explicit as missing.
    """

    mapped_features = {
        "MDVP:Fo(Hz)": biomarkers["pitch_mean"],
        "MDVP:Fhi(Hz)": biomarkers["pitch_max"],
        "MDVP:Flo(Hz)": biomarkers["pitch_min"],
        "HNR": biomarkers["hnr_mean"],
    }

    missing_features = [feature for feature in PARK_FEATURE_ORDER if feature not in mapped_features]

    return {
        "model_name": "parkinsons_model.sav",
        "mapped_features": mapped_features,
        "missing_features": missing_features,
        "ready_for_direct_inference": len(missing_features) == 0,
        "note": (
            "This endpoint extracts the requested six Parselmouth biomarkers. "
            "The current Parkinson model still requires the complete 22-feature vector."
        ),
    }

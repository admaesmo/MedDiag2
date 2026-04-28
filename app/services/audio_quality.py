"""
Quality control for normalized voice audio before biomarker extraction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import soundfile as sf
from sqlalchemy.orm import Session

from app.models import AudioQualityReport
from app.services.voice_biomarkers import PreparedVoiceAudio

MIN_DURATION_SECONDS = 0.5
MIN_RMS = 0.005
MAX_CLIPPING_RATIO = 0.05
MAX_SILENCE_RATIO = 0.80
MIN_VALID_QUALITY_SCORE = 0.65
MIN_LOW_QUALITY_SCORE = 0.45


class AudioQualityError(Exception):
    """Raised when audio quality cannot be evaluated."""


@dataclass
class AudioQualityResult:
    quality_score: float
    is_valid: bool
    quality_status: str
    noise_level: float
    clipping: float
    silence_ratio: float
    rms: float
    peak_amplitude: float
    stability_score: float
    rejection_reason: Optional[str]
    metrics: Dict[str, float]


def analyze_audio_quality(prepared_audio: PreparedVoiceAudio) -> AudioQualityResult:
    """Evaluate basic quality gates over the normalized WAV used downstream."""

    try:
        waveform, sample_rate = sf.read(prepared_audio.temp_wav_path, dtype="float32", always_2d=False)
    except Exception as exc:
        raise AudioQualityError(f"Failed to read normalized audio for quality control: {exc}") from exc

    if waveform.size == 0:
        raise AudioQualityError("Normalized audio does not contain samples.")

    if waveform.ndim > 1:
        waveform = np.mean(waveform, axis=1)

    waveform = np.asarray(waveform, dtype=np.float32)
    abs_waveform = np.abs(waveform)
    rms = float(np.sqrt(np.mean(np.square(waveform))))
    peak_amplitude = float(np.max(abs_waveform))
    clipping = float(np.mean(abs_waveform >= 0.98))
    silence_threshold = max(MIN_RMS * 0.6, peak_amplitude * 0.02)
    silence_ratio = float(np.mean(abs_waveform < silence_threshold))
    noise_level = _estimate_noise_level(waveform)
    stability_score = _estimate_stability_score(waveform, sample_rate)

    penalties = [
        _linear_penalty(prepared_audio.duration_seconds, MIN_DURATION_SECONDS, MIN_DURATION_SECONDS * 4),
        _linear_penalty(rms, MIN_RMS, MIN_RMS * 8),
        1.0 - min(clipping / MAX_CLIPPING_RATIO, 1.0),
        1.0 - min(silence_ratio / MAX_SILENCE_RATIO, 1.0),
        stability_score,
    ]
    quality_score = float(np.clip(np.mean(penalties), 0.0, 1.0))

    rejection_reason = _build_rejection_reason(
        duration_seconds=prepared_audio.duration_seconds,
        rms=rms,
        clipping=clipping,
        silence_ratio=silence_ratio,
        quality_score=quality_score,
    )

    if rejection_reason:
        quality_status = "invalid"
        is_valid = False
    elif quality_score < MIN_VALID_QUALITY_SCORE:
        quality_status = "low_quality"
        is_valid = False
        rejection_reason = "Audio quality score is below the inference threshold."
    else:
        quality_status = "valid"
        is_valid = True

    metrics = {
        "duration_seconds": float(prepared_audio.duration_seconds),
        "sample_rate_hz": float(prepared_audio.sample_rate_hz),
        "channels": float(prepared_audio.channels),
        "min_duration_seconds": float(MIN_DURATION_SECONDS),
        "min_rms": float(MIN_RMS),
        "max_clipping_ratio": float(MAX_CLIPPING_RATIO),
        "max_silence_ratio": float(MAX_SILENCE_RATIO),
        "min_valid_quality_score": float(MIN_VALID_QUALITY_SCORE),
        "min_low_quality_score": float(MIN_LOW_QUALITY_SCORE),
    }

    return AudioQualityResult(
        quality_score=quality_score,
        is_valid=is_valid,
        quality_status=quality_status,
        noise_level=noise_level,
        clipping=clipping,
        silence_ratio=silence_ratio,
        rms=rms,
        peak_amplitude=peak_amplitude,
        stability_score=stability_score,
        rejection_reason=rejection_reason,
        metrics=metrics,
    )


def store_audio_quality_report(
    db: Session,
    audio_record_id: int,
    quality: AudioQualityResult,
) -> AudioQualityReport:
    report = AudioQualityReport(
        audio_record_id=audio_record_id,
        quality_score=quality.quality_score,
        is_valid=quality.is_valid,
        quality_status=quality.quality_status,
        noise_level=quality.noise_level,
        clipping=quality.clipping,
        silence_ratio=quality.silence_ratio,
        rms=quality.rms,
        peak_amplitude=quality.peak_amplitude,
        stability_score=quality.stability_score,
        rejection_reason=quality.rejection_reason,
        metrics_json=quality.metrics,
    )
    db.add(report)
    db.flush()
    return report


def get_latest_audio_quality_report(db: Session, audio_record_id: int) -> Optional[AudioQualityReport]:
    return (
        db.query(AudioQualityReport)
        .filter(AudioQualityReport.audio_record_id == audio_record_id)
        .order_by(AudioQualityReport.created_at.desc(), AudioQualityReport.id.desc())
        .first()
    )


def _estimate_noise_level(waveform: np.ndarray) -> float:
    if waveform.size < 2:
        return 0.0
    high_frequency_delta = np.diff(waveform)
    return float(np.median(np.abs(high_frequency_delta)))


def _estimate_stability_score(waveform: np.ndarray, sample_rate: int) -> float:
    frame_length = max(int(sample_rate * 0.10), 1)
    if waveform.size < frame_length:
        return 0.0

    frame_rms_values = []
    for start in range(0, waveform.size - frame_length + 1, frame_length):
        frame = waveform[start : start + frame_length]
        frame_rms_values.append(float(np.sqrt(np.mean(np.square(frame)))))

    frame_rms = np.asarray(frame_rms_values, dtype=np.float32)
    voiced = frame_rms[frame_rms > MIN_RMS]
    if voiced.size < 2:
        return 0.0

    coefficient_variation = float(np.std(voiced) / max(np.mean(voiced), 1e-8))
    return float(np.clip(1.0 - coefficient_variation, 0.0, 1.0))


def _linear_penalty(value: float, minimum: float, target: float) -> float:
    if value <= minimum:
        return 0.0
    if value >= target:
        return 1.0
    return float((value - minimum) / (target - minimum))


def _build_rejection_reason(
    duration_seconds: float,
    rms: float,
    clipping: float,
    silence_ratio: float,
    quality_score: float,
) -> Optional[str]:
    reasons = []
    if duration_seconds < MIN_DURATION_SECONDS:
        reasons.append(f"Audio too short: {duration_seconds:.2f}s.")
    if rms < MIN_RMS:
        reasons.append("Audio level is too low.")
    if clipping > MAX_CLIPPING_RATIO:
        reasons.append("Audio has excessive clipping.")
    if silence_ratio > MAX_SILENCE_RATIO:
        reasons.append("Audio contains too much silence.")
    if quality_score < MIN_LOW_QUALITY_SCORE:
        reasons.append("Audio quality score is too low.")
    return " ".join(reasons) if reasons else None

"""
Quality Control Service — audio signal validation gate.

Analyses raw audio for:
  - Duration validity
  - Clipping (peak saturation)
  - RMS energy
  - Signal-to-noise ratio (SNR)
  - Silence ratio
  - Noise floor
  - Occupied bandwidth

Produces an AudioQualityReport that must pass before biomarker extraction.
"""

from __future__ import annotations

import io
import logging
import tempfile
from typing import Optional

import numpy as np

from sqlalchemy.orm import Session

from app.models import AudioRecord, AudioQualityReport
from app.schemas.quality_control import QualityControlResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tunable thresholds  (could be promoted to settings / env vars)
# ---------------------------------------------------------------------------

MIN_DURATION_S = 0.8          # seconds
MAX_CLIPPING_RATIO = 0.01     # 1 % of samples clipped → reject
MIN_RMS = 0.005               # below this → too quiet / mostly silence
MAX_SILENCE_RATIO = 0.60      # 60 % near-zero → reject
MIN_SNR_DB = 10.0             # below 10 dB → too noisy
CLIP_THRESHOLD = 0.98         # |sample| >= threshold → clipping candidate


def _load_audio_from_record(audio_record: AudioRecord) -> tuple[np.ndarray, int]:
    """Load and decode a WAV audio file from storage into (samples, sample_rate)."""
    from app.services.storage_service import get_storage_backend

    backend = get_storage_backend()
    audio_bytes = backend.load(audio_record.storage_path)
    if not audio_bytes:
        raise RuntimeError(f"Cannot load audio from {audio_record.storage_path}")

    try:
        import librosa
        y, sr = librosa.load(io.BytesIO(audio_bytes), sr=None, mono=True)
        return y, sr
    except Exception:
        # Fallback: try pydub
        try:
            from pydub import AudioSegment
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            seg = AudioSegment.from_file(tmp_path)
            import os
            os.remove(tmp_path)
            seg = seg.set_channels(1)
            y = np.array(seg.get_array_of_samples()).astype(np.float32)
            scale = float(1 << (8 * seg.sample_width - 1))
            if scale > 0:
                y /= scale
            return y, seg.frame_rate
        except Exception as exc:
            raise RuntimeError(f"Cannot decode audio: {exc}")


def _compute_snr(y: np.ndarray, sr: int, frame_ms: int = 30) -> Optional[float]:
    """Estimate SNR via voice-activity heuristic (energy percentile split)."""
    frame_len = int(sr * frame_ms / 1000)
    if len(y) < frame_len * 2:
        return None

    frames = y[: (len(y) // frame_len) * frame_len].reshape(-1, frame_len)
    rms_per_frame = np.sqrt(np.mean(frames ** 2, axis=1))

    if rms_per_frame.size < 4:
        return None

    # Bottom 25 % frames → noise floor estimate
    noise_frames = rms_per_frame[np.argsort(rms_per_frame)[: max(1, rms_per_frame.size // 4)]]
    noise_rms = float(np.mean(noise_frames)) + 1e-12

    # Top 25 % frames → signal
    signal_frames = rms_per_frame[np.argsort(-rms_per_frame)[: max(1, rms_per_frame.size // 4)]]
    signal_rms = float(np.mean(signal_frames))

    ratio = signal_rms / noise_rms
    if ratio <= 0:
        return None
    return 20.0 * np.log10(ratio)


def _compute_bandwidth(y: np.ndarray, sr: int, energy_fraction: float = 0.95) -> float:
    """Estimate the frequency band containing *energy_fraction* of total energy."""
    spec = np.abs(np.fft.rfft(y))
    power = spec ** 2
    total = np.sum(power)
    if total <= 0:
        return 0.0

    cumsum = np.cumsum(power)
    cutoff_idx = int(np.searchsorted(cumsum, total * energy_fraction))
    freqs = np.fft.rfftfreq(len(y), d=1.0 / sr)
    if cutoff_idx < len(freqs):
        return float(freqs[cutoff_idx])
    return float(freqs[-1]) if len(freqs) > 0 else 0.0


def analyse_audio(audio_record: AudioRecord) -> QualityControlResult:
    """
    Run quality checks on *audio_record* and return a structured result.

    Steps performed:
      1. Load & decode audio
      2. Measure duration, RMS, peak, clipping
      3. Estimate SNR
      4. Measure silence ratio, noise floor, bandwidth
      5. Combine into a pass/fail verdict with score
    """
    y, sr = _load_audio_from_record(audio_record)
    duration_s = float(len(y)) / sr

    # --- Basic metrics ---
    rms = float(np.sqrt(np.mean(y ** 2)))
    peak = float(np.max(np.abs(y)))
    clipping_mask = np.abs(y) >= CLIP_THRESHOLD
    clipping_count = int(np.sum(clipping_mask))
    clipping_ratio = clipping_count / max(len(y), 1)

    # --- Silence ratio (frames with RMS < 1 % of peak) ---
    frame_len = int(sr * 0.020)  # 20 ms frames
    if frame_len < 1:
        frame_len = max(1, len(y) // 100)
    frames = y[: (len(y) // frame_len) * frame_len].reshape(-1, frame_len)
    frame_rms = np.sqrt(np.mean(frames ** 2, axis=1))
    silence_threshold = 0.01 * (peak + 1e-12)
    silence_ratio = float(np.mean(frame_rms < silence_threshold))

    # --- SNR ---
    snr_db = _compute_snr(y, sr)

    # --- Noise floor (dB) ---
    noise_floor_db = float(20.0 * np.log10(np.percentile(np.abs(y), 5) + 1e-12))

    # --- Bandwidth ---
    bw = _compute_bandwidth(y, sr)

    # --- Scoring logic ---
    score = 1.0
    reasons: list[str] = []

    # Duration
    if duration_s < MIN_DURATION_S:
        reasons.append(f"Duration {duration_s:.2f}s < min {MIN_DURATION_S}s")
    else:
        score *= min(1.0, duration_s / 3.0)  # penalise very short recordings

    # Clipping
    if clipping_ratio > MAX_CLIPPING_RATIO:
        reasons.append(f"Clipping ratio {clipping_ratio:.4f} > max {MAX_CLIPPING_RATIO}")
        score *= 0.0  # hard reject
    elif clipping_ratio > 0:
        score *= (1.0 - clipping_ratio * 5.0)

    # RMS (too quiet)
    if rms < MIN_RMS:
        reasons.append(f"RMS energy {rms:.5f} < min {MIN_RMS}")
        score *= max(0.0, rms / MIN_RMS)

    # Silence ratio
    if silence_ratio > MAX_SILENCE_RATIO:
        reasons.append(f"Silence ratio {silence_ratio:.3f} > max {MAX_SILENCE_RATIO}")
        score *= 0.0  # hard reject
    else:
        score *= (1.0 - silence_ratio * 0.5)

    # SNR
    if snr_db is not None and snr_db < MIN_SNR_DB:
        reasons.append(f"SNR {snr_db:.1f} dB < min {MIN_SNR_DB} dB")
        score *= max(0.0, snr_db / MIN_SNR_DB)

    # Clip score to [0, 1]
    score = max(0.0, min(1.0, score))

    is_valid = len(reasons) == 0 or score >= 0.3
    rejection_reason = "; ".join(reasons) if reasons else None

    return QualityControlResult(
        is_valid=is_valid,
        quality_score=round(score, 4),
        rejection_reason=rejection_reason,
        duration_seconds=duration_s,
        rms_energy=float(rms),
        peak_amplitude=float(peak),
        clipping_detected=clipping_ratio > 0,
        clipping_ratio=clipping_ratio,
        snr_db=round(snr_db, 2) if snr_db is not None else None,
        silence_ratio=silence_ratio,
        noise_floor_db=round(noise_floor_db, 2),
        bandwidth_hz=round(bw, 1),
    )


def run_quality_check(db: Session, audio_record_id: int) -> AudioQualityReport:
    """
    Full quality-control round-trip: analyse → persist → update status.

    Returns the persisted AudioQualityReport row.
    """
    record = db.query(AudioRecord).filter(AudioRecord.id == audio_record_id).first()
    if not record:
        raise ValueError(f"AudioRecord {audio_record_id} not found")

    result = analyse_audio(record)

    report = AudioQualityReport(
        audio_record_id=audio_record_id,
        is_valid=result.is_valid,
        quality_score=result.quality_score,
        rejection_reason=result.rejection_reason,
        duration_seconds=result.duration_seconds,
        rms_energy=result.rms_energy,
        peak_amplitude=result.peak_amplitude,
        clipping_detected=result.clipping_detected,
        clipping_ratio=result.clipping_ratio,
        snr_db=result.snr_db,
        silence_ratio=result.silence_ratio,
        noise_floor_db=result.noise_floor_db,
        bandwidth_hz=result.bandwidth_hz,
    )
    db.add(report)

    # Update audio-record status
    if result.is_valid:
        record.status = "quality_checked"
    else:
        record.status = "rejected"
    db.commit()
    db.refresh(report)
    return report


def get_latest_quality_report(db: Session, audio_record_id: int) -> Optional[AudioQualityReport]:
    """Return the most recent QC report for an audio record."""
    return (
        db.query(AudioQualityReport)
        .filter(AudioQualityReport.audio_record_id == audio_record_id)
        .order_by(AudioQualityReport.created_at.desc())
        .first()
    )

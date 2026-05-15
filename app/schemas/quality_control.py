"""
Schemas de QA/QC para reportes de control de calidad de audio.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class QualityControlReportOut(BaseModel):
    """Forma pública de un AudioQualityReport."""
    id: int
    audio_record_id: int
    is_valid: bool
    quality_score: Optional[float] = None
    rejection_reason: Optional[str] = None

    duration_seconds: Optional[float] = None
    rms_energy: Optional[float] = None
    peak_amplitude: Optional[float] = None
    clipping_detected: bool = False
    clipping_ratio: Optional[float] = None
    snr_db: Optional[float] = None
    silence_ratio: Optional[float] = None
    noise_floor_db: Optional[float] = None
    bandwidth_hz: Optional[float] = None

    created_at: datetime

    class Config:
        from_attributes = True


class QualityControlResult(BaseModel):
    """Resultado devuelto por QA/QC después de analizar un audio."""
    is_valid: bool
    quality_score: float
    rejection_reason: Optional[str] = None

    duration_seconds: float
    rms_energy: float
    peak_amplitude: float
    clipping_detected: bool
    clipping_ratio: float
    snr_db: Optional[float] = None
    silence_ratio: float
    noise_floor_db: float
    bandwidth_hz: float

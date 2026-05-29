"""Schemas Pydantic para sesiones de voz (múltiples tomas)."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class VoiceSessionCreate(BaseModel):
    max_takes: int = Field(default=3, ge=2, le=5)


class TakeSummary(BaseModel):
    audio_record_id: int
    take_number: int
    status: str
    quality_score: Optional[float] = None
    is_valid: Optional[bool] = None
    rejection_reason: Optional[str] = None


class VoiceSessionOut(BaseModel):
    id: int
    uuid: str
    user_id: int
    max_takes: int
    status: str
    valid_takes_count: Optional[int] = None
    session_confidence: Optional[float] = None
    diagnosis_id: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    takes: List[TakeSummary] = []

    class Config:
        from_attributes = True


class SessionAnalysisResult(BaseModel):
    session_id: int
    session_uuid: str
    status: str
    valid_takes_count: int
    session_confidence: float
    aggregated_features: Dict[str, float]
    variance_per_feature: Dict[str, float]
    diagnosis_id: int
    prediction: str
    probability: float
    message: str

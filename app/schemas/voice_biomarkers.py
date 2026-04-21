"""
Schemas for the lightweight voice biomarker extraction endpoint.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class VoiceBiomarkerSet(BaseModel):
    pitch_mean: float = Field(..., description="Mean voiced pitch in Hz.")
    pitch_min: float = Field(..., description="Minimum voiced pitch in Hz.")
    pitch_max: float = Field(..., description="Maximum voiced pitch in Hz.")
    jitter_local: float = Field(..., description="Parselmouth local jitter.")
    shimmer_local: float = Field(..., description="Parselmouth local shimmer.")
    hnr_mean: float = Field(..., description="Mean harmonics-to-noise ratio from Parselmouth.")


class VoiceBiomarkerAudioMetadata(BaseModel):
    original_filename: Optional[str] = None
    content_type: Optional[str] = None
    sample_rate_hz: int
    channels: int
    normalized_format: str
    duration_seconds: float


class ParkinsonModelBridgeResponse(BaseModel):
    model_name: str
    mapped_features: Dict[str, float]
    missing_features: List[str]
    ready_for_direct_inference: bool
    note: str


class VoiceBiomarkerExtractionResponse(BaseModel):
    status: str = "success"
    audio: VoiceBiomarkerAudioMetadata
    biomarkers: VoiceBiomarkerSet
    parkinson_model_bridge: ParkinsonModelBridgeResponse

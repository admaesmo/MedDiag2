"""
Schemas para el endpoint ligero de extracción de biomarcadores de voz.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class VoiceBiomarkerSet(BaseModel):
    pitch_mean: float = Field(..., description="Pitch sonoro medio en Hz.")
    pitch_min: float = Field(..., description="Pitch sonoro mínimo en Hz.")
    pitch_max: float = Field(..., description="Pitch sonoro máximo en Hz.")
    jitter_local: float = Field(..., description="Jitter local calculado con Parselmouth.")
    shimmer_local: float = Field(..., description="Shimmer local calculado con Parselmouth.")
    hnr_mean: float = Field(
        ...,
        description="Relación media armónicos-ruido calculada con Parselmouth.",
    )


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


class ParkinsonModelInputResponse(BaseModel):
    model_name: str
    features: Dict[str, float]
    feature_count: int
    required_feature_count: int
    ready_for_direct_inference: bool
    note: str


class ParkinsonInferenceResponse(BaseModel):
    model_name: str
    disease_code: str
    prediction: int
    probability: float
    message: str


class VoiceBiomarkerExtractionResponse(BaseModel):
    status: str = "success"
    audio: VoiceBiomarkerAudioMetadata
    biomarkers: VoiceBiomarkerSet
    parkinson_model_bridge: ParkinsonModelBridgeResponse
    parkinson_model_input: ParkinsonModelInputResponse
    parkinson_inference: ParkinsonInferenceResponse

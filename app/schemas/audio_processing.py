"""
Audio processing schemas for API responses.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel


class AudioProcessingRequest(BaseModel):
    """Request schema for audio processing."""
    audio_id: int
    process_immediately: bool = True


class AudioProcessingResponse(BaseModel):
    """Response schema for audio processing."""
    audio_record_id: int
    status: str  # success, already_processed, failed
    features: Optional[Dict[str, float]] = None
    diagnosis_id: Optional[int] = None
    prediction: Optional[str] = None
    probability: Optional[float] = None
    message: Optional[str] = None
    error: Optional[str] = None


class BatchProcessingRequest(BaseModel):
    """Request schema for batch audio processing."""
    limit: int = 10
    process_all: bool = False


class BatchProcessingResult(BaseModel):
    """Single result in batch processing."""
    audio_record_id: int
    status: str
    error: Optional[str] = None
    features: Optional[Dict[str, float]] = None
    diagnosis_id: Optional[int] = None


class BatchProcessingResponse(BaseModel):
    """Response schema for batch audio processing."""
    results: List[BatchProcessingResult]
    total_processed: int
    successful: int
    failed: int


class AudioAnalysisSummary(BaseModel):
    """Summary of audio analysis for a user."""
    total_audio_records: int
    status_counts: Dict[str, int]
    recent_diagnoses: List[Dict[str, Any]]
    processed_features_summary: List[Dict[str, Any]]


class AudioFeatureExtraction(BaseModel):
    """Extracted audio features for Parkinson's detection."""
    # Fundamental frequency features
    mdvp_fo_hz: Optional[float] = None  # MDVP:Fo(Hz)
    mdvp_fhi_hz: Optional[float] = None  # MDVP:Fhi(Hz)
    mdvp_flo_hz: Optional[float] = None  # MDVP:Flo(Hz)
    
    # Jitter features
    mdvp_jitter_percent: Optional[float] = None  # MDVP:Jitter(%)
    mdvp_jitter_abs: Optional[float] = None  # MDVP:Jitter(Abs)
    mdvp_rap: Optional[float] = None  # MDVP:RAP
    mdvp_ppq: Optional[float] = None  # MDVP:PPQ
    jitter_ddp: Optional[float] = None  # Jitter:DDP
    
    # Shimmer features
    mdvp_shimmer: Optional[float] = None  # MDVP:Shimmer
    mdvp_shimmer_db: Optional[float] = None  # MDVP:Shimmer(dB)
    shimmer_apq3: Optional[float] = None  # Shimmer:APQ3
    shimmer_apq5: Optional[float] = None  # Shimmer:APQ5
    mdvp_apq: Optional[float] = None  # MDVP:APQ
    shimmer_dda: Optional[float] = None  # Shimmer:DDA
    
    # Noise features
    nhr: Optional[float] = None  # NHR
    hnr: Optional[float] = None  # HNR
    
    # Nonlinear dynamics features
    rpde: Optional[float] = None  # RPDE
    dfa: Optional[float] = None  # DFA
    spread1: Optional[float] = None  # spread1
    spread2: Optional[float] = None  # spread2
    d2: Optional[float] = None  # D2
    ppe: Optional[float] = None  # PPE
    
    class Config:
        from_attributes = True
        json_encoders = {
            float: lambda v: round(v, 6) if v is not None else None
        }


class AudioProcessingStatus(BaseModel):
    """Status of audio processing."""
    audio_id: int
    status: str  # uploaded, processing, processed, failed
    progress_percentage: Optional[int] = None
    estimated_time_remaining: Optional[int] = None  # seconds
    features_extracted: Optional[bool] = None
    prediction_completed: Optional[bool] = None
    created_at: datetime
    updated_at: datetime
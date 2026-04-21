from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class AudioUploadResponse(BaseModel):
    audio_id: int
    uuid: str
    status: str
    original_filename: Optional[str] = None
    mime_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AudioRecordOut(BaseModel):
    id: int
    uuid: str
    user_id: int
    source_type: Optional[str] = None
    original_filename: Optional[str] = None
    mime_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    duration_seconds: Optional[float] = None
    language_code: Optional[str] = None
    status: str
    transcript_text: Optional[str] = None
    notes: Optional[str] = None
    is_ready_for_inference: bool = False
    processing_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AudioListResponse(BaseModel):
    items: List[AudioRecordOut]
    total: int

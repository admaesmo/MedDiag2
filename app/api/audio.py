"""
Audio endpoints — upload, list, detail, delete.
"""

import json
import os

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models import User, UserRole
from app.schemas.audio import AudioListResponse, AudioRecordOut, AudioUploadResponse
from app.services.auth_service import get_current_user, get_db
from app.services import audio_service
from app.utils.database import SessionLocal

router = APIRouter(prefix="/audio", tags=["audio"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_admin(db: Session, user: User) -> bool:
    return any(
        ur.role.code == "admin"
        for ur in db.query(UserRole).filter(UserRole.user_id == user.id).all()
    )


def _is_ready_status(status_value: str) -> bool:
    return status_value in {"processed", "transcribed"}


def _extract_processing_error(notes: str | None) -> str | None:
    if not notes:
        return None

    try:
        payload = json.loads(notes)
        if isinstance(payload, dict):
            error = payload.get("processing_error")
            return str(error) if error else None
    except json.JSONDecodeError:
        return None

    return None


def _to_audio_record_out(record) -> AudioRecordOut:
    return AudioRecordOut(
        id=record.id,
        uuid=record.uuid,
        user_id=record.user_id,
        source_type=record.source_type,
        original_filename=record.original_filename,
        mime_type=record.mime_type,
        file_size_bytes=record.file_size_bytes,
        duration_seconds=record.duration_seconds,
        language_code=record.language_code,
        status=record.status,
        transcript_text=record.transcript_text,
        notes=record.notes,
        is_ready_for_inference=_is_ready_status(record.status),
        processing_error=_extract_processing_error(record.notes),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _run_audio_processing_background(audio_id: int, user_id: int) -> None:
    """Run processing in a dedicated DB session so upload request can return immediately."""
    db = SessionLocal()
    try:
        process_audio_pipeline(db, audio_id, user_id)
    except Exception:
        # process_audio_pipeline persists failed state and error context.
        pass
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=AudioUploadResponse, status_code=201)
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_type: str = Form("upload"),
    language_code: str | None = Form(None),
    notes: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload an audio file.
    Accepts multipart/form-data with the audio file and optional metadata.
    """
    # Read the file content to measure size
    contents = await file.read()
    file_size = len(contents)

    # Validate
    try:
        audio_service.validate_audio_file(file.content_type, file_size)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # Reset file cursor for storage
    import io
    file_like = io.BytesIO(contents)

    # Save to storage
    file_meta = audio_service.save_audio_file(
        file=file_like,
        user_id=current_user.id,
        original_filename=file.filename or "audio.bin",
        content_type=file.content_type,
    )

    # Persist metadata in DB
    record = audio_service.create_audio_record(
        db=db,
        user_id=current_user.id,
        file_meta=file_meta,
        original_filename=file.filename or "audio.bin",
        content_type=file.content_type,
        file_size=file_size,
        source_type=source_type,
        language_code=language_code,
        notes=notes,
    )

    # Expose processing state immediately in history while extraction runs.
    record.status = "processing"
    db.commit()

    # Process stored audio in the background.
    background_tasks.add_task(_run_audio_processing_background, record.id, current_user.id)

    return AudioUploadResponse(
        audio_id=record.id,
        uuid=record.uuid,
        status=record.status,
        original_filename=record.original_filename,
        mime_type=record.mime_type,
        file_size_bytes=record.file_size_bytes,
        created_at=record.created_at,
    )


@router.get("/me", response_model=AudioListResponse)
def list_my_audios(
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List audio records for the authenticated user."""
    items, total = audio_service.list_user_audios(
        db, current_user.id, status_filter=status_filter, limit=limit, offset=offset
    )
    return AudioListResponse(
        items=[_to_audio_record_out(i) for i in items],
        total=total,
    )


@router.get("/{audio_id}", response_model=AudioRecordOut)
def get_audio(
    audio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single audio record. Owner or admin only."""
    record = audio_service.get_audio_record(db, audio_id)
    if not record:
        raise HTTPException(status_code=404, detail="Audio record not found.")

    if record.user_id != current_user.id and not _is_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Access denied.")

    return _to_audio_record_out(record)


@router.delete("/{audio_id}", status_code=204)
def delete_audio(
    audio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft-delete an audio record. Owner or admin only."""
    record = audio_service.get_audio_record(db, audio_id)
    if not record:
        raise HTTPException(status_code=404, detail="Audio record not found.")

    if record.user_id != current_user.id and not _is_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Access denied.")

    audio_service.soft_delete_audio(db, record)
    db.commit()


# ---------------------------------------------------------------------------
# Audio Processing Endpoints
# ---------------------------------------------------------------------------

from typing import Optional
from app.schemas.audio_processing import (
    AudioProcessingRequest, 
    AudioProcessingResponse,
    BatchProcessingRequest,
    BatchProcessingResult,
    BatchProcessingResponse,
    AudioAnalysisSummary
)
from app.services.audio_pipeline import (
    process_audio_pipeline,
    batch_process_user_audio,
    get_audio_analysis_summary,
    AudioPipelineError
)


@router.post("/{audio_id}/process", response_model=AudioProcessingResponse)
def process_audio(
    audio_id: int,
    request: AudioProcessingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Process an audio file to extract features and run Parkinson's prediction.
    """
    # Verify ownership
    record = audio_service.get_audio_record(db, audio_id)
    if not record:
        raise HTTPException(status_code=404, detail="Audio record not found.")
    
    if record.user_id != current_user.id and not _is_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Access denied.")

    if record.status == "processing":
        return AudioProcessingResponse(
            audio_record_id=record.id,
            status="processing",
            message="Audio is currently being processed.",
        )

    if _is_ready_status(record.status):
        return AudioProcessingResponse(
            audio_record_id=record.id,
            status="already_processed",
            message="Audio was previously processed.",
        )
    
    try:
        # Process the audio pipeline
        result = process_audio_pipeline(db, audio_id, current_user.id)
        
        return AudioProcessingResponse(
            audio_record_id=result["audio_record_id"],
            status=result["status"],
            features=result.get("features"),
            diagnosis_id=result.get("diagnosis_id"),
            prediction=result.get("prediction"),
            probability=result.get("probability"),
            message=result.get("message")
        )
    except AudioPipelineError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch-process", response_model=BatchProcessingResponse)
def batch_process_audio(
    request: BatchProcessingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Process multiple audio records for the current user.
    """
    limit = request.limit if not request.process_all else 1000  # Large limit for "all"
    
    try:
        results = batch_process_user_audio(db, current_user.id, limit)
        
        successful = sum(1 for r in results if r["status"] in ["success", "already_processed"])
        failed = sum(1 for r in results if r["status"] == "failed")
        
        return BatchProcessingResponse(
            results=[
                BatchProcessingResult(
                    audio_record_id=r["audio_record_id"],
                    status=r["status"],
                    error=r.get("error"),
                    features=r.get("features"),
                    diagnosis_id=r.get("diagnosis_id")
                )
                for r in results
            ],
            total_processed=len(results),
            successful=successful,
            failed=failed
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")


@router.get("/analysis/summary", response_model=AudioAnalysisSummary)
def get_audio_analysis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get summary of audio analysis for the current user.
    """
    try:
        summary = get_audio_analysis_summary(db, current_user.id)
        return AudioAnalysisSummary(**summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analysis summary: {str(e)}")


@router.get("/{audio_id}/features")
def get_audio_features(
    audio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get extracted features from a processed audio record.
    """
    record = audio_service.get_audio_record(db, audio_id)
    if not record:
        raise HTTPException(status_code=404, detail="Audio record not found.")
    
    if record.user_id != current_user.id and not _is_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Access denied.")
    
    if not _is_ready_status(record.status) or not record.notes:
        raise HTTPException(
            status_code=400, 
            detail="Audio not processed or no features available."
        )
    
    try:
        notes_data = json.loads(record.notes)
        features = notes_data.get("extracted_features", {})
        
        if not features:
            # Try to find features in the notes structure
            for key, value in notes_data.items():
                if isinstance(value, dict) and any(f in value for f in ["MDVP:Fo(Hz)", "jitter", "shimmer"]):
                    features = value
                    break
        
        return {"audio_id": audio_id, "features": features}
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse audio features.")

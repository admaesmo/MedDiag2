"""
Endpoints de audio — carga, listado, detalle y eliminación.
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
# Utilidades
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
    """Ejecuta el procesamiento en una sesión dedicada para responder rápido a la carga."""
    db = SessionLocal()
    try:
        # create_diagnosis=False: el diagnóstico se crea explícitamente vía /predict/parkinson.
        # Así se evita duplicar diagnósticos cuando el frontend llama predict + upload juntos.
        process_audio_pipeline(db, audio_id, user_id, create_diagnosis=False)
    except Exception:
        # process_audio_pipeline persiste el estado fallido y el contexto del error.
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
    Carga un archivo de audio.
    Acepta multipart/form-data con el archivo y metadatos opcionales.
    """
    # Leer el contenido para medir el tamaño.
    contents = await file.read()
    file_size = len(contents)

    # Validar archivo.
    try:
        audio_service.validate_audio_file(file.content_type, file_size)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # Reiniciar el cursor para almacenamiento.
    import io
    file_like = io.BytesIO(contents)

    # Guardar en almacenamiento.
    file_meta = audio_service.save_audio_file(
        file=file_like,
        user_id=current_user.id,
        original_filename=file.filename or "audio.bin",
        content_type=file.content_type,
    )

    # Persistir metadatos en base de datos.
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

    # Mostrar el estado de procesamiento mientras corre la extracción.
    record.status = "processing"
    db.commit()

    # Procesar el audio almacenado en segundo plano.
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
    """Lista los registros de audio del usuario autenticado."""
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
    """Obtiene un registro de audio. Solo propietario o administrador."""
    record = audio_service.get_audio_record(db, audio_id)
    if not record:
        raise HTTPException(status_code=404, detail="Registro de audio no encontrado.")

    if record.user_id != current_user.id and not _is_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Acceso denegado.")

    return _to_audio_record_out(record)


@router.delete("/{audio_id}", status_code=204)
def delete_audio(
    audio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Elimina lógicamente un registro de audio. Solo propietario o administrador."""
    record = audio_service.get_audio_record(db, audio_id)
    if not record:
        raise HTTPException(status_code=404, detail="Registro de audio no encontrado.")

    if record.user_id != current_user.id and not _is_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Acceso denegado.")

    audio_service.soft_delete_audio(db, record)
    db.commit()


# ---------------------------------------------------------------------------
# Endpoints de procesamiento de audio
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
    get_latest_feature_set,
    load_feature_set_payload,
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
    Procesa un audio para extraer biomarcadores y ejecutar la predicción de Parkinson.
    """
    # Verificar propiedad.
    record = audio_service.get_audio_record(db, audio_id)
    if not record:
        raise HTTPException(status_code=404, detail="Registro de audio no encontrado.")
    
    if record.user_id != current_user.id and not _is_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Acceso denegado.")

    if record.status == "processing":
        return AudioProcessingResponse(
            audio_record_id=record.id,
            status="processing",
            message="El audio se está procesando actualmente.",
        )

    if _is_ready_status(record.status):
        return AudioProcessingResponse(
            audio_record_id=record.id,
            status="already_processed",
            message="El audio ya había sido procesado.",
        )
    
    try:
        # Procesar el pipeline de audio.
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
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.post("/batch-process", response_model=BatchProcessingResponse)
def batch_process_audio(
    request: BatchProcessingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Procesa varios registros de audio del usuario actual.
    """
    limit = request.limit if not request.process_all else 1000  # Límite amplio para "todos".
    
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
        raise HTTPException(status_code=500, detail=f"Falló el procesamiento por lotes: {str(e)}")


@router.get("/analysis/summary", response_model=AudioAnalysisSummary)
def get_audio_analysis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Obtiene el resumen de análisis de audio del usuario actual.
    """
    try:
        summary = get_audio_analysis_summary(db, current_user.id)
        return AudioAnalysisSummary(**summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo obtener el resumen de análisis: {str(e)}")


@router.get("/{audio_id}/features")
def get_audio_features(
    audio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Obtiene los biomarcadores extraídos de un audio procesado.
    """
    record = audio_service.get_audio_record(db, audio_id)
    if not record:
        raise HTTPException(status_code=404, detail="Registro de audio no encontrado.")
    
    if record.user_id != current_user.id and not _is_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    
    if not _is_ready_status(record.status):
        raise HTTPException(
            status_code=400, 
            detail="El audio no ha sido procesado o no hay biomarcadores disponibles."
        )

    # Fuente primaria: Feature Store.
    feature_row = get_latest_feature_set(db, audio_id)
    if feature_row is not None:
        return {
            "audio_id": audio_id,
            "features": load_feature_set_payload(feature_row),
            "feature_set_id": feature_row.id,
            "extractor_version": feature_row.extractor_version,
            "feature_schema_version": feature_row.feature_schema_version,
            "partial_features": feature_row.is_partial,
        }

    # Compatibilidad hacia atrás: carga desde notes.
    if not record.notes:
        raise HTTPException(status_code=404, detail="No se encontró un conjunto de biomarcadores para este audio.")

    try:
        notes_data = json.loads(record.notes)
        features = notes_data.get("extracted_features", {})
        return {"audio_id": audio_id, "features": features}
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="No se pudieron interpretar los biomarcadores del audio.")


# ---------------------------------------------------------------------------
# Endpoints de control de calidad
# ---------------------------------------------------------------------------


@router.get("/{audio_id}/quality")
def get_audio_quality_report(
    audio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtiene el último reporte de calidad de un audio. Solo propietario o administrador."""
    record = audio_service.get_audio_record(db, audio_id)
    if not record:
        raise HTTPException(status_code=404, detail="Registro de audio no encontrado.")

    if record.user_id != current_user.id and not _is_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Acceso denegado.")

    from app.services.quality_control import get_latest_quality_report
    report = get_latest_quality_report(db, audio_id)
    if report is None:
        raise HTTPException(status_code=404, detail="No hay reporte de calidad disponible para este audio.")

    return {
        "id": report.id,
        "audio_record_id": report.audio_record_id,
        "is_valid": report.is_valid,
        "quality_score": report.quality_score,
        "rejection_reason": report.rejection_reason,
        "duration_seconds": report.duration_seconds,
        "rms_energy": report.rms_energy,
        "peak_amplitude": report.peak_amplitude,
        "clipping_detected": report.clipping_detected,
        "clipping_ratio": report.clipping_ratio,
        "snr_db": report.snr_db,
        "silence_ratio": report.silence_ratio,
        "noise_floor_db": report.noise_floor_db,
        "bandwidth_hz": report.bandwidth_hz,
        "created_at": report.created_at,
    }


@router.post("/{audio_id}/quality/check")
def run_audio_quality_check(
    audio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ejecuta o repite el control de calidad de un audio. Solo propietario o administrador."""
    from app.services.quality_control import run_quality_check

    record = audio_service.get_audio_record(db, audio_id)
    if not record:
        raise HTTPException(status_code=404, detail="Registro de audio no encontrado.")

    if record.user_id != current_user.id and not _is_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Acceso denegado.")

    try:
        report = run_quality_check(db, audio_id)
        return {
            "id": report.id,
            "audio_record_id": report.audio_record_id,
            "is_valid": report.is_valid,
            "quality_score": report.quality_score,
            "rejection_reason": report.rejection_reason,
            "duration_seconds": report.duration_seconds,
            "rms_energy": report.rms_energy,
            "peak_amplitude": report.peak_amplitude,
            "clipping_detected": report.clipping_detected,
            "clipping_ratio": report.clipping_ratio,
            "snr_db": report.snr_db,
            "silence_ratio": report.silence_ratio,
            "noise_floor_db": report.noise_floor_db,
            "bandwidth_hz": report.bandwidth_hz,
            "created_at": report.created_at,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=f"Falló el control de calidad: {exc}")

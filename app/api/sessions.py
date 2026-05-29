"""
Endpoints de sesiones de voz — múltiples tomas para análisis robusto.

Flujo típico:
  POST /sessions                    → crear sesión (max_takes=3)
  POST /sessions/{id}/takes  ×N    → subir cada toma (dispara pipeline por toma)
  GET  /sessions/{id}               → consultar estado y tomas
  POST /sessions/{id}/analyze       → agregar tomas válidas + inferencia
  GET  /sessions/{id}/result        → obtener resultado ya calculado
  DELETE /sessions/{id}/takes/{tid} → retirar una toma fallida para reintentar
"""

from __future__ import annotations

import io
import logging
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.models import AudioRecord, User, UserRole, VoiceSession
from app.schemas.sessions import SessionAnalysisResult, VoiceSessionCreate, VoiceSessionOut
from app.services import audio_service
from app.services.auth_service import get_current_user, get_db
from app.services.audio_pipeline import process_audio_pipeline, AudioPipelineError
from app.services.session_pipeline import (
    SessionPipelineError,
    analyze_session,
    count_registered_takes,
    get_session_with_takes_summary,
    next_take_number,
)
from app.utils.database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _is_admin(db: Session, user: User) -> bool:
    return any(
        ur.role.code == "admin"
        for ur in db.query(UserRole).filter(UserRole.user_id == user.id).all()
    )


def _get_session_or_404(db: Session, session_id: int) -> VoiceSession:
    s = db.query(VoiceSession).filter(VoiceSession.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    return s


def _assert_owner(session: VoiceSession, current_user: User, db: Session) -> None:
    if session.user_id != current_user.id and not _is_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Acceso denegado.")


def _run_take_pipeline_background(audio_id: int, user_id: int) -> None:
    db = SessionLocal()
    try:
        process_audio_pipeline(db, audio_id, user_id)
    except Exception:
        pass
    finally:
        db.close()


# ---------------------------------------------------------------------------
# POST /sessions — Crear sesión
# ---------------------------------------------------------------------------

@router.post("", status_code=201, response_model=VoiceSessionOut)
def create_session(
    body: VoiceSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Inicia una nueva sesión de análisis de voz.
    La sesión permanece en estado 'collecting' hasta que el usuario
    llame explícitamente a POST /sessions/{id}/analyze.
    """
    session = VoiceSession(
        user_id=current_user.id,
        max_takes=body.max_takes,
        status="collecting",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info("Sesión %d creada para usuario %d (max_takes=%d)", session.id, current_user.id, body.max_takes)
    return VoiceSessionOut(
        id=session.id,
        uuid=session.uuid,
        user_id=session.user_id,
        max_takes=session.max_takes,
        status=session.status,
        created_at=session.created_at,
        takes=[],
    )


# ---------------------------------------------------------------------------
# POST /sessions/{id}/takes — Agregar una toma
# ---------------------------------------------------------------------------

@router.post("/{session_id}/takes", status_code=202)
async def add_take(
    session_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_type: str = Form("microphone"),
    language_code: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Sube una toma de audio a la sesión y dispara su procesamiento en segundo plano.

    Reglas:
    - La sesión debe estar en estado 'collecting'.
    - No se puede superar max_takes.
    - El procesamiento (QC + extracción) ocurre en segundo plano.
    """
    session = _get_session_or_404(db, session_id)
    _assert_owner(session, current_user, db)

    if session.status != "collecting":
        raise HTTPException(
            status_code=409,
            detail=f"La sesión está en estado '{session.status}'. Solo se pueden agregar tomas en estado 'collecting'.",
        )

    current_count = count_registered_takes(session)
    if current_count >= session.max_takes:
        raise HTTPException(
            status_code=409,
            detail=f"La sesión ya tiene {current_count} tomas (máximo: {session.max_takes}). "
                   "Llame a POST /sessions/{id}/analyze para proceder.",
        )

    contents = await file.read()
    file_size = len(contents)

    try:
        audio_service.validate_audio_file(file.content_type, file_size)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    file_meta = audio_service.save_audio_file(
        file=io.BytesIO(contents),
        user_id=current_user.id,
        original_filename=file.filename or "audio.bin",
        content_type=file.content_type,
    )

    take_num = next_take_number(session)
    record = audio_service.create_audio_record(
        db=db,
        user_id=current_user.id,
        file_meta=file_meta,
        original_filename=file.filename or "audio.bin",
        content_type=file.content_type,
        file_size=file_size,
        source_type=source_type,
        language_code=language_code,
    )
    record.session_id = session.id
    record.take_number = take_num
    record.status = "processing"
    db.commit()

    background_tasks.add_task(_run_take_pipeline_background, record.id, current_user.id)

    logger.info("Toma %d agregada a sesión %d (audio_id=%d)", take_num, session_id, record.id)

    return {
        "audio_record_id": record.id,
        "uuid": record.uuid,
        "take_number": take_num,
        "status": record.status,
        "message": f"Toma {take_num} recibida. Procesándose en segundo plano.",
        "takes_registered": take_num,
        "max_takes": session.max_takes,
    }


# ---------------------------------------------------------------------------
# GET /sessions/{id} — Estado de la sesión
# ---------------------------------------------------------------------------

@router.get("/{session_id}", response_model=VoiceSessionOut)
def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Devuelve el estado de la sesión y el resumen de cada toma."""
    session = _get_session_or_404(db, session_id)
    _assert_owner(session, current_user, db)
    summary = get_session_with_takes_summary(db, session)
    return VoiceSessionOut(**summary)


# ---------------------------------------------------------------------------
# POST /sessions/{id}/analyze — Agregar + inferir
# ---------------------------------------------------------------------------

@router.post("/{session_id}/analyze", response_model=SessionAnalysisResult)
def analyze(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Agrega las tomas válidas de la sesión y ejecuta la inferencia de Parkinson.

    Requisitos:
    - Al menos 2 tomas en estado 'processed'.
    - Las tomas aún en estado 'processing' se ignoran (no se esperan).

    El usuario puede llamar este endpoint en cualquier momento tras tener
    ≥ 2 tomas procesadas, o reintentar tomas fallidas antes de llamarlo.
    """
    session = _get_session_or_404(db, session_id)
    _assert_owner(session, current_user, db)

    try:
        result = analyze_session(db, session_id, current_user.id)
    except SessionPipelineError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return SessionAnalysisResult(**result)


# ---------------------------------------------------------------------------
# GET /sessions/{id}/result — Resultado ya calculado
# ---------------------------------------------------------------------------

@router.get("/{session_id}/result", response_model=SessionAnalysisResult)
def get_result(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Devuelve el resultado de una sesión ya analizada sin reejecutar la inferencia."""
    session = _get_session_or_404(db, session_id)
    _assert_owner(session, current_user, db)

    if session.status != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"La sesión aún no está completada (estado: '{session.status}'). "
                   "Use POST /sessions/{id}/analyze primero.",
        )

    from app.services.session_pipeline import _build_result_from_session
    result = _build_result_from_session(session)

    # Recuperar probabilidad del diagnóstico persistido
    if session.diagnosis_id:
        from app.models import Diagnosis
        diag = db.query(Diagnosis).filter(Diagnosis.id == session.diagnosis_id).first()
        if diag:
            prob = float(next((d.probability for d in diag.details), 0.0))
            pred = "positive" if diag.final_description.startswith("Posibles") else "negative"
            result["probability"] = prob
            result["prediction"] = pred
            result["message"] = diag.final_description

    return SessionAnalysisResult(**result)


# ---------------------------------------------------------------------------
# DELETE /sessions/{id}/takes/{take_id} — Retirar una toma
# ---------------------------------------------------------------------------

@router.delete("/{session_id}/takes/{take_id}", status_code=204)
def remove_take(
    session_id: int,
    take_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retira lógicamente una toma de la sesión para permitir reintento.
    Solo es posible si la sesión sigue en estado 'collecting'.
    """
    session = _get_session_or_404(db, session_id)
    _assert_owner(session, current_user, db)

    if session.status != "collecting":
        raise HTTPException(
            status_code=409,
            detail="No se pueden retirar tomas de una sesión que ya no está en estado 'collecting'.",
        )

    record = db.query(AudioRecord).filter(
        AudioRecord.id == take_id,
        AudioRecord.session_id == session_id,
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Toma no encontrada en esta sesión.")

    audio_service.soft_delete_audio(db, record)
    db.commit()
    logger.info("Toma %d retirada de sesión %d por usuario %d", take_id, session_id, current_user.id)

"""
Lógica de negocio para registros de audio: guardar archivos y CRUD en base de datos.
"""

import os
import uuid as _uuid
from datetime import datetime, timezone
from typing import BinaryIO, List, Optional

from sqlalchemy.orm import Session

from app.models import AudioRecord
from app.services.storage_service import get_storage_backend

ALLOWED_MIME_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp4",
    "audio/ogg",
    "application/ogg",
    "audio/flac",
    "audio/x-m4a",
    "application/octet-stream",
}

MAX_FILE_SIZE = int(os.getenv("MAX_AUDIO_FILE_SIZE_MB", "25")) * 1024 * 1024  # bytes


def validate_audio_file(content_type: Optional[str], file_size: int) -> None:
    """Lanza ValueError si el audio no tiene un tipo permitido o es demasiado grande."""
    normalized_content_type = (content_type or "").split(";", 1)[0].strip().lower()

    if normalized_content_type and normalized_content_type not in ALLOWED_MIME_TYPES:
        raise ValueError(
            f"Tipo de archivo no permitido: {content_type}. "
            f"Permitidos: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
        )
    if file_size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE // (1024 * 1024)
        raise ValueError(f"Archivo demasiado grande. Máximo: {max_mb} MB.")


def save_audio_file(
    file: BinaryIO,
    user_id: int,
    original_filename: str,
    content_type: Optional[str],
) -> dict:
    """
    Persiste el archivo de audio y devuelve metadatos (uuid, stored_filename, etc.).
    """
    audio_uuid = str(_uuid.uuid4())
    ext = _safe_extension(original_filename, content_type)
    stored_filename = f"{audio_uuid}{ext}"
    relative_path = f"{user_id}/{stored_filename}"

    backend = get_storage_backend()
    backend.save(file, relative_path)

    return {
        "uuid": audio_uuid,
        "stored_filename": stored_filename,
        "storage_path": relative_path,
        "storage_provider": os.getenv("STORAGE_PROVIDER", "local"),
    }


def create_audio_record(
    db: Session,
    user_id: int,
    file_meta: dict,
    original_filename: str,
    content_type: Optional[str],
    file_size: int,
    source_type: str = "upload",
    language_code: Optional[str] = None,
    notes: Optional[str] = None,
) -> AudioRecord:
    """Inserta una fila en audio_records."""
    record = AudioRecord(
        uuid=file_meta["uuid"],
        user_id=user_id,
        source_type=source_type,
        original_filename=original_filename,
        stored_filename=file_meta["stored_filename"],
        storage_provider=file_meta["storage_provider"],
        storage_path=file_meta["storage_path"],
        mime_type=content_type,
        file_size_bytes=file_size,
        language_code=language_code,
        notes=notes,
        status="uploaded",
    )
    db.add(record)
    db.flush()
    return record


def list_user_audios(
    db: Session,
    user_id: int,
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[List[AudioRecord], int]:
    """Devuelve (items, total) para audios del usuario no eliminados lógicamente."""
    q = db.query(AudioRecord).filter(
        AudioRecord.user_id == user_id,
        AudioRecord.deleted_at.is_(None),
    )
    if status_filter:
        q = q.filter(AudioRecord.status == status_filter)

    total = q.count()
    items = q.order_by(AudioRecord.created_at.desc()).offset(offset).limit(limit).all()
    return items, total


def get_audio_record(db: Session, audio_id: int) -> Optional[AudioRecord]:
    return (
        db.query(AudioRecord)
        .filter(AudioRecord.id == audio_id, AudioRecord.deleted_at.is_(None))
        .first()
    )


def soft_delete_audio(db: Session, record: AudioRecord) -> None:
    record.deleted_at = datetime.now(timezone.utc)
    db.flush()


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

_MIME_TO_EXT = {
    "audio/webm": ".webm",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/ogg": ".ogg",
    "application/ogg": ".ogg",
    "audio/flac": ".flac",
    "audio/x-m4a": ".m4a",
}


def _safe_extension(filename: str, content_type: Optional[str]) -> str:
    """Deriva una extensión segura para el archivo."""
    # Intentar primero desde content-type.
    if content_type and content_type in _MIME_TO_EXT:
        return _MIME_TO_EXT[content_type]
    # Respaldo: usar el nombre original.
    _, ext = os.path.splitext(filename)
    return ext.lower() if ext else ".bin"

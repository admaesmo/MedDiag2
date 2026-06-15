"""
Pipeline de audio: coordina el flujo completo de procesamiento.

Secuencia:
  1. Cargar bytes de audio desde almacenamiento
  2. Control de calidad (QA/QC) — compuerta antes de la extracción
  3. Extraer biomarcadores acústicos
  4. Validar valores y registrar features faltantes
  5. Persistir en BiomarkerFeature (Feature Store)
  6. Ejecutar predicción de Parkinson
  7. Actualizar estado del registro
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import AudioRecord, BiomarkerFeature, Diagnosis, DiagnosisDetail, Disease
from app.model_predict import predict_parkinson
from app.services.audio_processing import extract_features_from_audio, AudioProcessingError
from app.services.constants import PARKINSON_FEATURE_ORDER
from app.services.feature_validator import sanitize_features, validate_features, get_feature_quality_score
from app.services.storage_service import get_storage_backend

logger = logging.getLogger(__name__)

FEATURE_EXTRACTOR_VERSION = "audio-processing+nonlinear-v1"
FEATURE_SCHEMA_VERSION = "parkinson-oxford-22-v1"


class AudioPipelineError(Exception):
    pass


# ---------------------------------------------------------------------------
# Utilidades de features
# ---------------------------------------------------------------------------

def _detect_invalid_values(features: Dict[str, float]) -> List[str]:
    """Detecta variables presentes en el dict pero con valor NaN o infinito."""
    return [
        f for f in PARKINSON_FEATURE_ORDER
        if f in features and not (float("-inf") < features[f] < float("inf"))
    ]


# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------

def store_processing_result(db: Session, audio_record_id: int, diagnosis_id: int) -> None:
    """Marca el audio como procesado y vincula el diagnóstico en notes."""
    audio_record = db.query(AudioRecord).filter(AudioRecord.id == audio_record_id).first()
    if not audio_record:
        raise AudioPipelineError(f"Registro de audio {audio_record_id} no encontrado")

    notes_payload: dict = {}
    if audio_record.notes:
        try:
            existing = json.loads(audio_record.notes)
            if isinstance(existing, dict):
                notes_payload.update(existing)
            else:
                notes_payload["original_notes"] = existing
        except json.JSONDecodeError:
            notes_payload["original_notes"] = audio_record.notes

    notes_payload["diagnosis_id"] = diagnosis_id
    audio_record.notes = json.dumps(notes_payload, indent=2, default=str)
    audio_record.status = "processed"
    audio_record.updated_at = datetime.now(timezone.utc)
    db.commit()


def store_biomarker_feature_set(
    db: Session,
    audio_record_id: int,
    features: Dict[str, float],
    missing_features: List[str],
    extractor_version: str = FEATURE_EXTRACTOR_VERSION,
    feature_schema_version: str = FEATURE_SCHEMA_VERSION,
) -> BiomarkerFeature:
    payload = {k: float(v) for k, v in features.items()}

    row = (
        db.query(BiomarkerFeature)
        .filter(
            BiomarkerFeature.audio_record_id == audio_record_id,
            BiomarkerFeature.extractor_version == extractor_version,
            BiomarkerFeature.feature_schema_version == feature_schema_version,
        )
        .first()
    )

    if row is None:
        row = BiomarkerFeature(
            audio_record_id=audio_record_id,
            extractor_version=extractor_version,
            feature_schema_version=feature_schema_version,
            features_json=json.dumps(payload, indent=2),
            missing_features_json=json.dumps(missing_features),
            is_partial=bool(missing_features),
        )
        db.add(row)
    else:
        row.features_json = json.dumps(payload, indent=2)
        row.missing_features_json = json.dumps(missing_features)
        row.is_partial = bool(missing_features)

    db.commit()
    db.refresh(row)
    return row


def get_latest_feature_set(db: Session, audio_record_id: int) -> Optional[BiomarkerFeature]:
    return (
        db.query(BiomarkerFeature)
        .filter(BiomarkerFeature.audio_record_id == audio_record_id)
        .order_by(BiomarkerFeature.created_at.desc())
        .first()
    )


def load_feature_set_payload(row: Optional[BiomarkerFeature]) -> Dict[str, float]:
    if row is None:
        return {}
    try:
        payload = json.loads(row.features_json or "{}")
        if isinstance(payload, dict):
            return {str(k): float(v) for k, v in payload.items()}
    except Exception:
        pass
    return {}


# ---------------------------------------------------------------------------
# Diagnóstico
# ---------------------------------------------------------------------------

def create_parkinson_diagnosis(
    db: Session,
    user_id: int,
    features: Dict[str, float],
    audio_record_id: Optional[int] = None,
) -> Diagnosis:
    try:
        prediction_label, probability = predict_parkinson(features)
    except Exception as exc:
        logger.error("Predicción de Parkinson fallida: %s", exc, exc_info=True)
        raise AudioPipelineError(f"Falló la predicción: {exc}")

    diagnosis = Diagnosis(
        user_id=user_id,
        generated_at=datetime.now(timezone.utc),
        status="pending",
        final_description="Diagnóstico preliminar de Parkinson basado en análisis de voz.",
    )
    db.add(diagnosis)
    db.flush()

    parkinson_disease = db.query(Disease).filter(Disease.disease_code == "PARK").first()
    if not parkinson_disease:
        raise AudioPipelineError("No se encontró el registro de Parkinson en la base de datos")

    db.add(DiagnosisDetail(
        diagnosis_id=diagnosis.id,
        disease_id=parkinson_disease.id,
        probability=probability,
    ))

    if prediction_label == 1:
        diagnosis.final_description = (
            f"Posibles indicadores de Parkinson detectados con {probability:.1%} de confianza. "
            "Consulte a un neurólogo."
        )
    else:
        diagnosis.final_description = (
            f"No se detectaron indicadores significativos de Parkinson ({probability:.1%} de confianza)."
        )

    if audio_record_id:
        diagnosis.final_description += f" Basado en la grabación de audio #{audio_record_id}."

    db.commit()
    return diagnosis


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def process_audio_pipeline(
    db: Session,
    audio_record_id: int,
    user_id: Optional[int] = None,
    create_diagnosis: bool = True,
) -> Dict:
    """
    Ejecuta el pipeline completo para un registro de audio.

    Retorna un diccionario con el resultado del procesamiento.
    """
    audio_record = db.query(AudioRecord).filter(AudioRecord.id == audio_record_id).first()
    if not audio_record:
        raise AudioPipelineError(f"Registro de audio {audio_record_id} no encontrado")

    if user_id is None:
        user_id = audio_record.user_id

    # Si ya fue procesado, devolver los biomarcadores persistidos.
    if audio_record.status in {"processed", "transcribed"}:
        logger.info("Registro %d ya procesado", audio_record_id)
        features = load_feature_set_payload(get_latest_feature_set(db, audio_record_id))
        if features:
            return {
                "audio_record_id": audio_record_id,
                "status": "already_processed",
                "features": features,
                "message": "El audio ya había sido procesado",
            }
        logger.info("Registro %d sin biomarcadores; se reprocesará", audio_record_id)

    try:
        audio_record.status = "processing"
        audio_record.updated_at = datetime.now(timezone.utc)
        db.commit()

        # --- COMPUERTA QA/QC ---
        from app.services.quality_control import run_quality_check
        qc_report = run_quality_check(db, audio_record_id)
        if not qc_report.is_valid:
            reason = qc_report.rejection_reason or "El audio no superó el control de calidad"
            logger.warning("QA/QC rechazó el registro %d: %s", audio_record_id, reason)
            raise AudioPipelineError(f"Control de calidad rechazado: {reason}")

        # --- CARGA DE AUDIO ---
        backend = get_storage_backend()
        audio_bytes = backend.load(audio_record.storage_path)
        if not audio_bytes:
            raise AudioProcessingError("No se pudo cargar el archivo de audio desde almacenamiento")

        # --- EXTRACCIÓN DE BIOMARCADORES ---
        features, missing_features = extract_features_from_audio(
            audio_bytes,
            source_name=audio_record.original_filename or audio_record.stored_filename,
        )

        # Agregar variables con valor NaN/inf a la lista de faltantes.
        invalid = _detect_invalid_values(features)
        if invalid:
            logger.warning("Features con valores inválidos (NaN/inf): %s", invalid)
            missing_features = list(set(missing_features) | set(invalid))
            for f in invalid:
                features.pop(f, None)

        # --- SANEAMIENTO TEMPORAL (clamping a rangos UCI) ---
        raw_features = dict(features)
        features = sanitize_features(features)

        # --- VALIDACIÓN DE CALIDAD DE FEATURES ---
        quality = validate_features(features)
        quality_score = get_feature_quality_score(features)

        if not quality["valid"]:
            error_msg = (
                f"Extracción no confiable: {quality['message']}. "
                f"Puntaje: {quality_score:.1%}."
            )
            logger.warning("Calidad rechazada para audio %d: %s", audio_record_id, error_msg)

            store_biomarker_feature_set(
                db=db,
                audio_record_id=audio_record_id,
                features=features,
                missing_features=missing_features,
            )
            audio_record.status = "failed"
            audio_record.notes = json.dumps({
                "processing_error": error_msg,
                "quality_score": quality_score,
                "out_of_range_pct": quality["out_of_range_pct"],
                "critical_failures": quality["critical_failures"],
                "raw_features_snapshot": {k: float(v) for k, v in raw_features.items()},
            })
            audio_record.updated_at = datetime.now(timezone.utc)
            db.commit()
            raise AudioPipelineError(error_msg)

        # --- PERSISTENCIA EN FEATURE STORE ---
        feature_set = store_biomarker_feature_set(
            db=db,
            audio_record_id=audio_record_id,
            features=features,
            missing_features=missing_features,
        )

        # --- INFERENCIA ---
        result: Dict = {
            "audio_record_id": audio_record_id,
            "status": "success",
            "features": features,
            "missing_features": missing_features,
            "feature_set_id": feature_set.id,
            "extractor_version": feature_set.extractor_version,
            "feature_schema_version": feature_set.feature_schema_version,
            "partial_features": feature_set.is_partial,
        }

        if create_diagnosis:
            diagnosis = create_parkinson_diagnosis(db, user_id, features, audio_record_id)
            store_processing_result(db, audio_record_id, diagnosis.id)
            result["diagnosis_id"] = diagnosis.id
            result["prediction"] = (
                "positive"
                if diagnosis.final_description and diagnosis.final_description.startswith("Posibles")
                else "negative"
            )
            result["probability"] = float(next((d.probability for d in diagnosis.details), 0.0))
            result["message"] = diagnosis.final_description
        else:
            # Diagnóstico se crea aparte (vía /predict/parkinson); aquí sólo se
            # extraen y persisten los biomarcadores. Marcar el audio como procesado.
            audio_record.status = "processed"
            audio_record.updated_at = datetime.now(timezone.utc)
            db.commit()

        logger.info("Pipeline completado correctamente para registro %d", audio_record_id)
        return result

    except Exception as exc:
        logger.error("Pipeline fallido para registro %d: %s", audio_record_id, exc, exc_info=True)
        audio_record.status = "failed"
        audio_record.notes = json.dumps({"processing_error": str(exc)})
        audio_record.updated_at = datetime.now(timezone.utc)
        db.commit()
        raise AudioPipelineError(f"Falló el pipeline de audio: {exc}")


# ---------------------------------------------------------------------------
# Utilidades de lote y resumen
# ---------------------------------------------------------------------------

def batch_process_user_audio(db: Session, user_id: int, limit: int = 10) -> List[Dict]:
    """Procesa varios registros pendientes de un usuario."""
    audio_records = (
        db.query(AudioRecord)
        .filter(
            AudioRecord.user_id == user_id,
            AudioRecord.status.in_(["uploaded", "failed"]),
            AudioRecord.deleted_at.is_(None),
        )
        .order_by(AudioRecord.created_at.desc())
        .limit(limit)
        .all()
    )

    results = []
    for record in audio_records:
        try:
            results.append(process_audio_pipeline(db, record.id, user_id))
        except Exception as exc:
            results.append({"audio_record_id": record.id, "status": "failed", "error": str(exc)})

    return results


def get_audio_analysis_summary(db: Session, user_id: int) -> Dict:
    """Resumen de análisis de audio para un usuario."""
    audio_records = (
        db.query(AudioRecord)
        .filter(AudioRecord.user_id == user_id, AudioRecord.deleted_at.is_(None))
        .all()
    )

    status_counts: Dict[str, int] = {}
    for record in audio_records:
        status_counts[record.status] = status_counts.get(record.status, 0) + 1

    recent_diagnoses = (
        db.query(Diagnosis)
        .filter(Diagnosis.user_id == user_id)
        .order_by(Diagnosis.generated_at.desc())
        .limit(5)
        .all()
    )

    processed_features = []
    for record in audio_records:
        if record.status == "processed":
            try:
                features = load_feature_set_payload(get_latest_feature_set(db, record.id))
                if "MDVP:Fo(Hz)" in features:
                    processed_features.append({
                        "audio_id": record.id,
                        "created_at": record.created_at,
                        "fundamental_frequency": features["MDVP:Fo(Hz)"],
                        "jitter": features.get("MDVP:Jitter(%)", 0),
                        "shimmer": features.get("MDVP:Shimmer", 0),
                        "hnr": features.get("HNR", 0),
                    })
            except Exception:
                continue

    return {
        "total_audio_records": len(audio_records),
        "status_counts": status_counts,
        "recent_diagnoses": [
            {
                "id": d.id,
                "generated_at": d.generated_at,
                "status": d.status,
                "description": d.final_description or "Sin descripción",
            }
            for d in recent_diagnoses
        ],
        "processed_features_summary": processed_features,
    }

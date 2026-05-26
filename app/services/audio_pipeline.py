"""
Servicio de pipeline de audio: coordina el flujo completo de procesamiento:
1. Cargar archivo de audio
2. Ejecutar control de calidad
3. Extraer biomarcadores acústicos
4. Ejecutar predicción de Parkinson
5. Almacenar resultados
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import AudioRecord, BiomarkerFeature, Diagnosis, DiagnosisDetail, Disease, User
from app.model_predict import predict_parkinson, PARK_FEATURE_ORDER
from app.services.audio_processing import (
    extract_features_from_audio, 
    process_audio_file,
    AudioProcessingError
)
from app.services.feature_validator import (
    sanitize_features,
    validate_features,
    get_feature_quality_score,
)

from app.services.storage_service import get_storage_backend


logger = logging.getLogger(__name__)
FEATURE_EXTRACTOR_VERSION = "audio-processing+nonlinear-v1"
FEATURE_SCHEMA_VERSION = "parkinson-oxford-22-v1"


class AudioPipelineError(Exception):
    """Excepción personalizada para errores del pipeline de audio."""
    pass


def validate_features_for_prediction(features: Dict[str, float]) -> Tuple[bool, List[str]]:
    """
    Valida que todos los biomarcadores requeridos por Parkinson existan y sean válidos.
    
    Argumentos:
        features: Diccionario de biomarcadores acústicos extraídos
        
    Retorna:
        Tupla (es_valido, biomarcadores_faltantes)
    """
    missing_features = []
    
    for feature in PARK_FEATURE_ORDER:
        if feature not in features:
            missing_features.append(feature)
            continue
            
        value = features[feature]
        if not isinstance(value, (int, float)) or not float('-inf') < value < float('inf'):
            # Los valores NaN o infinitos no son válidos.
            missing_features.append(feature)
    
    return len(missing_features) == 0, missing_features


def store_processing_result(
    db: Session,
    audio_record_id: int,
    diagnosis_id: int,
) -> None:
    """
    Marca el audio como procesado y vincula el diagnóstico en notes.

    Los biomarcadores se persisten exclusivamente en ``BiomarkerFeature``.
    El campo ``notes`` conserva la referencia al diagnóstico y metadatos previos.
    """
    audio_record = db.query(AudioRecord).filter(AudioRecord.id == audio_record_id).first()
    if not audio_record:
        raise AudioPipelineError(f"Registro de audio {audio_record_id} no encontrado")

    # Conservar contexto existente, por ejemplo las notas originales de carga.
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
    missing_payload = list(missing_features)

    row = db.query(BiomarkerFeature).filter(
        BiomarkerFeature.audio_record_id == audio_record_id,
        BiomarkerFeature.extractor_version == extractor_version,
        BiomarkerFeature.feature_schema_version == feature_schema_version,
    ).first()

    if row is None:
        row = BiomarkerFeature(
            audio_record_id=audio_record_id,
            extractor_version=extractor_version,
            feature_schema_version=feature_schema_version,
            features_json=json.dumps(payload, indent=2),
            missing_features_json=json.dumps(missing_payload),
            is_partial=bool(missing_payload),
        )
        db.add(row)
    else:
        row.features_json = json.dumps(payload, indent=2)
        row.missing_features_json = json.dumps(missing_payload)
        row.is_partial = bool(missing_payload)

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
        return {}

    return {}


def create_parkinson_diagnosis(
    db: Session, 
    user_id: int, 
    features: Dict[str, float],
    audio_record_id: Optional[int] = None
) -> Diagnosis:
    """
    Crea un diagnóstico preliminar de Parkinson basado en biomarcadores de audio.
    
    Argumentos:
        db: Sesión de base de datos
        user_id: ID del usuario
        features: Diccionario de biomarcadores acústicos extraídos
        audio_record_id: ID opcional del audio en el que se basa el diagnóstico
        
    Retorna:
        Objeto Diagnosis creado
    """
    # Ejecutar predicción.
    try:
        prediction_label, probability = predict_parkinson(features)
    except Exception as e:
        logger.error(f"No se pudo ejecutar la predicción de Parkinson: {str(e)}", exc_info=True)
        raise AudioPipelineError(f"Falló la predicción: {str(e)}")
    
    # Crear registro de diagnóstico.
    diagnosis = Diagnosis(
        user_id=user_id,
        generated_at=datetime.now(timezone.utc),
        status="pending",
        final_description="Diagnóstico preliminar de Parkinson basado en análisis de voz."
    )
    db.add(diagnosis)
    db.flush()
    
    # Obtener registro de la enfermedad Parkinson.
    parkinson_disease = db.query(Disease).filter(Disease.disease_code == "PARK").first()
    if not parkinson_disease:
        raise AudioPipelineError("No se encontró el registro de Parkinson en la base de datos")
    
    # Crear detalle del diagnóstico.
    diagnosis_detail = DiagnosisDetail(
        diagnosis_id=diagnosis.id,
        disease_id=parkinson_disease.id,
        probability=probability
    )
    db.add(diagnosis_detail)
    
    # Actualizar diagnóstico con mensaje apropiado.
    if prediction_label == 1:
        diagnosis.final_description = f"Posibles indicadores de Parkinson detectados con {probability:.1%} de confianza. Consulte a un neurólogo."
    else:
        diagnosis.final_description = f"No se detectaron indicadores significativos de Parkinson ({probability:.1%} de confianza)."
    
    # Vincular audio si fue proporcionado.
    if audio_record_id:
        # Esta relación puede almacenarse en notes o en un campo dedicado futuro.
        if not diagnosis.final_description:
            diagnosis.final_description = ""
        diagnosis.final_description += f" Basado en la grabación de audio #{audio_record_id}."
    
    db.commit()
    return diagnosis


def process_audio_pipeline(
    db: Session, 
    audio_record_id: int, 
    user_id: Optional[int] = None
) -> Dict:
    """
    Función principal del pipeline: procesa audio y crea diagnóstico preliminar.
    
    Argumentos:
        db: Sesión de base de datos
        audio_record_id: ID del registro de audio a procesar
        user_id: ID opcional del usuario; se toma del audio si no se entrega
        
    Retorna:
        Diccionario con resultados del procesamiento
    """
    # Obtener registro de audio.
    audio_record = db.query(AudioRecord).filter(AudioRecord.id == audio_record_id).first()
    if not audio_record:
        raise AudioPipelineError(f"Registro de audio {audio_record_id} no encontrado")
    
    # Obtener user_id desde el audio si no fue proporcionado.
    if user_id is None:
        user_id = audio_record.user_id
    
    # Verificar si ya fue procesado.
    if audio_record.status in {"processed", "transcribed"}:
        logger.info(f"El registro de audio {audio_record_id} ya fue procesado")
        features = load_feature_set_payload(get_latest_feature_set(db, audio_record_id))
        # Compatibilidad: registros antiguos pueden tener biomarcadores en notes.
        if not features and audio_record.notes:
            try:
                notes_data = json.loads(audio_record.notes)
                if "extracted_features" in notes_data:
                    features = notes_data["extracted_features"]
            except Exception:
                pass
        
        if features:
            return {
                "audio_record_id": audio_record_id,
                "status": "already_processed",
                "features": features,
                "message": "El audio ya había sido procesado"
            }
        else:
            # Reprocesar si no se encontraron biomarcadores.
            logger.info(f"El audio {audio_record_id} figura como procesado, pero no tiene biomarcadores; se reprocesará")
    
    try:
        # Actualizar estado a procesamiento.
        audio_record.status = "processing"
        audio_record.updated_at = datetime.now(timezone.utc)
        db.commit()

        # --- COMPUERTA DE CONTROL DE CALIDAD ---
        # Ejecutar QA/QC antes de extraer biomarcadores; si falla, el audio
        # queda marcado como rechazado y no se calculan features.
        from app.services.quality_control import run_quality_check

        qc_report = run_quality_check(db, audio_record_id)
        if not qc_report.is_valid:
            reason = qc_report.rejection_reason or "El audio no superó el control de calidad"
            logger.warning(f"QA/QC rechazó el registro de audio {audio_record_id}: {reason}")
            raise AudioPipelineError(
                f"Control de calidad rechazado: {reason}"
            )

        # Extraer biomarcadores usando el servicio de procesamiento de audio.
        features = process_audio_file(audio_record_id, db)
        if not features:
            # Fallback: intentar extracción directa.
            logger.info("process_audio_file retornó None; se intentará extracción directa")
            backend = get_storage_backend()
            audio_bytes = backend.load(audio_record.storage_path)
            if not audio_bytes:
                raise AudioProcessingError("No se pudo cargar el archivo de audio desde almacenamiento")
            
            features = extract_features_from_audio(
                audio_bytes,
                source_name=audio_record.original_filename or audio_record.stored_filename,
            )
        
        # --- SANEAMIENTO TEMPORAL DE FEATURES (DEMO) ---
        # Aplica clamping a los valores fuera de rango para que el modelo
        # pueda recibir parámetros coherentes incluso si la grabación fue
        # ruidosa o de baja calidad.  Esto es una solución temporal que
        # será reemplazada por un mejor preprocesamiento de audio.
        raw_features = dict(features)  # conservar originales para depuración
        features = sanitize_features(features)

        # Validar biomarcadores.
        is_valid, missing_features = validate_features_for_prediction(features)
        if not is_valid:
            logger.warning(f"Biomarcadores faltantes o inválidos: {missing_features}; se usarán los disponibles")

        # Validar calidad de las features contra rangos UCI.
        quality = validate_features(features)
        quality_score = get_feature_quality_score(features)
        
        if not quality["valid"]:
            error_msg = (
                f"Extracción de audio no confiable: {quality['message']}. "
                f"Puntaje de calidad: {quality_score:.1%}. "
                f"Las features extraídas no se asemejan al dataset de entrenamiento."
            )
            logger.warning(f"Calidad de features rechazada para audio {audio_record_id}: {error_msg}")
            
            # Almacenar features igual para depuración, pero marcar como fallido
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


        feature_set = store_biomarker_feature_set(
            db=db,
            audio_record_id=audio_record_id,
            features=features,
            missing_features=missing_features,
        )
        
        # Crear diagnóstico preliminar de Parkinson.
        diagnosis = create_parkinson_diagnosis(db, user_id, features, audio_record_id)


        # Vincular diagnóstico en notes; los biomarcadores viven en BiomarkerFeature.
        store_processing_result(db, audio_record_id, diagnosis.id)
        
        logger.info(f"Pipeline de audio procesado correctamente para el registro {audio_record_id}")
        
        return {
            "audio_record_id": audio_record_id,
            "status": "success",
            "features": features,
            "diagnosis_id": diagnosis.id,
            "prediction": "positive" if diagnosis.final_description and diagnosis.final_description.startswith("Posibles indicadores") else "negative",
            "probability": float(next((d.probability for d in diagnosis.details), 0.0)),
            "message": diagnosis.final_description,
            "feature_set_id": feature_set.id,
            "extractor_version": feature_set.extractor_version,
            "feature_schema_version": feature_set.feature_schema_version,
            "partial_features": feature_set.is_partial,
        }
        
    except Exception as e:
        logger.error(f"Falló el pipeline de audio para el registro {audio_record_id}: {str(e)}", exc_info=True)
        audio_record.status = "failed"
        audio_record.notes = json.dumps({
            "processing_error": str(e),
        })
        audio_record.updated_at = datetime.now(timezone.utc)
        db.commit()
        raise AudioPipelineError(f"Falló el pipeline de audio: {str(e)}")


def batch_process_user_audio(
    db: Session, 
    user_id: int, 
    limit: int = 10
) -> List[Dict]:
    """
    Procesa varios registros de audio de un usuario.
    
    Argumentos:
        db: Sesión de base de datos
        user_id: ID del usuario
        limit: Máximo número de registros a procesar
        
    Retorna:
        Lista con resultados del procesamiento
    """
    # Obtener registros no procesados del usuario.
    audio_records = db.query(AudioRecord).filter(
        AudioRecord.user_id == user_id,
        AudioRecord.status.in_(["uploaded", "failed"]),  # Reintentar fallidos.
        AudioRecord.deleted_at.is_(None)
    ).order_by(AudioRecord.created_at.desc()).limit(limit).all()
    
    results = []
    for record in audio_records:
        try:
            result = process_audio_pipeline(db, record.id, user_id)
            results.append(result)
        except Exception as e:
            results.append({
                "audio_record_id": record.id,
                "status": "failed",
                "error": str(e)
            })
    
    return results


def get_audio_analysis_summary(db: Session, user_id: int) -> Dict:
    """
    Obtiene el resumen de análisis de audio de un usuario.
    
    Argumentos:
        db: Sesión de base de datos
        user_id: ID del usuario
        
    Retorna:
        Diccionario de resumen
    """
    # Contar registros de audio por estado.
    status_counts = {}
    audio_records = db.query(AudioRecord).filter(
        AudioRecord.user_id == user_id,
        AudioRecord.deleted_at.is_(None)
    ).all()
    
    for record in audio_records:
        status_counts[record.status] = status_counts.get(record.status, 0) + 1
    
    # Obtener diagnósticos recientes.
    recent_diagnoses = db.query(Diagnosis).filter(
        Diagnosis.user_id == user_id
    ).order_by(Diagnosis.generated_at.desc()).limit(5).all()
    
    # Extraer biomarcadores de audios procesados.
    processed_features = []
    for record in audio_records:
        if record.status == "processed":
            try:
                features = load_feature_set_payload(get_latest_feature_set(db, record.id))
                if not features and record.notes:
                    notes_data = json.loads(record.notes)
                    features = notes_data.get("extracted_features", {})

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
                "description": d.final_description or "Sin descripción"
            }
            for d in recent_diagnoses
        ],
        "processed_features_summary": processed_features
    }

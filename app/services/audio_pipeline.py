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
    AudioProcessingError
)
from app.services.audio_quality import (
    analyze_audio_quality,
    store_audio_quality_report,
    AudioQualityError,
)
from app.services.storage_service import get_storage_backend
from app.services.voice_biomarkers import (
    VoiceBiomarkerError,
    prepare_audio_for_voice_biomarkers,
    cleanup_prepared_audio,
    build_parkinson_features_parselmouth_primary,
)

logger = logging.getLogger(__name__)


class AudioPipelineError(Exception):
    """Excepción personalizada para errores del pipeline de audio."""
    pass


def validate_features_for_prediction(features: Dict[str, float]) -> Tuple[bool, List[str], List[str]]:
    """
    Valida que todos los biomarcadores requeridos por Parkinson existan y sean válidos.
    
    Argumentos:
        features: Diccionario de biomarcadores acústicos extraídos
        
    Returns:
        Tuple of (is_valid, missing_features)
    """
    missing_features = []
    invalid_features = []
    
    for feature in PARK_FEATURE_ORDER:
        if feature not in features:
            missing_features.append(feature)
            continue
            
        value = features[feature]
        if not isinstance(value, (int, float)) or not float('-inf') < value < float('inf'):
            # NaN or infinite values are invalid
            missing_features.append(feature)
    
    return len(missing_features) == 0 and len(invalid_features) == 0, missing_features, invalid_features


def get_latest_biomarker_features(db: Session, audio_record_id: int) -> Optional[BiomarkerFeature]:
    return (
        db.query(BiomarkerFeature)
        .filter(BiomarkerFeature.audio_record_id == audio_record_id)
        .order_by(BiomarkerFeature.created_at.desc(), BiomarkerFeature.id.desc())
        .first()
    )


def _json_safe_features(features: Dict[str, float]) -> Dict[str, Optional[float]]:
    safe_features: Dict[str, Optional[float]] = {}
    for key, value in features.items():
        try:
            metric = float(value)
        except (TypeError, ValueError):
            safe_features[key] = None
            continue

        if float("-inf") < metric < float("inf"):
            safe_features[key] = metric
        else:
            safe_features[key] = None
    return safe_features


def store_processing_result(
    db: Session,
    audio_record_id: int,
    features: Dict[str, float],
    diagnosis_id: Optional[int] = None,
) -> None:
    """
    Store extracted features in the audio record as JSON.
    
    Args:
        db: Database session
        audio_record_id: ID of the audio record
        features: Dictionary of extracted features
    """
    audio_record = db.query(AudioRecord).filter(AudioRecord.id == audio_record_id).first()
    if not audio_record:
        raise AudioPipelineError(f"Audio record {audio_record_id} not found")
    
    notes_payload = {
        "extracted_features": features,
    }
    if diagnosis_id is not None:
        notes_payload["diagnosis_id"] = diagnosis_id

    # Merge any existing non-JSON notes as metadata.
    if audio_record.notes:
        try:
            existing_notes = json.loads(audio_record.notes)
            if isinstance(existing_notes, dict):
                existing_notes.update(notes_payload)
                notes_payload = existing_notes
            else:
                notes_payload["original_notes"] = existing_notes
        except json.JSONDecodeError:
            notes_payload["original_notes"] = audio_record.notes

    audio_record.notes = json.dumps(notes_payload, indent=2)
    
    # Update status and timestamp
    audio_record.status = "processed"
    audio_record.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except IntegrityError:
        # Backward compatibility for environments with older status constraints.
        db.rollback()
        audio_record = db.query(AudioRecord).filter(AudioRecord.id == audio_record_id).first()
        if not audio_record:
            raise AudioPipelineError(f"Audio record {audio_record_id} not found after rollback")

        audio_record.notes = json.dumps(notes_payload, indent=2)
        audio_record.status = "transcribed"
        audio_record.updated_at = datetime.now(timezone.utc)
        db.commit()


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
    
    # Check if already processed
    if audio_record.status in {"processed", "transcribed"}:
        logger.info(f"Audio record {audio_record_id} already processed")
        # Try to extract features from notes
        features = {}
        if audio_record.notes:
            try:
                notes_data = json.loads(audio_record.notes)
                if 'extracted_features' in notes_data:
                    features = notes_data['extracted_features']
            except:
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
        # Update status to processing
        audio_record.status = "processing"
        audio_record.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        # Extract features using audio_processing service
        features = process_audio_file(audio_record_id, db)
        if not features:
            # Fallback: try direct extraction
            logger.info(f"process_audio_file returned None, trying direct extraction")
            backend = get_storage_backend()
            audio_bytes = backend.load(audio_record.storage_path)
            if not audio_bytes:
                raise AudioProcessingError(f"Could not load audio file from storage")
            
            features = extract_features_from_audio(
                audio_bytes,
                source_name=audio_record.original_filename or audio_record.stored_filename,
            )
            audio_record.status = "features_extracted"
            db.commit()
        finally:
            cleanup_prepared_audio(prepared_audio)
        
        # Validate features
        is_valid, missing_features = validate_features_for_prediction(features)
        if not is_valid:
            logger.warning(f"Missing features: {missing_features}, using available features")
        
        # Create Parkinson diagnosis
        diagnosis = create_parkinson_diagnosis(db, user_id, features, audio_record_id)

        # Store features in audio record with diagnosis linkage
        store_extracted_features(db, audio_record_id, features, diagnosis.id)
        
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
        AudioRecord.status.in_(["uploaded", "failed"]),  # Retry failed ones
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
    
    # Extract features from processed audio
    processed_features = []
    for record in audio_records:
        if record.status == "processed" and record.notes:
            try:
                notes_data = json.loads(record.notes)
                if 'extracted_features' in notes_data:
                    features = notes_data['extracted_features']
                    # Add basic feature summary
                    if 'MDVP:Fo(Hz)' in features:
                        processed_features.append({
                            'audio_id': record.id,
                            'created_at': record.created_at,
                            'fundamental_frequency': features['MDVP:Fo(Hz)'],
                            'jitter': features.get('MDVP:Jitter(%)', 0),
                            'shimmer': features.get('MDVP:Shimmer', 0),
                            'hnr': features.get('HNR', 0)
                        })
            except:
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

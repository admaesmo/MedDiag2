"""
Audio pipeline service - orchestrates the complete audio processing workflow:
1. Upload audio file
2. Extract acoustic features
3. Run Parkinson's prediction
4. Store results
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

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

EXTRACTOR_VERSION = "parselmouth-primary-2.0"
FEATURE_SCHEMA_VERSION = "parkinson-oxford-22-v1"


class AudioPipelineError(Exception):
    """Custom exception for audio pipeline errors."""
    pass


def validate_features_for_prediction(features: Dict[str, float]) -> Tuple[bool, List[str], List[str]]:
    """
    Validate that all required Parkinson features are present and have valid values.
    
    Args:
        features: Dictionary of extracted acoustic features
        
    Returns:
        Tuple of (is_valid, missing_features, invalid_features)
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
            invalid_features.append(feature)
    
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


def store_extracted_features(
    db: Session,
    audio_record_id: int,
    features: Dict[str, float],
    diagnosis_id: Optional[int] = None,
    feature_validation: Optional[Dict[str, object]] = None,
) -> None:
    """
    Store extracted features in the feature store.
    
    Args:
        db: Database session
        audio_record_id: ID of the audio record
        features: Dictionary of extracted features
    """
    audio_record = db.query(AudioRecord).filter(AudioRecord.id == audio_record_id).first()
    if not audio_record:
        raise AudioPipelineError(f"Audio record {audio_record_id} not found")

    feature_row = BiomarkerFeature(
        audio_record_id=audio_record_id,
        extractor_version=EXTRACTOR_VERSION,
        feature_schema_version=FEATURE_SCHEMA_VERSION,
        features_json=_json_safe_features(features),
        feature_status="complete",
        ready_for_inference=True,
        missing_features_json=(feature_validation or {}).get("missing_features", []),
        invalid_features_json=(feature_validation or {}).get("invalid_features", []),
        diagnosis_id=diagnosis_id,
    )
    db.add(feature_row)

    audio_record.status = "inference_completed" if diagnosis_id is not None else "features_extracted"
    audio_record.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except IntegrityError:
        # Backward compatibility for environments with older status constraints.
        db.rollback()
        audio_record = db.query(AudioRecord).filter(AudioRecord.id == audio_record_id).first()
        if not audio_record:
            raise AudioPipelineError(f"Audio record {audio_record_id} not found after rollback")
        feature_row = BiomarkerFeature(
            audio_record_id=audio_record_id,
            extractor_version=EXTRACTOR_VERSION,
            feature_schema_version=FEATURE_SCHEMA_VERSION,
            features_json=_json_safe_features(features),
            feature_status="complete",
            ready_for_inference=True,
            missing_features_json=(feature_validation or {}).get("missing_features", []),
            invalid_features_json=(feature_validation or {}).get("invalid_features", []),
            diagnosis_id=diagnosis_id,
        )
        db.add(feature_row)
        audio_record.status = "processed"
        audio_record.updated_at = datetime.now(timezone.utc)
        db.commit()


def store_partial_features(
    db: Session,
    audio_record_id: int,
    features: Dict[str, float],
    missing_features: List[str],
    invalid_features: List[str],
    message: str,
) -> None:
    """
    Persist extracted-but-incomplete features with explicit traceability and
    mark the audio record as not ready for inference.
    """
    audio_record = db.query(AudioRecord).filter(AudioRecord.id == audio_record_id).first()
    if not audio_record:
        raise AudioPipelineError(f"Audio record {audio_record_id} not found")

    feature_row = BiomarkerFeature(
        audio_record_id=audio_record_id,
        extractor_version=EXTRACTOR_VERSION,
        feature_schema_version=FEATURE_SCHEMA_VERSION,
        features_json=_json_safe_features(features),
        feature_status="partial",
        ready_for_inference=False,
        missing_features_json=missing_features,
        invalid_features_json=invalid_features,
    )
    db.add(feature_row)
    audio_record.notes = json.dumps({"processing_error": message})
    audio_record.status = "partial_features"
    audio_record.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        audio_record = db.query(AudioRecord).filter(AudioRecord.id == audio_record_id).first()
        if not audio_record:
            raise AudioPipelineError(f"Audio record {audio_record_id} not found after rollback")
        audio_record.notes = json.dumps({"processing_error": message})
        audio_record.status = "failed"
        audio_record.updated_at = datetime.now(timezone.utc)
        db.commit()


def create_parkinson_diagnosis(
    db: Session, 
    user_id: int, 
    features: Dict[str, float],
    audio_record_id: Optional[int] = None
) -> Diagnosis:
    """
    Create a Parkinson diagnosis based on extracted audio features.
    
    Args:
        db: Database session
        user_id: User ID
        features: Dictionary of extracted acoustic features
        audio_record_id: Optional audio record ID that this diagnosis is based on
        
    Returns:
        The created Diagnosis object
    """
    # Run prediction
    try:
        prediction_label, probability = predict_parkinson(features)
    except Exception as e:
        logger.error(f"Failed to run Parkinson prediction: {str(e)}", exc_info=True)
        raise AudioPipelineError(f"Prediction failed: {str(e)}")
    
    # Create diagnosis record
    diagnosis = Diagnosis(
        user_id=user_id,
        generated_at=datetime.now(timezone.utc),
        status="pending",
        final_description="Parkinson's diagnosis based on voice analysis."
    )
    db.add(diagnosis)
    db.flush()
    
    # Get Parkinson disease record
    parkinson_disease = db.query(Disease).filter(Disease.disease_code == "PARK").first()
    if not parkinson_disease:
        raise AudioPipelineError("Parkinson disease record not found in database")
    
    # Create diagnosis detail
    diagnosis_detail = DiagnosisDetail(
        diagnosis_id=diagnosis.id,
        disease_id=parkinson_disease.id,
        probability=probability
    )
    db.add(diagnosis_detail)
    
    # Update diagnosis with appropriate message
    if prediction_label == 1:
        diagnosis.final_description = f"Possible Parkinson's detected with {probability:.1%} confidence. Please consult a neurologist."
    else:
        diagnosis.final_description = f"No significant Parkinson's indicators detected ({probability:.1%} confidence)."
    
    # Link audio record if provided
    if audio_record_id:
        # Could store this relationship in notes or a separate field
        if not diagnosis.final_description:
            diagnosis.final_description = ""
        diagnosis.final_description += f" Based on audio recording #{audio_record_id}."
    
    db.commit()
    return diagnosis


def process_audio_pipeline(
    db: Session, 
    audio_record_id: int, 
    user_id: Optional[int] = None
) -> Dict:
    """
    Main audio pipeline function: process audio and create diagnosis.
    
    Args:
        db: Database session
        audio_record_id: ID of the audio record to process
        user_id: Optional user ID (will be fetched from audio record if not provided)
        
    Returns:
        Dictionary with processing results
    """
    # Get audio record
    audio_record = db.query(AudioRecord).filter(AudioRecord.id == audio_record_id).first()
    if not audio_record:
        raise AudioPipelineError(f"Audio record {audio_record_id} not found")
    
    # Get user_id from audio record if not provided
    if user_id is None:
        user_id = audio_record.user_id
    
    # Check if already processed
    if audio_record.status in {"inference_completed", "processed", "transcribed"}:
        logger.info(f"Audio record {audio_record_id} already processed")
        feature_row = get_latest_biomarker_features(db, audio_record_id)
        features = feature_row.features_json if feature_row else {}

        # Legacy fallback for records created before biomarker_features existed.
        if not features and audio_record.notes:
            try:
                notes_data = json.loads(audio_record.notes)
                if "extracted_features" in notes_data:
                    features = notes_data["extracted_features"]
            except json.JSONDecodeError:
                pass
        
        if features:
            return {
                "audio_record_id": audio_record_id,
                "status": "already_processed",
                "features": features,
                "message": "Audio was previously processed"
            }
        else:
            # Reprocess if features not found
            logger.info(f"Audio record {audio_record_id} marked as processed but features not found, reprocessing")
    
    try:
        # Update status to preprocessing
        audio_record.status = "preprocessing"
        audio_record.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        backend = get_storage_backend()
        audio_bytes = backend.load(audio_record.storage_path)
        if not audio_bytes:
            raise AudioProcessingError("Could not load audio file from storage")

        # Default extraction route: Parselmouth-first.
        prepared_audio = None
        try:
            prepared_audio = prepare_audio_for_voice_biomarkers(
                audio_bytes=audio_bytes,
                source_name=audio_record.original_filename or audio_record.stored_filename,
            )
            audio_record.duration_seconds = prepared_audio.duration_seconds
            audio_record.status = "quality_checked"
            quality = analyze_audio_quality(prepared_audio)
            store_audio_quality_report(db, audio_record_id, quality)
            if not quality.is_valid:
                audio_record.status = "rejected"
                audio_record.notes = json.dumps({
                    "processing_error": quality.rejection_reason or "Audio quality is not valid for inference.",
                })
                audio_record.updated_at = datetime.now(timezone.utc)
                db.commit()
                return {
                    "audio_record_id": audio_record_id,
                    "status": "rejected",
                    "message": quality.rejection_reason or "Audio quality is not valid for inference.",
                }
            audio_record.updated_at = datetime.now(timezone.utc)
            db.commit()

            features = build_parkinson_features_parselmouth_primary(prepared_audio)
            audio_record.status = "features_extracted"
            db.commit()
        except (VoiceBiomarkerError, AudioQualityError) as exc:
            logger.warning(
                "Parselmouth-first extraction failed for audio %s, using support extractor fallback. Error: %s",
                audio_record_id,
                exc,
            )
            features = extract_features_from_audio(
                audio_bytes,
                source_name=audio_record.original_filename or audio_record.stored_filename,
            )
            audio_record.status = "features_extracted"
            db.commit()
        finally:
            cleanup_prepared_audio(prepared_audio)
        
        # Validate features
        is_valid, missing_features, invalid_features = validate_features_for_prediction(features)
        if not is_valid:
            message = (
                "Incomplete Parkinson feature vector. "
                "Inference was blocked to avoid unreliable predictions."
            )
            logger.warning(
                "%s Missing features=%s, invalid features=%s",
                message,
                missing_features,
                invalid_features,
            )
            store_partial_features(
                db=db,
                audio_record_id=audio_record_id,
                features=features,
                missing_features=missing_features,
                invalid_features=invalid_features,
                message=message,
            )
            return {
                "audio_record_id": audio_record_id,
                "status": "partial_features",
                "features": features,
                "missing_features": missing_features,
                "invalid_features": invalid_features,
                "message": message,
            }
        
        # Create Parkinson diagnosis
        diagnosis = create_parkinson_diagnosis(db, user_id, features, audio_record_id)

        # Store features in audio record with diagnosis linkage
        store_extracted_features(
            db,
            audio_record_id,
            features,
            diagnosis.id,
            feature_validation={
                "ready_for_inference": True,
                "missing_features": [],
                "invalid_features": [],
            },
        )
        
        logger.info(f"Successfully processed audio pipeline for record {audio_record_id}")
        
        return {
            "audio_record_id": audio_record_id,
            "status": "success",
            "features": features,
            "diagnosis_id": diagnosis.id,
            "prediction": "positive" if diagnosis.final_description and "detected" in diagnosis.final_description.lower() else "negative",
            "probability": float(next((d.probability for d in diagnosis.details), 0.0)),
            "message": diagnosis.final_description
        }
        
    except Exception as e:
        logger.error(f"Audio pipeline failed for record {audio_record_id}: {str(e)}", exc_info=True)
        audio_record.status = "failed"
        audio_record.notes = json.dumps({
            "processing_error": str(e),
        })
        audio_record.updated_at = datetime.now(timezone.utc)
        db.commit()
        raise AudioPipelineError(f"Audio pipeline failed: {str(e)}")


def batch_process_user_audio(
    db: Session, 
    user_id: int, 
    limit: int = 10
) -> List[Dict]:
    """
    Process multiple audio records for a user.
    
    Args:
        db: Database session
        user_id: User ID
        limit: Maximum number of records to process
        
    Returns:
        List of processing results
    """
    # Get unprocessed audio records for user
    audio_records = db.query(AudioRecord).filter(
        AudioRecord.user_id == user_id,
        AudioRecord.status.in_(["uploaded", "failed", "partial_features", "rejected"]),  # Retry incomplete ones
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
    Get summary of audio analysis for a user.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        Summary dictionary
    """
    # Count audio records by status
    status_counts = {}
    audio_records = db.query(AudioRecord).filter(
        AudioRecord.user_id == user_id,
        AudioRecord.deleted_at.is_(None)
    ).all()
    
    for record in audio_records:
        status_counts[record.status] = status_counts.get(record.status, 0) + 1
    
    # Get recent diagnoses
    recent_diagnoses = db.query(Diagnosis).filter(
        Diagnosis.user_id == user_id
    ).order_by(Diagnosis.generated_at.desc()).limit(5).all()
    
    # Extract features from feature store.
    processed_features = []
    for record in audio_records:
        feature_row = get_latest_biomarker_features(db, record.id)
        if not feature_row:
            continue
        features = feature_row.features_json or {}
        if 'MDVP:Fo(Hz)' in features:
            processed_features.append({
                'audio_id': record.id,
                'created_at': record.created_at,
                'fundamental_frequency': features['MDVP:Fo(Hz)'],
                'jitter': features.get('MDVP:Jitter(%)', 0),
                'shimmer': features.get('MDVP:Shimmer', 0),
                'hnr': features.get('HNR', 0),
                'feature_status': feature_row.feature_status,
            })
    
    return {
        "total_audio_records": len(audio_records),
        "status_counts": status_counts,
        "recent_diagnoses": [
            {
                "id": d.id,
                "generated_at": d.generated_at,
                "status": d.status,
                "description": d.final_description or "No description"
            }
            for d in recent_diagnoses
        ],
        "processed_features_summary": processed_features
    }

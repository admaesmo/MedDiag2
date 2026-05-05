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
    process_audio_file,
    AudioProcessingError
)
from app.services.storage_service import get_storage_backend

logger = logging.getLogger(__name__)
FEATURE_EXTRACTOR_VERSION = "audio-processing+nonlinear-v1"
FEATURE_SCHEMA_VERSION = "parkinson-oxford-22-v1"


class AudioPipelineError(Exception):
    """Custom exception for audio pipeline errors."""
    pass


def validate_features_for_prediction(features: Dict[str, float]) -> Tuple[bool, List[str]]:
    """
    Validate that all required Parkinson features are present and have valid values.
    
    Args:
        features: Dictionary of extracted acoustic features
        
    Returns:
        Tuple of (is_valid, missing_features)
    """
    missing_features = []
    
    for feature in PARK_FEATURE_ORDER:
        if feature not in features:
            missing_features.append(feature)
            continue
            
        value = features[feature]
        if not isinstance(value, (int, float)) or not float('-inf') < value < float('inf'):
            # NaN or infinite values are invalid
            missing_features.append(feature)
    
    return len(missing_features) == 0, missing_features


def store_extracted_features(
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
    if audio_record.status in {"processed", "transcribed"}:
        logger.info(f"Audio record {audio_record_id} already processed")
        features = load_feature_set_payload(get_latest_feature_set(db, audio_record_id))
        if audio_record.notes:
            try:
                notes_data = json.loads(audio_record.notes)
                if "extracted_features" in notes_data and not features:
                    features = notes_data["extracted_features"]
            except Exception:
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
        
        # Validate features
        is_valid, missing_features = validate_features_for_prediction(features)
        if not is_valid:
            logger.warning(f"Missing features: {missing_features}, using available features")

        feature_set = store_biomarker_feature_set(
            db=db,
            audio_record_id=audio_record_id,
            features=features,
            missing_features=missing_features,
        )
        
        # Create Parkinson diagnosis
        diagnosis = create_parkinson_diagnosis(db, user_id, features, audio_record_id)

        # Store features in audio record with diagnosis linkage
        store_extracted_features(db, audio_record_id, features, diagnosis.id)
        
        logger.info(f"Successfully processed audio pipeline for record {audio_record_id}")
        
        return {
            "audio_record_id": audio_record_id,
            "status": "success",
            "features": features,
            "diagnosis_id": diagnosis.id,
            "prediction": "positive" if diagnosis.final_description and "detected" in diagnosis.final_description.lower() else "negative",
            "probability": float(next((d.probability for d in diagnosis.details), 0.0)),
            "message": diagnosis.final_description,
            "feature_set_id": feature_set.id,
            "extractor_version": feature_set.extractor_version,
            "feature_schema_version": feature_set.feature_schema_version,
            "partial_features": feature_set.is_partial,
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
    
    # Extract features from processed audio
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
                "description": d.final_description or "No description"
            }
            for d in recent_diagnoses
        ],
        "processed_features_summary": processed_features
    }

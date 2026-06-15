"""
Orquestación de sesiones de voz con múltiples tomas.

Responsabilidad: dado un VoiceSession con ≥ 2 tomas válidas procesadas,
agregar los biomarcadores por mediana y producir un Diagnosis.

El pipeline por toma (process_audio_pipeline) no se modifica.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import numpy as np
from sqlalchemy.orm import Session

from app.models import AudioRecord, BiomarkerFeature, VoiceSession
from app.services.audio_pipeline import (
    create_parkinson_diagnosis,
    load_feature_set_payload,
    get_latest_feature_set,
    AudioPipelineError,
)
from app.services.constants import PARKINSON_FEATURE_ORDER

logger = logging.getLogger(__name__)

MIN_VALID_TAKES = 2


class SessionPipelineError(Exception):
    pass


# ---------------------------------------------------------------------------
# Tomas activas (excluye borrado lógico)
# ---------------------------------------------------------------------------
#
# La relación VoiceSession.takes NO filtra deleted_at, así que toda lectura de
# tomas debe pasar por este helper. De lo contrario las tomas retiradas siguen
# apareciendo en la UI y desfasan la numeración de slots (ver
# Documentacion/analisis_multitoma_mejoras.md).

def active_takes(session: VoiceSession) -> List[AudioRecord]:
    """Devuelve las tomas no borradas de la sesión, ordenadas por take_number."""
    return [t for t in session.takes if t.deleted_at is None]


# ---------------------------------------------------------------------------
# Agregación de biomarcadores
# ---------------------------------------------------------------------------

def aggregate_takes(
    feature_sets: List[Dict[str, float]],
) -> Tuple[Dict[str, float], Dict[str, float], float]:
    """
    Agrega N vectores de biomarcadores en uno solo.

    Returns
    -------
    medians : Dict[str, float]
        Mediana por biomarcador — vector que recibe el modelo.
    cvs : Dict[str, float]
        Coeficiente de variación (std/|mean|) por biomarcador.
        Mide la inconsistencia entre tomas; alta CV puede indicar
        inestabilidad fonatoria real o problemas de grabación.
    session_confidence : float
        1 - mean(CV). 0 = muy inconsistente, 1 = tomas idénticas.
    """
    stacked: Dict[str, List[float]] = {f: [] for f in PARKINSON_FEATURE_ORDER}

    for fs in feature_sets:
        for feature in PARKINSON_FEATURE_ORDER:
            if feature in fs and np.isfinite(fs[feature]):
                stacked[feature].append(fs[feature])

    medians: Dict[str, float] = {}
    cvs: Dict[str, float] = {}

    for feature, values in stacked.items():
        if not values:
            continue
        arr = np.array(values)
        medians[feature] = float(np.median(arr))
        mean_v = float(np.mean(arr))
        cvs[feature] = float(np.std(arr) / (abs(mean_v) + 1e-6))

    session_confidence = 1.0 - float(np.mean(list(cvs.values()))) if cvs else 0.0
    session_confidence = max(0.0, min(1.0, session_confidence))

    return medians, cvs, session_confidence


# ---------------------------------------------------------------------------
# Carga de tomas válidas
# ---------------------------------------------------------------------------

def _load_valid_feature_sets(
    db: Session, session: VoiceSession
) -> Tuple[List[Dict[str, float]], List[int]]:
    """
    Devuelve (lista_de_feature_dicts, lista_de_audio_record_ids) para las
    tomas cuyo audio_record está en estado 'processed' y tiene BiomarkerFeature.
    """
    valid_features: List[Dict[str, float]] = []
    valid_ids: List[int] = []

    for take in active_takes(session):
        if take.status != "processed":
            continue
        row = get_latest_feature_set(db, take.id)
        if row is None:
            continue
        payload = load_feature_set_payload(row)
        if payload:
            valid_features.append(payload)
            valid_ids.append(take.id)

    return valid_features, valid_ids


# ---------------------------------------------------------------------------
# Pipeline principal de sesión
# ---------------------------------------------------------------------------

def analyze_session(db: Session, session_id: int, user_id: int) -> Dict:
    """
    Agrega las tomas válidas de la sesión y genera un Diagnosis.

    Flujo:
      1. Cargar sesión y validar estado
      2. Recolectar feature sets de tomas procesadas
      3. Verificar mínimo de tomas válidas
      4. Agregar por mediana
      5. Crear Diagnosis con el vector agregado
      6. Persistir resultados en VoiceSession
    """
    session = db.query(VoiceSession).filter(VoiceSession.id == session_id).first()
    if not session:
        raise SessionPipelineError(f"Sesión {session_id} no encontrada")

    if session.user_id != user_id:
        raise SessionPipelineError("Acceso denegado a esta sesión")

    if session.status == "completed":
        return _build_result_from_session(session)

    if session.status == "processing":
        raise SessionPipelineError("La sesión ya está siendo procesada")

    # --- Recolectar tomas válidas ---
    valid_feature_sets, valid_ids = _load_valid_feature_sets(db, session)

    if len(valid_feature_sets) < MIN_VALID_TAKES:
        raise SessionPipelineError(
            f"Se necesitan al menos {MIN_VALID_TAKES} tomas válidas (procesadas). "
            f"Tomas válidas actuales: {len(valid_feature_sets)}."
        )

    if len(valid_feature_sets) == 2:
        logger.warning(
            "Sesión %d: operando con solo 2 tomas válidas. "
            "La mediana es equivalente al promedio — sin rechazo de outliers.",
            session_id,
        )

    try:
        session.status = "processing"
        db.commit()

        # --- Agregación ---
        medians, cvs, confidence = aggregate_takes(valid_feature_sets)

        if not medians:
            raise SessionPipelineError("No se pudieron agregar biomarcadores de las tomas")

        # --- Inferencia sobre el vector agregado ---
        diagnosis = create_parkinson_diagnosis(
            db=db,
            user_id=user_id,
            features=medians,
            audio_record_id=None,
        )

        # Enriquecer la descripción con información de sesión
        diagnosis.final_description += (
            f" (Análisis basado en {len(valid_feature_sets)} tomas; "
            f"confianza de sesión: {confidence:.0%})"
        )
        db.flush()

        # --- Persistir resultados en la sesión ---
        session.aggregated_features_json = json.dumps(
            {k: float(v) for k, v in medians.items()}, indent=2
        )
        session.variance_json = json.dumps(
            {k: float(v) for k, v in cvs.items()}, indent=2
        )
        session.valid_takes_count = len(valid_feature_sets)
        session.session_confidence = round(confidence, 4)
        session.diagnosis_id = diagnosis.id
        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)
        db.commit()

        probability = float(next((d.probability for d in diagnosis.details), 0.0))
        prediction = (
            "positive"
            if diagnosis.final_description.startswith("Posibles")
            else "negative"
        )

        logger.info(
            "Sesión %d completada: %d tomas válidas, confianza=%.2f, predicción=%s",
            session_id, len(valid_feature_sets), confidence, prediction,
        )

        return {
            "session_id": session_id,
            "session_uuid": session.uuid,
            "status": "completed",
            "valid_takes_count": len(valid_feature_sets),
            "session_confidence": confidence,
            "aggregated_features": medians,
            "variance_per_feature": cvs,
            "diagnosis_id": diagnosis.id,
            "prediction": prediction,
            "probability": probability,
            "message": diagnosis.final_description,
        }

    except Exception as exc:
        session.status = "failed"
        db.commit()
        logger.error("Análisis de sesión %d fallido: %s", session_id, exc, exc_info=True)
        raise SessionPipelineError(f"Falló el análisis de sesión: {exc}")


def _build_result_from_session(session: VoiceSession) -> Dict:
    """Reconstruye el resultado desde una sesión ya completada."""
    medians = json.loads(session.aggregated_features_json or "{}")
    cvs = json.loads(session.variance_json or "{}")

    return {
        "session_id": session.id,
        "session_uuid": session.uuid,
        "status": "completed",
        "valid_takes_count": session.valid_takes_count,
        "session_confidence": session.session_confidence,
        "aggregated_features": medians,
        "variance_per_feature": cvs,
        "diagnosis_id": session.diagnosis_id,
        "prediction": "already_completed",
        "probability": None,
        "message": "Sesión ya analizada previamente.",
    }


# ---------------------------------------------------------------------------
# Utilidades de sesión
# ---------------------------------------------------------------------------

def get_session_with_takes_summary(db: Session, session: VoiceSession) -> Dict:
    """Construye el resumen de estado de la sesión con detalle de cada toma."""
    from app.services.quality_control import get_latest_quality_report

    takes_summary = []
    for take in active_takes(session):
        qc = get_latest_quality_report(db, take.id)
        takes_summary.append({
            "audio_record_id": take.id,
            "take_number": take.take_number,
            "status": take.status,
            "quality_score": qc.quality_score if qc else None,
            "is_valid": qc.is_valid if qc else None,
            "rejection_reason": qc.rejection_reason if qc else None,
        })

    return {
        "id": session.id,
        "uuid": session.uuid,
        "user_id": session.user_id,
        "max_takes": session.max_takes,
        "status": session.status,
        "valid_takes_count": session.valid_takes_count,
        "session_confidence": session.session_confidence,
        "diagnosis_id": session.diagnosis_id,
        "created_at": session.created_at,
        "completed_at": session.completed_at,
        "takes": takes_summary,
    }


def next_take_number(session: VoiceSession) -> int:
    """
    Devuelve el número de slot libre más bajo dentro de [1, max_takes].

    Solo considera tomas activas (no borradas), de modo que al retirar una toma
    su slot queda disponible y el reintento lo reutiliza (en vez de crear un
    número fuera del rango de slots que la UI renderiza).
    """
    ocupados = {
        t.take_number for t in active_takes(session) if t.take_number is not None
    }
    for n in range(1, session.max_takes + 1):
        if n not in ocupados:
            return n
    # Sin slots libres: caer al siguiente número (el límite se valida aparte).
    return max(ocupados, default=0) + 1


def count_registered_takes(session: VoiceSession) -> int:
    return len(active_takes(session))

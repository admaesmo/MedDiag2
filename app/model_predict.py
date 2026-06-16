"""
Módulo de predicción — carga modelos serializados y ejecuta inferencia.

Modelo de Parkinson — "classic16" (2026-06-16):
El modelo `parkinsons_model_smote.sav` (entrenado con las 22 features del
dataset Oxford, incluyendo las 6 no lineales) predecía positivo casi siempre
en audio real: RPDE/DFA/spread1/spread2/PPE quedan clampeadas al límite del
rango UCI en 74-100% de los audios reales (ver diagnóstico de proyecto,
memoria 2026-06-16). Se reentrenó usando solo las 16 features clásicas
(jitter, shimmer, HNR, F0), y además directamente sobre audio real con
diagnóstico confirmado (dataset figshare DOI 10.6084/m9.figshare.23849127,
81 sujetos), porque un modelo entrenado solo con Oxford (laboratorio) no
transfiere a audio real (AUC ~0.41-0.51 fuera de dominio). Ver
`scripts/retrain_parkinson_classic16.py`.

LIMITACIÓN CONOCIDA: N=81, AUC out-of-fold ~0.64, y el dataset de
entrenamiento tiene un confound de edad no corregido (PD~67a vs HC~48a).
Resultado preliminar, no validado clínicamente — ver memoria de proyecto.

Este módulo aplica el scaler antes de predecir para mantener la
consistencia con el contrato de entrenamiento.

Archivos esperados en ``saved_models/``:
    - parkinsons_model_classic16.sav   (modelo classic16, ver arriba)
    - parkinsons_scaler_classic16.sav  (StandardScaler para modelo classic16)
    - diabetes_model.sav           (modelo de diabetes, sin scaler)
    - heart_disease_model.sav      (modelo cardíaco, sin scaler)
"""

from __future__ import annotations

import logging
import os
import pickle
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv

from app.services.constants import PARKINSON_FEATURE_ORDER, PARKINSON_MODEL_FEATURE_ORDER
from app.services.feature_validator import validate_features, get_feature_quality_score

load_dotenv()

logger = logging.getLogger(__name__)

WORKING_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.getenv("MODEL_DIR", os.path.join(os.path.dirname(WORKING_DIR), "saved_models"))

# ---------------------------------------------------------------------------
# Órdenes de características
# ---------------------------------------------------------------------------

DIABETES_FEATURE_ORDER = [
    "Pregnancies",
    "Glucose",
    "BloodPressure",
    "SkinThickness",
    "Insulin",
    "BMI",
    "DiabetesPedigreeFunction",
    "Age",
]

HEART_FEATURE_ORDER = [
    "age",
    "sex",
    "cp",
    "trestbps",
    "chol",
    "fbs",
    "restecg",
    "thalach",
    "exang",
    "oldpeak",
    "slope",
    "ca",
    "thal",
]

# Alias para compatibilidad con imports existentes.
PARK_FEATURE_ORDER = PARKINSON_FEATURE_ORDER

# ---------------------------------------------------------------------------
# Carga de modelos (una sola vez por proceso)
# ---------------------------------------------------------------------------


def _load_model(filename: str):
    """Carga un modelo/serializado con joblib (preferido) o pickle (legacy)."""
    path = os.path.join(MODEL_DIR, filename)
    try:
        return joblib.load(path)
    except Exception:
        with open(path, "rb") as f:
            return pickle.load(f)


diabetes_model = _load_model("diabetes_model.sav")
heart_model = _load_model("heart_disease_model.sav")

# ---------------------------------------------------------------------------
# Modelo de Parkinson — "classic16", entrenado solo con features clásicas
# sobre audio real (ver docstring del módulo y scripts/retrain_parkinson_classic16.py)
# ---------------------------------------------------------------------------

PARKINSON_CONFIDENCE_THRESHOLD = 0.40
PARKINSON_THRESHOLD = PARKINSON_CONFIDENCE_THRESHOLD
PARKINSON_POSITIVE_MESSAGE = (
    "Veredicto: positivo para Parkinson. Confianza igual o superior al 40%. "
    "Consulte a su médico. (Resultado preliminar, N=81, no validado clínicamente.)"
)
PARKINSON_NEGATIVE_MESSAGE = (
    "Veredicto: no tiene Parkinson. Confianza inferior al 40%. "
    "(Resultado preliminar, N=81, no validado clínicamente.)"
)



try:
    parkinsons_model = _load_model("parkinsons_model_classic16.sav")
    parkinsons_scaler = _load_model("parkinsons_scaler_classic16.sav")
    logger.info(
        "parkinsons_model_classic16.sav + scaler cargados — modelo classic16 listo."
    )
except (FileNotFoundError, Exception):
    parkinsons_model = None
    parkinsons_scaler = None
    logger.error(
        "parkinsons_model_classic16.sav no encontrado — la inferencia de Parkinson "
        "no estará disponible."
    )

# ---------------------------------------------------------------------------
# Lógica de inferencia
# ---------------------------------------------------------------------------


def _predict_binary(
    model,
    ordered_features: List[str],
    features: Dict[str, float],
    scaler=None,
) -> Tuple[int, float]:
    """
    Devuelve clase predicha y probabilidad.

    Si el modelo expone ``predict_proba`` se usa directamente; en caso
    contrario se devuelve una probabilidad de respaldo (1.0 si la clase
    predicha es 1, 0.0 en otro caso).

    Si se proporciona un ``scaler``, las features se estandarizan antes
    de pasar al modelo.
    """
    if scaler is not None:
        x = pd.DataFrame(
            [[float(features[f]) for f in ordered_features]],
            columns=ordered_features,
        )
        x = scaler.transform(x)
    else:
        x = np.array([[float(features[f]) for f in ordered_features]])

    label = int(model.predict(x)[0])

    if hasattr(model, "predict_proba"):
        proba = float(model.predict_proba(x)[0][1])
    else:
        proba = 1.0 if label == 1 else 0.0

    return label, proba


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def predict_diabetes(features: Dict[str, float]) -> Tuple[int, float]:
    return _predict_binary(diabetes_model, DIABETES_FEATURE_ORDER, features)


def predict_heart(features: Dict[str, float]) -> Tuple[int, float]:
    return _predict_binary(heart_model, HEART_FEATURE_ORDER, features)


def predict_parkinson(
    features: Dict[str, float],
    threshold: float = PARKINSON_THRESHOLD,
) -> Tuple[int, float]:
    """
    Predice Parkinson usando el modelo "classic16" + umbral ajustable.

    El modelo usa solo las 16 features clásicas (jitter, shimmer, HNR, F0).
    Las 6 no lineales del esquema completo (RPDE, DFA, spread1, spread2, D2,
    PPE) se ignoran a propósito: su extracción queda clampeada al límite del
    rango UCI en 74-100% de los audios reales, lo que hacía que el modelo
    anterior predijera positivo casi siempre (ver docstring del módulo).

    Parameters
    ----------
    features : Dict[str, float]
        Dict con (al menos) las 16 features clásicas. Puede incluir además
        las 6 no lineales del esquema completo — se ignoran si están.
    threshold : float, optional
        Umbral de probabilidad para clasificación (default 0.40).

    Returns
    -------
    Tuple[int, float]
        (predicción 0/1, probabilidad de Parkinson)
    """
    if parkinsons_model is None or parkinsons_scaler is None:
        raise RuntimeError("Modelo de Parkinson no disponible.")

    x = pd.DataFrame(
        [[float(features[f]) for f in PARKINSON_MODEL_FEATURE_ORDER]],
        columns=PARKINSON_MODEL_FEATURE_ORDER,
    )
    x = parkinsons_scaler.transform(x)
    proba = float(parkinsons_model.predict_proba(x)[0][1])
    label = 1 if proba >= threshold else 0
    return label, proba


def get_parkinson_verdict(
    probability: float,
    threshold: float = PARKINSON_THRESHOLD,
) -> Tuple[int, str]:
    prediction = 1 if probability >= threshold else 0
    message = PARKINSON_POSITIVE_MESSAGE if prediction == 1 else PARKINSON_NEGATIVE_MESSAGE
    return prediction, message

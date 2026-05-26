"""
Módulo de predicción — carga modelos serializados y ejecuta inferencia.

El modelo de Parkinson (XGBoost con SMOTE) fue entrenado sobre datos escalados
con StandardScaler.  Este módulo aplica el scaler antes de predecir para
mantener la consistencia con el contrato de entrenamiento.

Archivos esperados en ``saved_models/``:
    - parkinsons_model_smote.sav   (XGBoost entrenado con SMOTE — versión mejorada)
    - parkinsons_scaler_smote.sav  (StandardScaler para modelo SMOTE)
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
from dotenv import load_dotenv

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

PARK_FEATURE_ORDER = [
    "MDVP:Fo(Hz)", "MDVP:Fhi(Hz)", "MDVP:Flo(Hz)", "MDVP:Jitter(%)", "MDVP:Jitter(Abs)",
    "MDVP:RAP", "MDVP:PPQ", "Jitter:DDP", "MDVP:Shimmer", "MDVP:Shimmer(dB)",
    "Shimmer:APQ3", "Shimmer:APQ5", "MDVP:APQ", "Shimmer:DDA", "NHR", "HNR",
    "RPDE", "DFA", "spread1", "spread2", "D2", "PPE",
]

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
# Modelo de Parkinson — XGBoost entrenado con SMOTE (balanceo de clases)
# ---------------------------------------------------------------------------

PARKINSON_THRESHOLD = 0.85  # umbral ajustado: mejor balance sensibilidad/especificidad para audio real



try:
    parkinsons_model = _load_model("parkinsons_model_smote.sav")
    parkinsons_scaler = _load_model("parkinsons_scaler_smote.sav")
    logger.info(
        "parkinsons_model_smote.sav + scaler cargados — modelo SMOTE listo."
    )
except (FileNotFoundError, Exception):
    parkinsons_model = None
    parkinsons_scaler = None
    logger.error(
        "parkinsons_model_smote.sav no encontrado — la inferencia de Parkinson "
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
    x = np.array([[float(features[f]) for f in ordered_features]])

    if scaler is not None:
        x = scaler.transform(x)

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
    Predice Parkinson usando XGBoost entrenado con SMOTE + umbral ajustable.

    El modelo fue entrenado con balanceo de clases (SMOTE) sobre las 22
    features del dataset UCI Oxford, estandarizadas con StandardScaler.

    Parameters
    ----------
    features : Dict[str, float]
        Las 22 características del dataset UCI Oxford.
    threshold : float, optional
        Umbral de probabilidad para clasificación (default 0.55).

    Returns
    -------
    Tuple[int, float]
        (predicción 0/1, probabilidad de Parkinson)
    """
    if parkinsons_model is None or parkinsons_scaler is None:
        raise RuntimeError("Modelo de Parkinson no disponible.")

    x = np.array([[float(features[f]) for f in PARK_FEATURE_ORDER]])
    x = parkinsons_scaler.transform(x)
    proba = float(parkinsons_model.predict_proba(x)[0][1])
    label = 1 if proba >= threshold else 0
    return label, proba

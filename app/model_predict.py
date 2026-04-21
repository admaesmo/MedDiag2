import os
import pickle
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

WORKING_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.getenv("MODEL_DIR", os.path.join(os.path.dirname(WORKING_DIR), "saved_models"))

# Feature orders used for inference
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


def _load_model(filename: str):
    path = os.path.join(MODEL_DIR, filename)
    with open(path, "rb") as f:
        return pickle.load(f)


# Load models once per process
diabetes_model = _load_model("diabetes_model.sav")
heart_model = _load_model("heart_disease_model.sav")
parkinsons_model = _load_model("parkinsons_model.sav")


def _predict_binary(model, ordered_features: List[str], features: Dict[str, float]) -> Tuple[int, float]:
    """Return predicted class and probability (best effort if no predict_proba)."""
    x = np.array([[float(features[f]) for f in ordered_features]])

    if hasattr(model, "predict_proba"):
        proba = float(model.predict_proba(x)[0][1])
    else:
        pred = model.predict(x)[0]
        # fallback probability when model has no predict_proba
        proba = 1.0 if pred == 1 else 0.0
    label = int(model.predict(x)[0])
    return label, proba

#def _predict_binary(model, ordered_features: List[str], features: Dict[str, float]) -> Tuple[int, float]:
    """Return predicted class and probability (best effort if no predict_proba)."""
    x = np.array([[float(features[f]) for f in ordered_features]])

    supports_proba = hasattr(model, "predict_proba") and bool(getattr(model, "probability", True))
    if supports_proba:
        try:
            proba = float(model.predict_proba(x)[0][1])
        except Exception:
            pred = model.predict(x)[0]
            # fallback probability when predict_proba is not usable at runtime
            proba = 1.0 if pred == 1 else 0.0
    else:
        pred = model.predict(x)[0]
        # fallback probability when model has no predict_proba
        proba = 1.0 if pred == 1 else 0.0
    label = int(model.predict(x)[0])
    return label, proba

def predict_diabetes(features: Dict[str, float]) -> Tuple[int, float]:
    return _predict_binary(diabetes_model, DIABETES_FEATURE_ORDER, features)


def predict_heart(features: Dict[str, float]) -> Tuple[int, float]:
    return _predict_binary(heart_model, HEART_FEATURE_ORDER, features)


def predict_parkinson(features: Dict[str, float]) -> Tuple[int, float]:
    return _predict_binary(parkinsons_model, PARK_FEATURE_ORDER, features)

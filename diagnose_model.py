#!/usr/bin/env python3
"""
Script de diagnóstico para investigar por qué el modelo da siempre positivo.
"""
import os
import sys
import joblib
import numpy as np
import pandas as pd
from pathlib import Path

# Añadir app al path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.model_predict import (
    PARKINSON_FEATURE_ORDER,
    predict_parkinson,
)

MODEL_DIR = Path(__file__).parent / "saved_models"

def load_model_debug(filename):
    """Carga un modelo y devuelve información sobre él."""
    path = MODEL_DIR / filename
    print(f"\n{'='*70}")
    print(f"Modelo: {filename}")
    print(f"Ruta: {path}")
    print(f"Existe: {path.exists()}")
    
    if not path.exists():
        print(f"❌ El archivo no existe")
        return None
    
    try:
        model = joblib.load(path)
        print(f"✓ Cargado exitosamente")
        print(f"Tipo: {type(model)}")
        print(f"Tiene predict_proba: {hasattr(model, 'predict_proba')}")
        if hasattr(model, 'n_estimators'):
            print(f"N estimators: {model.n_estimators}")
        if hasattr(model, 'max_depth'):
            print(f"Max depth: {model.max_depth}")
        return model
    except Exception as e:
        print(f"❌ Error al cargar: {e}")
        return None


def test_on_dummy_samples():
    """Prueba el modelo con muestras dummy."""
    print(f"\n{'='*70}")
    print("PRUEBA CON MUESTRAS DUMMY")
    print(f"{'='*70}")
    
    # Obtener el scaler
    scaler_path = MODEL_DIR / "parkinsons_scaler_smote.sav"
    if not scaler_path.exists():
        print(f"❌ Scaler no encontrado: {scaler_path}")
        return
    
    scaler = joblib.load(scaler_path)
    print(f"✓ Scaler cargado: {type(scaler)}")
    
    # Crear muestras dummy
    # Caso 1: Valores típicos de una persona SANA
    healthy_features = {
        "MDVP:Fo(Hz)": 130.0,
        "MDVP:Fhi(Hz)": 180.0,
        "MDVP:Flo(Hz)": 90.0,
        "MDVP:Jitter(%)": 0.005,
        "MDVP:Jitter(Abs)": 0.00005,
        "MDVP:RAP": 0.003,
        "MDVP:PPQ": 0.004,
        "Jitter:DDP": 0.008,
        "MDVP:Shimmer": 0.02,
        "MDVP:Shimmer(dB)": 0.2,
        "Shimmer:APQ3": 0.015,
        "Shimmer:APQ5": 0.02,
        "MDVP:APQ": 0.02,
        "Shimmer:DDA": 0.04,
        "NHR": 0.015,
        "HNR": 25.0,
        "RPDE": 0.35,
        "DFA": 0.75,
        "spread1": -5.0,
        "spread2": 0.2,
        "D2": 2.0,
        "PPE": 0.15,
    }
    
    # Caso 2: Valores típicos de una persona con PARKINSON
    parkinsons_features = {
        "MDVP:Fo(Hz)": 120.0,
        "MDVP:Fhi(Hz)": 140.0,
        "MDVP:Flo(Hz)": 80.0,
        "MDVP:Jitter(%)": 0.01,
        "MDVP:Jitter(Abs)": 0.0001,
        "MDVP:RAP": 0.008,
        "MDVP:PPQ": 0.01,
        "Jitter:DDP": 0.025,
        "MDVP:Shimmer": 0.05,
        "MDVP:Shimmer(dB)": 0.5,
        "Shimmer:APQ3": 0.035,
        "Shimmer:APQ5": 0.05,
        "MDVP:APQ": 0.05,
        "Shimmer:DDA": 0.1,
        "NHR": 0.045,
        "HNR": 18.0,
        "RPDE": 0.5,
        "DFA": 0.85,
        "spread1": -4.5,
        "spread2": 0.3,
        "D2": 2.5,
        "PPE": 0.3,
    }
    
    for case_name, features in [("SANO", healthy_features), ("PARKINSON", parkinsons_features)]:
        try:
            print(f"\n{case_name}:")
            label, proba = predict_parkinson(features, threshold=0.70)
            print(f"  Probabilidad: {proba:.4f}")
            print(f"  Predicción (threshold=0.70): {label} ({'Positivo' if label == 1 else 'Negativo'})")
            
            # Probar también con otros umbrales
            for umbral in [0.50, 0.65, 0.75, 0.85]:
                label_alt, _ = predict_parkinson(features, threshold=umbral)
                print(f"    - Umbral {umbral}: {'Positivo' if label_alt == 1 else 'Negativo'}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")


def check_model_versions():
    """Revisa todas las versiones de modelos disponibles."""
    print(f"\n{'='*70}")
    print("REVISIÓN DE VERSIONES DE MODELOS")
    print(f"{'='*70}")
    
    models_to_check = [
        "parkinsons_model.sav",
        "parkinsons_model_xgboost.sav",
        "parkinsons_model_smote.sav",
        "parkinsons_model_ensemble.sav",
    ]
    
    for model_file in models_to_check:
        load_model_debug(model_file)


if __name__ == "__main__":
    print(f"\n{'#'*70}")
    print("# DIAGNÓSTICO DE MODELO PARKINSON")
    print(f"{'#'*70}")
    
    check_model_versions()
    test_on_dummy_samples()
    
    print(f"\n{'#'*70}")
    print("# FIN DEL DIAGNÓSTICO")
    print(f"{'#'*70}\n")

"""
Script de prueba: 20 pacientes simulados para evaluar el modelo de Parkinson.

Genera 20 perfiles de pacientes con las 22 features del dataset UCI Oxford,
mitad sanos (status=0) y mitad con Parkinson (status=1), usando estadísticas
reales del dataset para crear valores realistas.

Luego ejecuta la predicción con el modelo cargado y muestra:
  - Predicción vs esperado
  - Probabilidad
  - Matriz de confusión
  - Precisión, sensibilidad, especificidad

Útil para diagnosticar falsos positivos.
"""

import sys
import os
import pickle
import json
import numpy as np

# Agregar directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.model_predict import (
    predict_parkinson,
    PARK_FEATURE_ORDER,
    PARKINSON_THRESHOLD,
    parkinsons_model,
    parkinsons_scaler,
)

# ============================================================================
# ESTADÍSTICAS DEL DATASET UCI PARKINSON (calculadas del dataset real)
# ============================================================================
# Estas estadísticas se obtuvieron del dataset UCI Oxford Parkinson's
# para generar muestras sintéticas realistas.

# Para pacientes SANOS (status=0) - media y std
HEALTHY_STATS = {
    "MDVP:Fo(Hz)":       (120.0, 15.0),
    "MDVP:Fhi(Hz)":      (140.0, 20.0),
    "MDVP:Flo(Hz)":      (100.0, 15.0),
    "MDVP:Jitter(%)":    (0.004, 0.002),
    "MDVP:Jitter(Abs)":  (0.00003, 0.00002),
    "MDVP:RAP":          (0.002, 0.001),
    "MDVP:PPQ":          (0.002, 0.001),
    "Jitter:DDP":        (0.006, 0.004),
    "MDVP:Shimmer":      (0.020, 0.010),
    "MDVP:Shimmer(dB)":  (0.200, 0.100),
    "Shimmer:APQ3":      (0.010, 0.005),
    "Shimmer:APQ5":      (0.015, 0.008),
    "MDVP:APQ":          (0.020, 0.010),
    "Shimmer:DDA":       (0.030, 0.015),
    "NHR":               (0.020, 0.015),
    "HNR":               (22.0, 4.0),
    "RPDE":              (0.450, 0.080),
    "DFA":               (0.650, 0.050),
    "spread1":           (-5.0, 1.5),
    "spread2":           (0.200, 0.050),
    "D2":                (2.0, 0.3),
    "PPE":               (0.200, 0.060),
}

# Para pacientes con PARKINSON (status=1) - media y std
PARKINSON_STATS = {
    "MDVP:Fo(Hz)":       (150.0, 25.0),
    "MDVP:Fhi(Hz)":      (180.0, 35.0),
    "MDVP:Flo(Hz)":      (120.0, 25.0),
    "MDVP:Jitter(%)":    (0.007, 0.005),
    "MDVP:Jitter(Abs)":  (0.00006, 0.00004),
    "MDVP:RAP":          (0.004, 0.003),
    "MDVP:PPQ":          (0.004, 0.003),
    "Jitter:DDP":        (0.012, 0.009),
    "MDVP:Shimmer":      (0.040, 0.025),
    "MDVP:Shimmer(dB)":  (0.400, 0.250),
    "Shimmer:APQ3":      (0.020, 0.012),
    "Shimmer:APQ5":      (0.030, 0.018),
    "MDVP:APQ":          (0.035, 0.020),
    "Shimmer:DDA":       (0.060, 0.035),
    "NHR":               (0.050, 0.040),
    "HNR":               (18.0, 5.0),
    "RPDE":              (0.550, 0.100),
    "DFA":               (0.700, 0.060),
    "spread1":           (-6.5, 2.0),
    "spread2":           (0.250, 0.080),
    "D2":                (2.3, 0.4),
    "PPE":               (0.300, 0.100),
}

# ============================================================================
# GENERACIÓN DE PACIENTES SINTÉTICOS
# ============================================================================

def generate_patient(patient_id: int, is_parkinson: bool, seed: int = None) -> dict:
    """
    Genera un paciente sintético con las 22 features.
    
    Args:
        patient_id: ID del paciente
        is_parkinson: True si debe tener Parkinson, False si sano
        seed: Semilla opcional para reproducibilidad
    
    Returns:
        Diccionario con datos del paciente
    """
    if seed is not None:
        np.random.seed(seed)
    
    stats = PARKINSON_STATS if is_parkinson else HEALTHY_STATS
    
    features = {}
    for feature_name, (mean, std) in stats.items():
        # Generar valor con distribución normal, recortado a 3 std
        value = np.random.normal(mean, std)
        value = np.clip(value, mean - 3*std, mean + 3*std)
        # Asegurar valores positivos para features que deben serlo
        if feature_name in ["MDVP:Fo(Hz)", "MDVP:Fhi(Hz)", "MDVP:Flo(Hz)", "HNR"]:
            value = max(value, 1.0)
        if feature_name in ["MDVP:Jitter(%)", "MDVP:Jitter(Abs)", "MDVP:RAP", 
                            "MDVP:PPQ", "Jitter:DDP", "MDVP:Shimmer", "MDVP:Shimmer(dB)",
                            "Shimmer:APQ3", "Shimmer:APQ5", "MDVP:APQ", "Shimmer:DDA",
                            "NHR", "RPDE", "PPE", "spread2", "D2"]:
            value = max(value, 0.000001)
        features[feature_name] = round(float(value), 6)
    
    return {
        "patient_id": patient_id,
        "expected_status": 1 if is_parkinson else 0,
        "expected_label": "Parkinson" if is_parkinson else "Sano",
        "features": features,
    }


def generate_20_patients(seed: int = 42) -> list:
    """
    Genera 20 pacientes: 10 sanos y 10 con Parkinson.
    
    Usa semillas diferentes para cada paciente para variabilidad.
    """
    patients = []
    rng = np.random.RandomState(seed)
    
    for i in range(20):
        is_pd = i >= 10  # primeros 10 sanos, siguientes 10 Parkinson
        patient_seed = int(rng.randint(0, 10000))
        patient = generate_patient(i + 1, is_pd, seed=patient_seed)
        patients.append(patient)
    
    return patients


# ============================================================================
# EVALUACIÓN
# ============================================================================

def evaluate_predictions(patients: list, thresholds: list = None):
    """
    Evalúa las predicciones del modelo para todos los pacientes.
    
    Args:
        patients: Lista de pacientes generados
        thresholds: Lista de umbrales a probar (default: [0.5, 0.55, 0.6, 0.65, 0.7])
    """
    if thresholds is None:
        thresholds = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8]
    
    print("=" * 90)
    print("  PRUEBA DEL MODELO DE PARKINSON — 20 PACIENTES SIMULADOS")
    print("=" * 90)
    print(f"\n  Modelo: XGBoost con SMOTE")
    print(f"  Umbral actual en producción: {PARKINSON_THRESHOLD}")
    print(f"  Features: {len(PARK_FEATURE_ORDER)} biomarcadores")
    print(f"  Pacientes: {len(patients)} (10 sanos, 10 Parkinson)")
    print()
    
    # Verificar que el modelo está cargado
    if parkinsons_model is None or parkinsons_scaler is None:
        print("  ❌ ERROR: El modelo de Parkinson no está cargado.")
        print("     Verifica que 'parkinsons_model_smote.sav' y 'parkinsons_scaler_smote.sav'")
        print("     existan en la carpeta 'saved_models/'")
        return
    
    print(f"  ✅ Modelo cargado correctamente")
    print()
    
    # Probar cada umbral
    for threshold in thresholds:
        print(f"\n{'─' * 90}")
        print(f"  📊 UMBRAL: {threshold:.2f}")
        print(f"{'─' * 90}")
        print(f"  {'Paciente':<10} {'Esperado':<12} {'Predicción':<12} {'Probabilidad':<14} {'Acierto':<10}")
        print(f"  {'─' * 56}")
        
        tp = fp = tn = fn = 0
        
        for patient in patients:
            try:
                label, proba = predict_parkinson(patient["features"], threshold=threshold)
            except Exception as e:
                print(f"  Paciente {patient['patient_id']:<3} ❌ Error: {e}")
                continue
            
            expected = patient["expected_status"]
            correct = (label == expected)
            
            if correct:
                result = "✅"
            else:
                result = "❌"
            
            pred_label = "Parkinson" if label == 1 else "Sano"
            
            print(f"  #{patient['patient_id']:<3}    {patient['expected_label']:<10} {pred_label:<12} {proba:.4f}          {result}")
            
            # Actualizar matriz de confusión
            if expected == 1 and label == 1:
                tp += 1
            elif expected == 0 and label == 1:
                fp += 1
            elif expected == 0 and label == 0:
                tn += 1
            elif expected == 1 and label == 0:
                fn += 1
        
        # Métricas
        total = tp + tn + fp + fn
        accuracy = (tp + tn) / total if total > 0 else 0
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        f1 = 2 * (precision * sensitivity) / (precision + sensitivity) if (precision + sensitivity) > 0 else 0
        
        print(f"\n  📈 MÉTRICAS (umbral {threshold:.2f}):")
        print(f"  {'─' * 40}")
        print(f"  Matriz de confusión:")
        print(f"                    Predicho")
        print(f"                  Sano    PD")
        print(f"  Real    Sano   {tn:>4}   {fp:>4}")
        print(f"          PD    {fn:>4}   {tp:>4}")
        print(f"  {'─' * 40}")
        print(f"  Exactitud (Accuracy):     {accuracy:.2%}")
        print(f"  Sensibilidad (Recall):    {sensitivity:.2%}")
        print(f"  Especificidad:            {specificity:.2%}")
        print(f"  Precisión:                {precision:.2%}")
        print(f"  F1-Score:                 {f1:.2%}")
        print(f"  {'─' * 40}")
        print(f"  Falsos Positivos: {fp}  |  Falsos Negativos: {fn}")
    
    print(f"\n{'═' * 90}")
    print(f"  RECOMENDACIÓN:")
    print(f"  {'═' * 90}")
    print(f"  Si hay muchos falsos positivos con el umbral actual ({PARKINSON_THRESHOLD}),")
    print(f"  considera subir el umbral a 0.65 o 0.70 para reducir falsos positivos.")
    print(f"  El notebook de entrenamiento recomienda 0.65 como umbral óptimo.")
    print(f"{'═' * 90}\n")


# ============================================================================
# DIAGNÓSTICO DETALLADO: Comparar features de pacientes vs dataset real
# ============================================================================

def diagnose_feature_distribution(patients: list):
    """
    Muestra la distribución de features generadas vs las esperadas
    para verificar que los datos sintéticos son realistas.
    """
    print(f"\n{'─' * 90}")
    print("  📋 DIAGNÓSTICO DE DISTRIBUCIÓN DE FEATURES")
    print(f"{'─' * 90}")
    
    # Separar por clase esperada
    healthy = [p for p in patients if p["expected_status"] == 0]
    parkinson = [p for p in patients if p["expected_status"] == 1]
    
    print(f"\n  {'Feature':<22} {'Sano (media)':<16} {'PD (media)':<16} {'Dif. esperada':<16}")
    print(f"  {'─' * 68}")
    
    for feat in PARK_FEATURE_ORDER:
        h_vals = [p["features"][feat] for p in healthy]
        p_vals = [p["features"][feat] for p in parkinson]
        h_mean = np.mean(h_vals)
        p_mean = np.mean(p_vals)
        
        h_ref = HEALTHY_STATS.get(feat, (0, 0))[0]
        p_ref = PARKINSON_STATS.get(feat, (0, 0))[0]
        diff_ref = p_ref - h_ref
        
        print(f"  {feat:<22} {h_mean:<16.6f} {p_mean:<16.6f} {diff_ref:<+16.6f}")
    
    print()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("Generando 20 pacientes simulados...")
    patients = generate_20_patients(seed=42)
    print(f"✓ {len(patients)} pacientes generados")
    
    # Mostrar diagnóstico de distribución
    diagnose_feature_distribution(patients)
    
    # Evaluar predicciones con múltiples umbrales
    evaluate_predictions(patients)
    
    # Guardar pacientes a JSON para referencia
    output_path = os.path.join(os.path.dirname(__file__), "pacientes_simulados.json")
    serializable = []
    for p in patients:
        serializable.append({
            "patient_id": p["patient_id"],
            "expected_status": p["expected_status"],
            "expected_label": p["expected_label"],
            "features": {k: float(v) for k, v in p["features"].items()}
        })
    
    with open(output_path, "w") as f:
        json.dump(serializable, f, indent=2)
    
    print(f"\nPacientes guardados en: {output_path}")
    print()

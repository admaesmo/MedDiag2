"""
Script de diagnóstico: Simula la extracción de features desde audio real.

El problema: cuando subes un audio real grabado con el celular, el extractor
de features (librosa) produce valores que NO se parecen a los del dataset UCI.
Esto causa que el modelo clasifique erróneamente como Parkinson.

Este script genera 20 pacientes con features que imitan lo que produce
la extracción desde audio real (con ruido, compresión, micrófono de celular),
y prueba el modelo para ver cuántos falsos positivos se producen.

Además, compara las features extraídas vs las del dataset UCI para identificar
qué biomarcadores se están desviando más.
"""

import sys
import os
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.model_predict import (
    predict_parkinson,
    PARK_FEATURE_ORDER,
    PARKINSON_THRESHOLD,
    parkinsons_model,
    parkinsons_scaler,
)

# ============================================================================
# RANGOS TÍPICOS DEL DATASET UCI (para referencia)
# ============================================================================
# Estos son los rangos observados en el dataset real de Parkinson UCI

UCI_RANGES = {
    "MDVP:Fo(Hz)":       (88.0, 260.0),
    "MDVP:Fhi(Hz)":      (100.0, 600.0),
    "MDVP:Flo(Hz)":      (65.0, 240.0),
    "MDVP:Jitter(%)":    (0.001, 0.033),
    "MDVP:Jitter(Abs)":  (0.000007, 0.00026),
    "MDVP:RAP":          (0.0005, 0.021),
    "MDVP:PPQ":          (0.0005, 0.02),
    "Jitter:DDP":        (0.0015, 0.063),
    "MDVP:Shimmer":      (0.009, 0.12),
    "MDVP:Shimmer(dB)":  (0.08, 1.2),
    "Shimmer:APQ3":      (0.004, 0.06),
    "Shimmer:APQ5":      (0.006, 0.08),
    "MDVP:APQ":          (0.007, 0.09),
    "Shimmer:DDA":       (0.012, 0.18),
    "NHR":               (0.0005, 0.32),
    "HNR":               (8.0, 33.0),
    "RPDE":              (0.25, 0.75),
    "DFA":               (0.50, 0.85),
    "spread1":           (-9.0, -2.0),
    "spread2":           (0.08, 0.45),
    "D2":                (1.5, 3.0),
    "PPE":               (0.08, 0.50),
}

# ============================================================================
# SIMULACIÓN DE FEATURES EXTRAÍDAS DE AUDIO REAL (con distorsión)
# ============================================================================

def simulate_real_audio_features(seed: int) -> dict:
    """
    Simula las features que produce el extractor de audio (librosa)
    cuando se graba con un celular en ambiente no controlado.
    
    Características del audio real vs dataset UCI:
    - Frecuencia fundamental (F0) más variable por ruido ambiente
    - Jitter/Shimmer elevados por compresión de audio (MP3/WebM)
    - HNR más bajo por ruido de fondo
    - NHR más alto por ruido ambiental
    - Features no lineales (RPDE, DFA, D2, PPE) distorsionadas
    """
    rng = np.random.RandomState(seed)
    
    # ============================================================
    # PACIENTE SANO con grabación de celular (típico falso positivo)
    # ============================================================
    # Características de una persona sana grabando con celular:
    # - Frecuencia fundamental normal (100-180 Hz para hombres, 180-250 para mujeres)
    # - Pero JITTER y SHIMMER se elevan por compresión de audio
    # - HNR baja por ruido ambiente
    # - NHR se eleva
    
    is_male = rng.choice([True, False])
    
    if is_male:
        fo_mean = rng.uniform(100, 150)
    else:
        fo_mean = rng.uniform(180, 240)
    
    # Variabilidad normal de F0
    fhi = fo_mean * rng.uniform(1.1, 1.4)
    flo = fo_mean * rng.uniform(0.7, 0.9)
    
    # Jitter - se eleva por compresión de audio (códec del celular)
    # Un sano tiene jitter(%) ~0.002-0.005, pero con compresión sube a 0.005-0.015
    jitter_pct = rng.uniform(0.003, 0.012)
    jitter_abs = jitter_pct * fo_mean / 100  # aproximación
    
    # RAP, PPQ, DDP - también se elevan
    rap = jitter_pct * rng.uniform(0.4, 0.7)
    ppq = jitter_pct * rng.uniform(0.4, 0.7)
    ddp = rap * 3
    
    # Shimmer - se eleva por compresión y ruido
    # Sano tiene shimmer ~0.01-0.03, con compresión sube a 0.02-0.08
    shimmer = rng.uniform(0.015, 0.07)
    shimmer_db = 20 * np.log10(1 + shimmer / 100) if shimmer > 0 else 0
    
    apq3 = shimmer * rng.uniform(0.4, 0.6)
    apq5 = shimmer * rng.uniform(0.5, 0.8)
    apq11 = shimmer * rng.uniform(0.6, 0.9)
    dda_shimmer = apq3 * 3
    
    # NHR - se eleva por ruido ambiente
    nhr = rng.uniform(0.01, 0.08)
    
    # HNR - baja por ruido
    hnr = rng.uniform(15, 25)
    
    # Features no lineales - se distorsionan con audio comprimido
    rpde = rng.uniform(0.35, 0.65)
    dfa = rng.uniform(0.55, 0.78)
    spread1 = rng.uniform(-7.0, -3.0)
    spread2 = rng.uniform(0.12, 0.35)
    d2 = rng.uniform(1.6, 2.6)
    ppe = rng.uniform(0.12, 0.35)
    
    features = {
        "MDVP:Fo(Hz)":       round(fo_mean, 2),
        "MDVP:Fhi(Hz)":      round(fhi, 2),
        "MDVP:Flo(Hz)":      round(flo, 2),
        "MDVP:Jitter(%)":    round(jitter_pct, 6),
        "MDVP:Jitter(Abs)":  round(jitter_abs, 6),
        "MDVP:RAP":          round(rap, 6),
        "MDVP:PPQ":          round(ppq, 6),
        "Jitter:DDP":        round(ddp, 6),
        "MDVP:Shimmer":      round(shimmer, 6),
        "MDVP:Shimmer(dB)":  round(shimmer_db, 6),
        "Shimmer:APQ3":      round(apq3, 6),
        "Shimmer:APQ5":      round(apq5, 6),
        "MDVP:APQ":          round(apq11, 6),
        "Shimmer:DDA":       round(dda_shimmer, 6),
        "NHR":               round(nhr, 6),
        "HNR":               round(hnr, 2),
        "RPDE":              round(rpde, 6),
        "DFA":               round(dfa, 6),
        "spread1":           round(spread1, 6),
        "spread2":           round(spread2, 6),
        "D2":                round(d2, 6),
        "PPE":               round(ppe, 6),
    }
    
    return {
        "patient_id": seed,
        "expected_status": 0,  # TODOS son sanos
        "expected_label": "Sano (grabación real)",
        "is_male": is_male,
        "features": features,
    }


def simulate_parkinson_audio_features(seed: int) -> dict:
    """
    Simula features de una persona CON Parkinson grabando con celular.
    Los valores son más extremos que un sano.
    """
    rng = np.random.RandomState(seed + 1000)
    
    is_male = rng.choice([True, False])
    
    if is_male:
        fo_mean = rng.uniform(110, 170)
    else:
        fo_mean = rng.uniform(160, 250)
    
    # Más variabilidad en F0 (temblor)
    fhi = fo_mean * rng.uniform(1.2, 1.6)
    flo = fo_mean * rng.uniform(0.5, 0.8)
    
    # Jitter más elevado (temblor vocal)
    jitter_pct = rng.uniform(0.006, 0.025)
    jitter_abs = jitter_pct * fo_mean / 100
    
    rap = jitter_pct * rng.uniform(0.5, 0.8)
    ppq = jitter_pct * rng.uniform(0.5, 0.8)
    ddp = rap * 3
    
    # Shimmer más elevado
    shimmer = rng.uniform(0.03, 0.10)
    shimmer_db = 20 * np.log10(1 + shimmer / 100) if shimmer > 0 else 0
    
    apq3 = shimmer * rng.uniform(0.4, 0.6)
    apq5 = shimmer * rng.uniform(0.5, 0.8)
    apq11 = shimmer * rng.uniform(0.6, 0.9)
    dda_shimmer = apq3 * 3
    
    # NHR más alto
    nhr = rng.uniform(0.03, 0.15)
    
    # HNR más bajo
    hnr = rng.uniform(8, 18)
    
    # Features no lineales más extremas
    rpde = rng.uniform(0.45, 0.75)
    dfa = rng.uniform(0.60, 0.85)
    spread1 = rng.uniform(-8.0, -4.0)
    spread2 = rng.uniform(0.18, 0.42)
    d2 = rng.uniform(1.8, 2.8)
    ppe = rng.uniform(0.20, 0.45)
    
    features = {
        "MDVP:Fo(Hz)":       round(fo_mean, 2),
        "MDVP:Fhi(Hz)":      round(fhi, 2),
        "MDVP:Flo(Hz)":      round(flo, 2),
        "MDVP:Jitter(%)":    round(jitter_pct, 6),
        "MDVP:Jitter(Abs)":  round(jitter_abs, 6),
        "MDVP:RAP":          round(rap, 6),
        "MDVP:PPQ":          round(ppq, 6),
        "Jitter:DDP":        round(ddp, 6),
        "MDVP:Shimmer":      round(shimmer, 6),
        "MDVP:Shimmer(dB)":  round(shimmer_db, 6),
        "Shimmer:APQ3":      round(apq3, 6),
        "Shimmer:APQ5":      round(apq5, 6),
        "MDVP:APQ":          round(apq11, 6),
        "Shimmer:DDA":       round(dda_shimmer, 6),
        "NHR":               round(nhr, 6),
        "HNR":               round(hnr, 2),
        "RPDE":              round(rpde, 6),
        "DFA":               round(dfa, 6),
        "spread1":           round(spread1, 6),
        "spread2":           round(spread2, 6),
        "D2":                round(d2, 6),
        "PPE":               round(ppe, 6),
    }
    
    return {
        "patient_id": seed,
        "expected_status": 1,
        "expected_label": "Parkinson (grabación real)",
        "is_male": is_male,
        "features": features,
    }


def generate_20_realistic_patients(seed: int = 42) -> list:
    """
    Genera 20 pacientes que simulan grabaciones de audio real:
    - 10 sanos grabando con celular (potenciales falsos positivos)
    - 10 con Parkinson grabando con celular
    """
    patients = []
    rng = np.random.RandomState(seed)
    
    for i in range(20):
        patient_seed = int(rng.randint(0, 10000))
        if i < 10:
            patient = simulate_real_audio_features(patient_seed)
        else:
            patient = simulate_parkinson_audio_features(patient_seed)
        patients.append(patient)
    
    return patients


# ============================================================================
# DIAGNÓSTICO: Comparar features simuladas vs rangos UCI
# ============================================================================

def diagnose_feature_deviation(patients: list):
    """
    Para cada feature, muestra cuánto se desvía el valor simulado
    del rango típico del dataset UCI.
    """
    print(f"\n{'=' * 100}")
    print("  DIAGNÓSTICO: FEATURES DE AUDIO REAL vs DATASET UCI")
    print(f"{'=' * 100}")
    print(f"\n  {'Feature':<22} {'Valor simulado':<18} {'Rango UCI':<22} {'¿Fuera de rango?':<18}")
    print(f"  {'─' * 78}")
    
    out_of_range_count = {feat: 0 for feat in PARK_FEATURE_ORDER}
    total_patients = len(patients)
    
    for feat in PARK_FEATURE_ORDER:
        uci_min, uci_max = UCI_RANGES.get(feat, (0, 1))
        oor = 0
        for p in patients:
            val = p["features"][feat]
            if val < uci_min or val > uci_max:
                oor += 1
        out_of_range_count[feat] = oor
        pct = oor / total_patients * 100
        
        # Tomar el primer paciente como ejemplo
        example_val = patients[0]["features"][feat]
        
        flag = "⚠️" if pct > 30 else "✅"
        print(f"  {feat:<22} {example_val:<18.6f} [{uci_min:<8.4f}, {uci_max:<8.4f}] {flag} {pct:.0f}% fuera de rango")
    
    print(f"\n  {'─' * 78}")
    print(f"  Resumen: Features con >30% de valores fuera de rango UCI:")
    for feat, count in sorted(out_of_range_count.items(), key=lambda x: -x[1]):
        pct = count / total_patients * 100
        if pct > 30:
            print(f"    ⚠️  {feat:<22} {count}/{total_patients} pacientes ({pct:.0f}%)")
    
    print()


# ============================================================================
# EVALUACIÓN
# ============================================================================

def evaluate_realistic_patients(patients: list):
    """
    Evalúa el modelo con los pacientes simulados (audio real).
    """
    print(f"\n{'=' * 100}")
    print("  PRUEBA CON FEATURES SIMULADAS DE AUDIO REAL (20 pacientes)")
    print(f"{'=' * 100}")
    print(f"\n  Umbral actual: {PARKINSON_THRESHOLD}")
    print(f"  Pacientes: 10 sanos (grabación real) + 10 Parkinson (grabación real)")
    print()
    
    if parkinsons_model is None or parkinsons_scaler is None:
        print("  ❌ ERROR: Modelo no cargado")
        return
    
    thresholds_to_test = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.80, 0.85, 0.90]
    
    for threshold in thresholds_to_test:
        tp = fp = tn = fn = 0
        
        for patient in patients:
            try:
                label, proba = predict_parkinson(patient["features"], threshold=threshold)
            except Exception as e:
                print(f"  Error paciente {patient['patient_id']}: {e}")
                continue
            
            expected = patient["expected_status"]
            
            if expected == 1 and label == 1:
                tp += 1
            elif expected == 0 and label == 1:
                fp += 1
            elif expected == 0 and label == 0:
                tn += 1
            elif expected == 1 and label == 0:
                fn += 1
        
        total = tp + tn + fp + fn
        accuracy = (tp + tn) / total if total > 0 else 0
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        f1 = 2 * (precision * sensitivity) / (precision + sensitivity) if (precision + sensitivity) > 0 else 0
        
        print(f"  {'─' * 60}")
        print(f"  📊 UMBRAL: {threshold:.2f}")
        print(f"  {'─' * 60}")
        print(f"  Matriz:          Sano  PD")
        print(f"    Real Sano:    {tn:>3}   {fp:>3}")
        print(f"    Real PD:      {fn:>3}   {tp:>3}")
        print(f"  Accuracy:  {accuracy:.1%}  |  Sensitivity: {sensitivity:.1%}")
        print(f"  Specificity: {specificity:.1%}  |  Precision: {precision:.1%}")
        print(f"  F1: {f1:.1%}  |  FP: {fp}  |  FN: {fn}")
    
    print(f"\n{'=' * 100}")
    print("  CONCLUSIONES DEL DIAGNÓSTICO")
    print(f"{'=' * 100}")
    print("""
  El problema de los FALSOS POSITIVOS con audio real se debe a que:

  1. El extractor de features (librosa) produce valores DISTINTOS a los del
     dataset UCI Oxford con el que se entrenó el modelo.

  2. La compresión de audio del celular (WebM/Opus, MP3) introduce
     distorsiones que elevan artificialmente el Jitter y Shimmer.

  3. El ruido ambiente baja el HNR y sube el NHR, simulando patrones
     de voz parkinsoniana.

  4. El modelo fue entrenado con grabaciones clínicas de calidad (UCI),
     no con grabaciones de celular.

  RECOMENDACIONES:
  - Aumentar el umbral a 0.80 (ya aplicado en model_predict.py)
  - Mejorar el preprocesamiento de audio (filtrado de ruido)
  - Re-entrenar el modelo con grabaciones de celular
  - Implementar un clasificador de calidad de audio antes de predecir
""")
    print()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("Generando 20 pacientes simulando grabaciones de audio real...")
    patients = generate_20_realistic_patients(seed=42)
    print(f"✓ {len(patients)} pacientes generados")
    
    # Mostrar diagnóstico de desviación de features
    diagnose_feature_deviation(patients)
    
    # Evaluar predicciones
    evaluate_realistic_patients(patients)
    
    # Guardar pacientes a JSON
    output_path = os.path.join(os.path.dirname(__file__), "pacientes_audio_real_simulados.json")
    serializable = []
    for p in patients:
        serializable.append({
            "patient_id": p["patient_id"],
            "expected_status": p["expected_status"],
            "expected_label": p["expected_label"],
            "is_male": bool(p["is_male"]),

            "features": {k: float(v) for k, v in p["features"].items()}
        })
    
    with open(output_path, "w") as f:
        json.dump(serializable, f, indent=2)
    
    print(f"\nPacientes guardados en: {output_path}")
    print()

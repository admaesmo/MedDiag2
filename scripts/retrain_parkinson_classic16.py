#!/usr/bin/env python3
"""
Reentrena el modelo de Parkinson usando solo las 16 features clásicas
(jitter, shimmer, HNR, F0), excluyendo las 6 no lineales (RPDE, DFA,
spread1, spread2, D2, PPE) cuya extracción está rota en producción:
quedan clampeadas al límite del rango UCI en 74-100% de los audios
reales procesados por el pipeline (ver memoria de diagnóstico
2026-06-16 / Documentacion del proyecto).

IMPORTANTE — por qué se entrena con figshare y no con Oxford:
Se intentó primero entrenar con el dataset Oxford (laboratorio, mic de
cabeza, 44.1kHz) y validar contra audio real (figshare, grabado por
teléfono, 8kHz). Resultado: el modelo entrenado en Oxford NO transfiere
a audio real (AUC externo 0.41-0.51, peor que azar) — hay un domain
mismatch demasiado grande entre datos de laboratorio y grabación real,
incluso usando solo las 16 features "buenas". Por eso este script
entrena directamente con el dataset figshare (CC BY 4.0, 81 sujetos
reales: 40 PD + 41 HC, procesados con el pipeline real de la app), que
es la única fuente de datos que comparte la distribución de despliegue.

LIMITACIÓN CONOCIDA Y ACEPTADA (decisión explícita para la muestra de
mañana, no apta para uso clínico sin resolver esto): en figshare, el
grupo PD tiene edad media ~67 años y el grupo HC ~48 años (19 años de
brecha). Jitter/shimmer/HNR cambian con la edad independientemente de
Parkinson, así que parte del poder discriminativo medido aquí puede ser
"detecta vejez" en vez de "detecta Parkinson". No se corrige por edad
en este script a petición explícita (ver memoria de decisión).

Uso:
    python scripts/retrain_parkinson_classic16.py
"""
from __future__ import annotations

import io
import sys
import warnings
import zipfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import requests
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.services.audio_processing import extract_features_from_audio, AudioProcessingError  # noqa: E402

UCI_URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/parkinsons/parkinsons.data"
FIGSHARE_ARTICLE_API = "https://api.figshare.com/v2/articles/23849127"

CLASSIC16_FEATURE_ORDER = [
    "MDVP:Fo(Hz)", "MDVP:Fhi(Hz)", "MDVP:Flo(Hz)",
    "MDVP:Jitter(%)", "MDVP:Jitter(Abs)", "MDVP:RAP", "MDVP:PPQ", "Jitter:DDP",
    "MDVP:Shimmer", "MDVP:Shimmer(dB)", "Shimmer:APQ3", "Shimmer:APQ5", "MDVP:APQ", "Shimmer:DDA",
    "NHR", "HNR",
]

MODEL_DIR = REPO_ROOT / "saved_models"
TMP_DIR = Path("/tmp/figshare_pd_retrain")


# ---------------------------------------------------------------------------
# 0. Oxford — solo como contexto narrativo (NO se usa para el modelo final)
# ---------------------------------------------------------------------------

def report_oxford_does_not_transfer() -> None:
    print("=== Contexto: por qué no se entrena con Oxford ===")
    df = pd.read_csv(UCI_URL)
    X = df[CLASSIC16_FEATURE_ORDER].astype(float)
    y = df["status"].astype(int)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    pipe = Pipeline([("scaler", StandardScaler()), ("model", LogisticRegression(class_weight="balanced", max_iter=2000))])
    proba = cross_val_predict(pipe, X, y, cv=cv, method="predict_proba")[:, 1]
    print(f"  CV en Oxford (mismo dominio): AUC={roc_auc_score(y, proba):.3f}  (ya sabíamos: no transfiere a audio real)")


# ---------------------------------------------------------------------------
# 1. Dataset figshare — fuente de entrenamiento real (única en el dominio de despliegue)
# ---------------------------------------------------------------------------

def download_figshare_dataset() -> None:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    meta = requests.get(FIGSHARE_ARTICLE_API, timeout=30).json()
    files = {f["name"]: f["download_url"] for f in meta["files"]}

    pd_dir = TMP_DIR / "PD_AH"
    hc_dir = TMP_DIR / "HC_AH"
    for zip_name, out_dir in [("PD_AH.zip", pd_dir), ("HC_AH.zip", hc_dir)]:
        if out_dir.exists():
            continue
        print(f"Descargando {zip_name}...")
        content = requests.get(files[zip_name], timeout=30).content
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            zf.extractall(out_dir)


def extract_figshare_features() -> pd.DataFrame:
    rows = []
    for label, subdir in [("PwPD", "PD_AH"), ("HC", "HC_AH")]:
        wav_files = list((TMP_DIR / subdir).rglob("*.wav"))
        for wav_path in wav_files:
            audio_bytes = wav_path.read_bytes()
            try:
                feats, missing = extract_features_from_audio(audio_bytes, source_name=wav_path.name)
            except AudioProcessingError as exc:
                print(f"  [WARN] extracción fallida en {wav_path.name}: {exc}")
                continue
            row = {f: feats.get(f) for f in CLASSIC16_FEATURE_ORDER}
            row["label"] = 1 if label == "PwPD" else 0
            row["file"] = wav_path.name
            rows.append(row)
    df = pd.DataFrame(rows)
    print(f"  Audios extraídos vía pipeline real: {len(df)} ({df['label'].sum()} PD / {(df['label'] == 0).sum()} HC)")
    return df


# ---------------------------------------------------------------------------
# 2. Candidatos de modelo (clases ya balanceadas 40/41 -> sin SMOTE)
# ---------------------------------------------------------------------------

def build_candidates() -> dict[str, Pipeline]:
    return {
        "LogisticRegression": Pipeline([
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(class_weight="balanced", max_iter=2000, random_state=42)),
        ]),
        "RandomForest": Pipeline([
            ("scaler", StandardScaler()),
            ("model", RandomForestClassifier(n_estimators=200, max_depth=4, class_weight="balanced", random_state=42)),
        ]),
        "XGBoost": Pipeline([
            ("scaler", StandardScaler()),
            ("model", XGBClassifier(
                n_estimators=100, max_depth=3, learning_rate=0.1,
                subsample=0.8, colsample_bytree=0.8,
                random_state=42, eval_metric="logloss",
            )),
        ]),
    }


# ---------------------------------------------------------------------------
# 3. Evaluación y selección de umbral
# ---------------------------------------------------------------------------

def threshold_sweep(y_true: np.ndarray, proba: np.ndarray) -> tuple[float, float, float]:
    """Recorre umbrales y devuelve (umbral, sensibilidad, especificidad).

    Prioriza sensibilidad >= 0.80 (herramienta de tamizaje: preferible no
    perder positivos) y dentro de eso maximiza especificidad. Si ningún
    umbral logra sensibilidad >= 0.80, maximiza sensibilidad+especificidad.
    """
    candidates = []
    for t in np.arange(0.30, 0.81, 0.05):
        pred = (proba >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
        sens = tp / (tp + fn) if (tp + fn) else 0.0
        spec = tn / (tn + fp) if (tn + fp) else 0.0
        candidates.append((t, sens, spec))

    good = [c for c in candidates if c[1] >= 0.80]
    if good:
        return max(good, key=lambda c: c[2])
    return max(candidates, key=lambda c: c[1] + c[2])


def main() -> None:
    report_oxford_does_not_transfer()

    print("\n=== Descargando y extrayendo dataset de entrenamiento real (figshare) ===")
    download_figshare_dataset()
    train_df = extract_figshare_features()
    X = train_df[CLASSIC16_FEATURE_ORDER].astype(float)
    y = train_df["label"].to_numpy()

    print("\n=== Validación cruzada por sujeto (5-fold, N=81) ===")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_results = {}
    for name, pipeline in build_candidates().items():
        proba_oof = cross_val_predict(pipeline, X, y, cv=cv, method="predict_proba")[:, 1]
        auc = roc_auc_score(y, proba_oof)
        cv_results[name] = (auc, proba_oof)
        print(f"  [{name}] AUC (out-of-fold)={auc:.3f}")

    winner_name = max(cv_results, key=lambda n: cv_results[n][0])
    winner_auc, winner_proba_oof = cv_results[winner_name]
    print(f"\n>>> Modelo ganador: {winner_name} (AUC out-of-fold={winner_auc:.3f})")

    threshold, sens, spec = threshold_sweep(y, winner_proba_oof)
    pred_oof = (winner_proba_oof >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred_oof, labels=[0, 1]).ravel()
    acc = (tp + tn) / len(y)

    print(f"\n=== Umbral elegido: {threshold:.2f} (medido out-of-fold, sin fuga) ===")
    print(f"  Sensibilidad={sens:.3f}  Especificidad={spec:.3f}  Accuracy={acc:.3f}")
    print(f"  Matriz de confusión (out-of-fold): TN={tn} FP={fp} FN={fn} TP={tp}")
    print("\n  RECORDATORIO: confound de edad no corregido (PD~67a vs HC~48a). "
          "Reportar como hallazgo preliminar, N=81, no validado clínicamente.")

    print(f"\n=== Entrenando modelo final ({winner_name}) sobre los 81 sujetos ===")
    winner_pipeline = build_candidates()[winner_name]
    winner_pipeline.fit(X, y)

    scaler_final = winner_pipeline.named_steps["scaler"]
    model_final = winner_pipeline.named_steps["model"]

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model_final, MODEL_DIR / "parkinsons_model_classic16.sav")
    joblib.dump(scaler_final, MODEL_DIR / "parkinsons_scaler_classic16.sav")

    print(f"\nGuardado: {MODEL_DIR / 'parkinsons_model_classic16.sav'}")
    print(f"Guardado: {MODEL_DIR / 'parkinsons_scaler_classic16.sav'}")
    print(f"\nActualizar en app/model_predict.py: PARKINSON_CONFIDENCE_THRESHOLD = {threshold:.2f}")


if __name__ == "__main__":
    main()

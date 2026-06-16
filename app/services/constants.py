"""Constantes compartidas del pipeline de biomarcadores de voz."""

# Orden canónico de las 22 características del dataset Oxford Parkinson's Disease Detection.
# Fuente única de verdad: todo módulo que necesite este orden debe importar desde aquí.
PARKINSON_FEATURE_ORDER = [
    "MDVP:Fo(Hz)", "MDVP:Fhi(Hz)", "MDVP:Flo(Hz)",
    "MDVP:Jitter(%)", "MDVP:Jitter(Abs)", "MDVP:RAP", "MDVP:PPQ", "Jitter:DDP",
    "MDVP:Shimmer", "MDVP:Shimmer(dB)", "Shimmer:APQ3", "Shimmer:APQ5", "MDVP:APQ", "Shimmer:DDA",
    "NHR", "HNR",
    "RPDE", "DFA", "spread1", "spread2", "D2", "PPE",
]

# Subconjunto de 16 features clásicas usado por el modelo de inferencia.
# Las 6 no lineales (RPDE, DFA, spread1, spread2, D2, PPE) se siguen
# calculando y persistiendo (ver PARKINSON_FEATURE_ORDER) pero se excluyen
# del modelo: su extracción queda clampeada al límite del rango UCI en
# 74-100% de los audios reales procesados por el pipeline, lo que hacía
# que el modelo predijera positivo casi siempre (ver diagnóstico 2026-06-16
# en la memoria del proyecto).
PARKINSON_MODEL_FEATURE_ORDER = [
    "MDVP:Fo(Hz)", "MDVP:Fhi(Hz)", "MDVP:Flo(Hz)",
    "MDVP:Jitter(%)", "MDVP:Jitter(Abs)", "MDVP:RAP", "MDVP:PPQ", "Jitter:DDP",
    "MDVP:Shimmer", "MDVP:Shimmer(dB)", "Shimmer:APQ3", "Shimmer:APQ5", "MDVP:APQ", "Shimmer:DDA",
    "NHR", "HNR",
]

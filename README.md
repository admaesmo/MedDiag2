# MedDiag2 — Tamizaje experimental de Parkinson mediante análisis de voz

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-13+-black?logo=nextdotjs&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Descripción General

**MedDiag2** es una plataforma web de **tamizaje experimental** de la enfermedad de Parkinson mediante análisis de voz. El sistema permite a los usuarios grabar múltiples tomas de voz sostenida, extraer automáticamente **22 biomarcadores acústicos** (F0, jitter, shimmer, HNR, NHR, y parámetros no lineales como DFA, D2, RPDE, PPE), agregarlos por mediana entre tomas, y obtener una **predicción preliminar basada en machine learning**.

El proyecto integra:
- **Frontend** en Next.js con interfaz de flujo multi-toma para Parkinson, historial y visualización de resultados.
- **Backend** en FastAPI con pipeline completo de procesamiento de señales.
- **Pipeline de audio** con extracción de biomarcadores, control de calidad y trazabilidad mediante Feature Store versionado.
- **Modelos ML** serializados para inferencia (Parkinson con modelo "classic16", y compatibilidad histórica con diabetes y enfermedad cardiovascular).

> 📚 **Proyecto integrador** — Facultad de Ingeniería, Departamento de Ingeniería de Sistemas, Universidad de Antioquia. Medellín, Colombia.

> ⚠️ **Importante:** MedDiag2 es una **herramienta académica experimental de apoyo**, no un sistema de diagnóstico clínico. No reemplaza la evaluación de un profesional de la salud.

---

## Tabla de Contenidos

- [Estado del Proyecto](#estado-del-proyecto)
- [Objetivos](#objetivos)
- [Arquitectura](#arquitectura)
- [Pipeline de Análisis de Voz](#pipeline-de-análisis-de-voz)
- [Biomarcadores Extraídos](#biomarcadores-extraídos)
- [Modelos ML](#modelos-ml)
- [Archivos de Entrenamiento (Vigentes vs Deprecados)](#archivos-de-entrenamiento-vigentes-vs-deprecados)
- [Tecnologías](#tecnologías)
- [Instalación y Ejecución](#instalación-y-ejecución)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Documentación](#documentación)
- [Limitaciones](#limitaciones)
- [Trabajo Futuro](#trabajo-futuro)
- [Licencia](#licencia)

---

## Estado del Proyecto

| Componente | Estado | Detalle |
|-----------|--------|---------|
| Pipeline de audio | ✅ Funcional | Carga, decodificación, extracción de 22 biomarcadores |
| Biomarcadores no lineales | ✅ Implementados | DFA (vectorizado), D2, PPE, RPDE, spread1, spread2 — extraídos y persistidos, **excluidos del modelo** |
| Feature Store | ✅ Implementado | Versionado con `extractor_version` y `feature_schema_version` |
| Inferencia | ✅ Funcional | Predicción con modelo "classic16" (16 features clásicas, umbral 0.40) |
| Control de calidad de audio | ✅ Implementado | Servicio `quality_control.py` activo; RPDE/DFA removidos de features críticas |
| Preprocesamiento DSP | ✅ Implementado | Cascada HP 70 Hz → LP 5 kHz → VAD trim → normalización RMS adaptativa |
| Análisis de múltiples tomas | ✅ Implementado | Flujo obligatorio de 2-5 tomas con agregación por mediana y `session_confidence` |
| Frontend Parkinson | ✅ Funcional | Simplificado a flujo multi-toma exclusivo; autenticación y historial |
| Parselmouth como extractor base | ✅ Implementado | Endpoint `/audio/biomarkers/extract` con Parselmouth |
| Validación clínica | ❌ Pendiente | Sin evaluación con pacientes reales; N=81, confound de edad no corregido |

---

## Objetivos

### General
Desarrollar y documentar un prototipo web de tamizaje experimental de Parkinson basado en análisis de voz, capaz de extraer biomarcadores acústicos desde grabaciones de usuario y utilizarlos como entrada para un modelo de machine learning.

### Específicos
1. Integrar un flujo de carga, almacenamiento y procesamiento de audios dentro de una arquitectura web.
2. Generar un vector de 22 características acústicas compatible con el esquema clásico del dataset de Parkinson.
3. Implementar aproximaciones determinísticas para biomarcadores no lineales.
4. Persistir los biomarcadores extraídos con versionado del extractor y del esquema de características.
5. Generar una predicción preliminar de Parkinson a partir del vector de biomarcadores.
6. Identificar y documentar limitaciones técnicas, metodológicas y clínicas.

---

## Arquitectura

```
┌──────────────┐     ┌─────────────────────────────┐     ┌──────────────┐
│  Frontend    │────▶│     Backend FastAPI          │────▶│  Modelos ML  │
│  (Next.js)   │     │  ┌─────────────────────────┐│     │  (.sav)      │
│              │     │  │  Pipeline de Audio       ││     └──────────────┘
│  Grabación   │     │  │  ┌─────────────────┐    ││     ┌──────────────┐
│  / Carga     │     │  │  │ Decodificación  │    ││     │  Base de     │
│  Historial   │     │  │  ├─────────────────┤    ││     │  Datos       │
│  Resultados  │     │  │  │ Extracción de   │    ││     │  (SQLite/    │
└──────────────┘     │  │  │ Biomarcadores   │    ││     │  PostgreSQL) │
                     │  │  ├─────────────────┤    ││     └──────────────┘
                     │  │  │ Feature Store   │    ││
                     │  │  ├─────────────────┤    ││
                     │  │  │ Inferencia      │    ││
                     │  │  └─────────────────┘    ││
                     │  └─────────────────────────┘│
                     └─────────────────────────────┘
```

### Frontend
- **Next.js 13+** con App Router y TypeScript
- Autenticación local o mediante Supabase
- Componentes atómicos (Atomic Design): atoms, molecules, organisms, templates
- Grabación de audio en el navegador y conversión a WAV
- Internacionalización (i18n): español, inglés, portugués (Brasil)
- Rutas protegidas: dashboard, historial, análisis de Parkinson, configuración

### Backend
- **FastAPI** con endpoints REST documentados (Swagger en `/docs`)
- Pipeline de audio en múltiples capas
- Persistencia con SQLAlchemy + Alembic para migraciones
- Almacenamiento de audio configurable (local, cloud)
- Feature Store versionado para trazabilidad de biomarcadores

---

## Pipeline de Análisis de Voz

```
Audio del usuario
      │
      ▼
┌──────────────────┐
│  Validación       │  Tipo MIME, tamaño, duración mínima (0.5s)
└──────────────────┘
      │
      ▼
┌──────────────────┐
│  Control de       │  Calidad sobre señal cruda: duración, SNR,
│  Calidad (QA/QC)  │  clipping, silencio  (quality_control.py)
└──────────────────┘
      │
      ▼
┌──────────────────┐
│  Decodificación   │  Librosa (principal) → Pydub (fallback)
│                   │  Mono, 22 kHz
└──────────────────┘
      │
      ▼
┌──────────────────────────────────┐
│  Preprocesamiento DSP             │  audio_filters.py
│  HP 70 Hz → LP 5 kHz → VAD trim  │  Butterworth ord. 4, sosfiltfilt
│  → Normalización RMS adaptativa   │  (fase cero, sin clipping)
└──────────────────────────────────┘
      │
      ▼
┌──────────────────┐
│  Extracción F0    │  pYIN → Parselmouth → Autocorrelación
└──────────────────┘
      │
      ▼
┌────────────────────────┐
│  Extracción de         │  Jitter, shimmer, HNR, NHR
│  biomarcadores         │  DFA, D2, RPDE, PPE, spread1, spread2
└────────────────────────┘
      │
      ▼
┌──────────────────┐     ┌─────────────────────────────────┐
│  Feature Store    │     │  Sesión multi-toma (opcional)   │
│  (toma única)     │     │  Mediana de N tomas + CV inter- │
└──────────────────┘     │  toma → session_confidence      │
      │                  └─────────────────────────────────┘
      └──────────┬────────────────────┘
                 ▼
┌──────────────────┐
│  Inferencia       │  StandardScaler → XGBClassifier
│                   │  predicción + probabilidad
└──────────────────┘
      │
      ▼
┌──────────────────┐
│  Visualización    │  Resultados en frontend
└──────────────────┘
```

---

## Biomarcadores Extraídos

El sistema extrae **22 variables** que componen el vector clásico del dataset de Parkinson:

| Categoría | Variables |
|-----------|-----------|
| **Frecuencia** | MDVP:Fo(Hz), MDVP:Fhi(Hz), MDVP:Flo(Hz) |
| **Jitter** | MDVP:Jitter(%), MDVP:Jitter(Abs), MDVP:RAP, MDVP:PPQ, Jitter:DDP |
| **Shimmer** | MDVP:Shimmer, MDVP:Shimmer(dB), Shimmer:APQ3, Shimmer:APQ5, MDVP:APQ, Shimmer:DDA |
| **Ruido** | NHR, HNR |
| **No lineales** | RPDE, DFA, spread1, spread2, D2, PPE |

La extracción usa una estrategia híbrida:
- **Librosa** para carga, preprocesamiento y pitch (ruta principal)
- **Parselmouth/Praat** como alternativa para F0
- **Implementaciones determinísticas propias** para biomarcadores no lineales
- **Aproximación cepstral** para NHR/HNR

> **Nota sobre biomarcadores no lineales:** Las 6 features no lineales (RPDE, DFA, spread1, spread2, D2, PPE) se extraen y persisten en el Feature Store, pero **no alimentan al modelo de inferencia actual**. En audios reales (grabación de celular/web), estas features quedan clampeadas al límite del rango UCI en un 74-100% de los casos, lo que provocaba falsos positivos casi sistemáticos con el modelo anterior. El modelo activo ("classic16") usa solo las 16 features clásicas (F0, jitter, shimmer, HNR/NHR). Ver sección [Modelos ML](#modelos-ml).

---

## Modelos ML

### Modelo principal: Parkinson "classic16"

El modelo activo de Parkinson es **"classic16"**, reentrenado en junio 2026 para corregir el problema de falsos positivos sistemáticos del modelo anterior (ver historial de cambios más abajo).

**Problema diagnosticado con el modelo anterior (SMOTE):**  
El modelo `parkinsons_model_smote.sav` usaba las 22 features del dataset Oxford, incluyendo las 6 no lineales (RPDE, DFA, spread1, spread2, D2, PPE). En audio real (grabación desde celular o web), estas features quedan clampeadas al límite del rango UCI en el **74-100% de los registros**, haciendo que el modelo predijera positivo casi siempre (accuracy ~42% en dataset externo). Ver [`app/services/constants.py`](./app/services/constants.py) y [`app/services/feature_validator.py`](./app/services/feature_validator.py).

**Solución — modelo "classic16":**
1. **Subconjunto de features** — El modelo usa solo las **16 features clásicas** (F0, jitter, shimmer, HNR, NHR), excluyendo las 6 no lineales que no transfieren a audio real de campo. Las no lineales siguen extrayéndose y persistiéndose en el Feature Store para análisis y trazabilidad, pero no entran al modelo.

2. **Nuevo dataset de entrenamiento con audio real** — Se incorporó el dataset figshare [`DOI 10.6084/m9.figshare.23849127`](https://doi.org/10.6084/m9.figshare.23849127) (81 sujetos, PD/HC, grabación telefónica a 8 kHz, CC-BY), ya que el dataset Oxford (laboratorio) no transfiere a audio real (AUC fuera de dominio ~0.41-0.51).

3. **Script de reentrenamiento:** [`scripts/retrain_parkinson_classic16.py`](./scripts/retrain_parkinson_classic16.py)

4. **Métricas (preliminares, N=81, out-of-fold):**
   - **AUC-ROC:** ~0.64
   - **Umbral de decisión:** 0.40

5. **Limitaciones conocidas del modelo actual:**
   - N=81, resultado preliminar, no validado clínicamente
   - Confound de edad no corregido (PD ~67a vs HC ~48a en el dataset)
   - AUC modesto — el tamizaje tiene valor orientativo, no diagnóstico

- **Archivo activo:** `saved_models/parkinsons_model_classic16.sav`
- **Archivo activo:** `saved_models/parkinsons_scaler_classic16.sav` (StandardScaler para classic16)
- **Archivos anteriores (deprecados):**
  - `saved_models/parkinsons_model_smote.sav` — Modelo con 22 features; producía falsos positivos en audio real
  - `saved_models/parkinsons_scaler_smote.sav` — Scaler para el modelo SMOTE
  - `saved_models/parkinsons_model.sav` — Modelo XGBoost sin SMOTE
  - `saved_models/parkinsons_scaler.sav` — Scaler original
- **Entrada:** Vector de 16 biomarcadores clásicos de voz (F0, jitter, shimmer, HNR, NHR)
- **Salida:** Clasificación binaria + probabilidad (umbral 0.40)

### Modelos históricos (compatibilidad)
- **Diabetes Tipo 2** — `saved_models/diabetes_model.sav` — 8 variables clínicas
- **Enfermedad Cardiovascular** — `saved_models/heart_disease_model.sav` — 13 variables clínicas

> El desarrollo activo se centra en el módulo de Parkinson por voz. Los modelos de diabetes y cardiovascular se conservan por compatibilidad histórica.

---

## Archivos de Entrenamiento (Vigentes vs Deprecados)

### Vigentes (en uso activo)

| Archivo | Propósito |
|---------|-----------|
| `app/model_predict.py` | Carga y ejecución de modelos ML; inferencia con modelo classic16 (16 features, umbral 0.40) |
| `app/services/constants.py` | `PARKINSON_FEATURE_ORDER` (22 features, para extracción) y `PARKINSON_MODEL_FEATURE_ORDER` (16 features, para inferencia) |
| `app/services/feature_validator.py` | Validación de features extraídas vs rangos UCI; RPDE/DFA excluidos de features críticas |
| `app/services/audio_processing.py` | Extracción de biomarcadores acústicos (pipeline principal) |
| `app/services/audio_filters.py` | Preprocesamiento DSP: HP 70 Hz, LP 5 kHz, VAD trim, normalización RMS sin clipping |
| `app/services/audio_pipeline.py` | Orquestación del pipeline completo de audio (toma única) |
| `app/services/session_pipeline.py` | Agregación multi-toma: mediana por biomarcador, CV inter-toma, `session_confidence` |
| `app/services/nonlinear_features.py` | Cálculo de biomarcadores no lineales (DFA vectorizado, D2, RPDE, PPE, spread1, spread2); output persistido pero excluido del modelo |
| `app/services/voice_biomarkers.py` | Extracción de biomarcadores vía Parselmouth (endpoint directo) |
| `app/services/quality_control.py` | Control de calidad de audio (QA/QC) |
| `app/api/voice_biomarkers.py` | Endpoint REST para extracción directa de biomarcadores |
| `app/api/audio.py` | Endpoints REST de carga y procesamiento de audio (toma única) |
| `app/api/sessions.py` | Endpoints REST de sesiones multi-toma (`/sessions`); polling con margen de 240s |
| `app/models.py` | Modelos SQLAlchemy (incluye `VoiceSession`, `BiomarkerFeature`, `AudioQualityReport`) |
| `app/schemas/voice_biomarkers.py` | Schemas Pydantic para biomarcadores de voz |
| `app/schemas/quality_control.py` | Schemas Pydantic para control de calidad |
| `app/schemas/sessions.py` | Schemas Pydantic para sesiones multi-toma |
| `alembic/versions/005_voice_sessions.py` | Migración: tabla `voice_sessions` + columnas `session_id`, `take_number` |
| `saved_models/parkinsons_model_classic16.sav` | Modelo "classic16" (16 features clásicas, entrenado con audio real figshare) |
| `saved_models/parkinsons_scaler_classic16.sav` | StandardScaler para el modelo classic16 |
| `scripts/retrain_parkinson_classic16.py` | Script de reentrenamiento del modelo classic16 con dataset figshare |
| `notebooks/MedDiag_Parkinson_SMOTE_Colab.ipynb` | Notebook del modelo SMOTE anterior (referencia histórica; modelo ya reemplazado) |

### Deprecados (⛔ mantenidos solo por referencia histórica)

| Archivo | Motivo de deprecación |
|---------|----------------------|
| `Parkinsons_Caro(1).ipynb` | Notebook original de entrenamiento (Diana Huertas). Reemplazado por `Parkinsons_Model_Training_REAL_FIXED.ipynb` |
| `EXPERIMENTOS_EXTRACCION_BIOMARCADORES_VOZ_PARKINSON_COLAB.ipynb` | Notebook experimental de extracción de biomarcadores. La funcionalidad fue integrada directamente en los servicios del backend |
| `saved_models/parkinsons_model_smote.sav` | Modelo con 22 features (incluye no lineales); producía falsos positivos en audio real — reemplazado por classic16 |
| `saved_models/parkinsons_scaler_smote.sav` | Scaler para el modelo SMOTE (reemplazado por scaler classic16) |
| `saved_models/parkinsons_model.sav` | Modelo XGBoost sin SMOTE (reemplazado por classic16) |
| `saved_models/parkinsons_scaler.sav` | Scaler original (reemplazado por scaler classic16) |
| `saved_models/parkinsons_model_xgboost.sav` | Modelo XGBoost individual generado durante experimentación. No es cargado por `model_predict.py` |
| `saved_models/parkinsons_model_ensemble.sav` | Ensemble de modelos generado durante experimentación. No es cargado por `model_predict.py` |

> **Nota:** Los archivos deprecados se conservan en el repositorio para trazabilidad académica, pero no forman parte del pipeline activo de producción.

---

## Tecnologías

| Tecnología | Versión | Propósito |
|-----------|---------|-----------|
| **Python** | 3.10+ | Lenguaje principal del backend |
| **FastAPI** | Latest | Backend REST API |
| **Next.js** | 13+ | Frontend web |
| **scikit-learn** | 1.3+ | Modelos ML |
| **Librosa** | Latest | Procesamiento digital de audio |
| **Parselmouth (Praat)** | Latest | Análisis acústico de voz |
| **SciPy** | 1.7+ | Señales y matemáticas |
| **SQLite / PostgreSQL** | — | Base de datos |
| **Alembic** | — | Migraciones de base de datos |
| **Docker** | — | Contenedores |

---

## Instalación y Ejecución

### Prerrequisitos
- Python 3.10+
- npm / Node.js
- Git

### 1. Clonar el repositorio
```bash
git clone https://github.com/admaesmo/MedDiag2.git
cd MedDiag2
```

### 2. Entorno virtual
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o: venv\Scripts\activate  # Windows
```

### 3. Instalar dependencias backend
```bash
pip install -r requirements.txt
```

### 4. Variables de entorno
Crear `.env` en la raíz:
```env
DATABASE_URL=sqlite:///./meddiag.local.db
MODEL_DIR=./saved_models
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
AUTH_PROVIDER=local
JWT_SECRET_KEY=dev-secret-change-me
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
STORAGE_PROVIDER=local
STORAGE_LOCAL_PATH=./storage/audio
MAX_AUDIO_FILE_SIZE_MB=25
```

### 5. Instalar frontend
```bash
cd frontend/web
cp .env.local.example .env.local  # Ajustar si es necesario
npm install
cd ../..
```

### 6. Iniciar
```bash
# Opción 1: Script automatizado
./scripts/start-local.sh

# Opción 2: Manual (dos terminales)
# Terminal 1:
python -m uvicorn app.main:app --reload
# Terminal 2:
cd frontend/web && npm run dev
```

### 7. Acceder
- **Frontend:** http://localhost:3000
- **Backend API:** http://127.0.0.1:8000
- **Documentación API (Swagger):** http://127.0.0.1:8000/docs

### Endpoint rápido de biomarcadores
```bash
POST /audio/biomarkers/extract
```
Recibe un audio por `multipart/form-data` y retorna las 22 features más la inferencia del modelo de Parkinson. No persiste el audio.

---

## Estructura del Proyecto

```
MedDiag2/
├── app/                          # Backend FastAPI
│   ├── main.py                   # Punto de entrada
│   ├── model_predict.py          # Carga y ejecución de modelos ML
│   ├── models.py                 # Modelos SQLAlchemy
│   ├── api/                      # Endpoints REST
│   │   ├── audio.py              # Endpoints de audio (toma única)
│   │   ├── auth.py               # Autenticación
│   │   ├── sessions.py           # Endpoints de sesiones multi-toma
│   │   └── voice_biomarkers.py   # Biomarcadores de voz
│   ├── schemas/                  # Schemas Pydantic
│   │   └── sessions.py           # Schemas de sesiones
│   ├── services/                 # Lógica de negocio
│   │   ├── audio_filters.py      # Preprocesamiento DSP (HP/LP/VAD/RMS)
│   │   ├── audio_pipeline.py     # Pipeline completo de audio (toma única)
│   │   ├── audio_processing.py   # Extracción de biomarcadores
│   │   ├── audio_service.py      # Servicio de audio
│   │   ├── nonlinear_features.py # Biomarcadores no lineales
│   │   ├── quality_control.py    # Control de calidad de audio
│   │   ├── session_pipeline.py   # Agregación multi-toma y sesiones
│   │   └── voice_biomarkers.py   # Extracción de biomarcadores vía Praat
│   └── utils/                    # Utilidades
├── frontend/web/                 # Frontend Next.js
│   ├── app/                      # App Router
│   ├── components/               # Componentes (Atomic Design)
│   ├── features/                 # Hooks y mutaciones por feature
│   ├── lib/                      # Utilidades y configuración
│   │   └── i18n/                 # Internacionalización (EN, ES, PT-BR)
│   └── stores/                   # Estado global (Zustand)
├── Documentacion/                # Documentación del proyecto
│   ├── MedDiag2_paper_corregido.md           # Paper académico (vigente)
│   ├── GUIA_DESPLIEGUE_RENDER_VERCEL.md      # Guía de despliegue
│   └── PLAN_MIGRACION_MODELO.md              # Plan de migración de modelos
├── saved_models/                 # Modelos serializados (.sav)
├── scripts/                      # Scripts de inicio/parada
├── alembic/                      # Migraciones de base de datos
├── requirements.txt              # Dependencias Python
├── Dockerfile                    # Imagen Docker del backend
└── render.yaml                   # Blueprint de Render
```

---

## Documentación

| Documento | Descripción |
|-----------|-------------|
| [`MedDiag2_paper_corregido.md`](./Documentacion/MedDiag2_paper_corregido.md) | Paper académico completo con metodología, resultados y discusión |
| [`GUIA_DESPLIEGUE_RENDER_VERCEL.md`](./Documentacion/GUIA_DESPLIEGUE_RENDER_VERCEL.md) | Guía de despliegue en Render + Vercel |
| [`PLAN_MIGRACION_MODELO.md`](./Documentacion/PLAN_MIGRACION_MODELO.md) | Plan de migración del modelo de Parkinson |
| API Docs | Swagger en `/docs` (servidor corriendo) |

---

## Limitaciones

1. **No es diagnóstico clínico** — Solo entrega una proyección preliminar experimental.
2. **Dataset limitado** — El modelo classic16 se entrenó con N=81 (dataset figshare, audio real). El dataset Oxford original (197 muestras, laboratorio) no transfiere a audio de campo.
3. **Confound de edad no corregido** — En el dataset figshare, los sujetos PD tienen ~67 años en promedio vs ~48 años para HC. El modelo puede estar capturando efectos de edad además de Parkinson.
4. **AUC modesto** — AUC out-of-fold ~0.64; el tamizaje tiene valor orientativo solamente.
5. **Features no lineales fuera del modelo** — RPDE, DFA, spread1, spread2, D2 y PPE se extraen y persisten, pero no alimentan la inferencia porque quedan clampeadas al límite UCI en el 74-100% de grabaciones reales de celular/web. Esta discrepancia de dominio (laboratorio vs campo) aún no está resuelta.
6. **Sensibilidad al audio** — Ruido, micrófono, distancia e intensidad afectan los biomarcadores, especialmente los no lineales.
7. **Aproximaciones algorítmicas** — Varias medidas son aproximaciones propias, no equivalentes exactos de MDVP o Praat.
8. **Sin validación clínica** — No se ha evaluado con pacientes reales ni profesionales médicos.
9. **Riesgo de sobreinterpretación** — Una probabilidad puede malentenderse sin el contexto y advertencias adecuadas.

---

## Trabajo Futuro

- [x] Implementar preprocesamiento DSP (HP/LP/VAD/normalización) — `audio_filters.py`
- [x] Implementar análisis de múltiples tomas con agregación robusta — `session_pipeline.py`
- [x] Integrar flujo multi-toma en el frontend (interfaz obligatoria de N tomas)
- [x] Diagnosticar y corregir falsos positivos sistemáticos por features no lineales clampeadas
- [x] Reentrenar modelo con audio real (dataset figshare, 81 sujetos) — modelo "classic16"
- [x] Vectorizar `compute_dfa` para eliminar timeout de procesamiento en producción (Render)
- [ ] Corregir confound de edad en el dataset de entrenamiento (PD ~67a vs HC ~48a)
- [ ] Ampliar dataset de entrenamiento con audio real para superar N=81
- [ ] Resolver brecha de dominio para features no lineales: validar si con audio de alta calidad salen del clamp UCI, o buscar re-escalado adecuado
- [ ] Congelar extractor clásico con Parselmouth/Praat para F0, jitter, shimmer y HNR
- [ ] Reemplazar uso de `0.0` como fallback por política formal `partial_features` o `missing_features`
- [ ] Validar parámetros DSP con audios controlados (medir impacto real en biomarcadores)
- [ ] Comparar Parselmouth vs openSMILE y DisVoice
- [ ] Explorar embeddings profundos (Wav2Vec2, HuBERT, WavLM) con banco de audios suficiente

---

## Licencia

MIT © 2025-2026 — Proyecto Integrador — Ingeniería de Sistemas

**Autores:** Adrián Espinosa, Diana Huertas, David Ríos  
**Docente asesor:** Sandra Patricia Zabala Orrego  
**Facultad de Ingeniería — Departamento de Ingeniería de Sistemas**  
**Universidad de Antioquia** — Medellín, Colombia

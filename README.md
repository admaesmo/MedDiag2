# MedDiag2 — Tamizaje experimental de Parkinson mediante análisis de voz

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-13+-black?logo=nextdotjs&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Descripción General

**MedDiag2** es una plataforma web de **tamizaje experimental** de la enfermedad de Parkinson mediante análisis de voz. El sistema permite a los usuarios grabar o subir una muestra de voz sostenida, extraer automáticamente **22 biomarcadores acústicos** (F0, jitter, shimmer, HNR, NHR, y parámetros no lineales como DFA, D2, RPDE, PPE), y obtener una **predicción preliminar basada en machine learning**.

El proyecto integra:
- **Frontend** en Next.js con interfaz para grabación/carga de audio, historial y visualización de resultados.
- **Backend** en FastAPI con pipeline completo de procesamiento de señales.
- **Pipeline de audio** con extracción de biomarcadores, control de calidad y trazabilidad mediante Feature Store versionado.
- **Modelos ML** serializados para inferencia (Parkinson, y compatibilidad histórica con diabetes y enfermedad cardiovascular).

> ⚠️ **Importante:** MedDiag2 es una **herramienta académica experimental de apoyo**, no un sistema de diagnóstico clínico. No reemplaza la evaluación de un profesional de la salud.

---

## Tabla de Contenidos

- [Estado del Proyecto](#estado-del-proyecto)
- [Objetivos](#objetivos)
- [Arquitectura](#arquitectura)
- [Pipeline de Análisis de Voz](#pipeline-de-análisis-de-voz)
- [Biomarcadores Extraídos](#biomarcadores-extraídos)
- [Modelos ML](#modelos-ml)
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
| Biomarcadores no lineales | ✅ Implementados | DFA, D2, PPE, RPDE, spread1, spread2 (rama `marcadoresNL`) |
| Feature Store | ✅ Implementado | Versionado con `extractor_version` y `feature_schema_version` |
| Inferencia | ✅ Funcional | Predicción preliminar con probabilidad |
| Frontend (grabación/carga) | ✅ Funcional | Interfaz de usuario con autenticación |
| Control de calidad de audio | ⏳ Pendiente | Servicio dedicado por implementar |
| Parselmouth como extractor base | ⏳ Pendiente | Actualmente se usa Librosa como ruta principal |
| Validación clínica | ❌ Pendiente | Sin evaluación con pacientes reales |

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
│  Decodificación   │  Librosa (principal) → Pydub (fallback)
│  y normalización │  Mono, frecuencia controlada
└──────────────────┘
      │
      ▼
┌──────────────────┐
│  Extracción F0    │  librosa.pyin → Parselmouth → SciPy (fallback)
└──────────────────┘
      │
      ▼
┌────────────────────────┐
│  Extracción de         │  Jitter, shimmer, HNR, NHR
│  biomarcadores         │  DFA, D2, RPDE, PPE, spread1, spread2
└────────────────────────┘
      │
      ▼
┌──────────────────┐
│  Feature Store    │  Persistencia con versión del extractor
└──────────────────┘
      │
      ▼
┌──────────────────┐
│  Inferencia       │  Modelo de Parkinson → predicción + probabilidad
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
- **Implementaciones determinísticas propias** para biomarcadores no lineales (rama `marcadoresNL`)
- **Aproximación cepstral** para NHR/HNR

---

## Modelos ML

### Modelo principal: Parkinson
- **Archivo:** `saved_models/parkinsons_model.sav`
- **Dataset:** Oxford Parkinson's Disease Detection Dataset (UCI)
- **Entrada:** Vector de 22 biomarcadores de voz
- **Salida:** Clasificación binaria + probabilidad
- **Rendimiento:** Accuracy ~88.3%, AUC-ROC ~0.93

### Modelos históricos (compatibilidad)
- **Diabetes Tipo 2** — 8 variables clínicas
- **Enfermedad Cardiovascular** — 13 variables clínicas

> El desarrollo activo se centra en el módulo de Parkinson por voz. Los modelos de diabetes y cardiovascular se conservan por compatibilidad histórica.

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
│   │   ├── audio.py              # Endpoints de audio
│   │   ├── auth.py               # Autenticación
│   │   └── voice_biomarkers.py   # Biomarcadores de voz
│   ├── schemas/                  # Schemas Pydantic
│   ├── services/                 # Lógica de negocio
│   │   ├── audio_pipeline.py     # Pipeline completo de audio
│   │   ├── audio_processing.py   # Procesamiento de señales
│   │   ├── audio_service.py      # Servicio de audio
│   │   ├── nonlinear_features.py # Biomarcadores no lineales
│   │   └── voice_biomarkers.py   # Extracción de biomarcadores
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
│   ├── Justificación de la ruta actual....md # ⛔ Deprecado
│   └── INVESTIGACION_BIOMARCADORES_VOZ_...md # Investigación técnica
├── saved_models/                 # Modelos serializados (.sav)
├── scripts/                      # Scripts de inicio/parada
├── alembic/                      # Migraciones de base de datos
├── DEPLOY.md                     # Guía de despliegue
├── requirements.txt              # Dependencias Python
├── Dockerfile                    # Imagen Docker del backend
└── render.yaml                   # Blueprint de Render
```

---

## Documentación

| Documento | Descripción |
|-----------|-------------|
| [`MedDiag2_paper_corregido.md`](./Documentacion/MedDiag2_paper_corregido.md) | Paper académico completo con metodología, resultados y discusión |
| [`INVESTIGACION_BIOMARCADORES_VOZ_PARKINSON.markdown.md`](./Documentacion/INVESTIGACION_BIOMARCADORES_VOZ_PARKINSON.markdown.md) | Investigación técnica sobre biomarcadores y librerías |
| [`DEPLOY.md`](./DEPLOY.md) | Guía de despliegue en Render + Vercel |
| [`frontend/web/README.md`](./frontend/web/README.md) | Documentación del frontend |
| API Docs | Swagger en `/docs` (servidor corriendo) |

---

## Limitaciones

1. **No es diagnóstico clínico** — Solo entrega una proyección preliminar experimental.
2. **Dataset limitado** — Modelo basado en dataset público pequeño (197 muestras, 31 personas).
3. **Sensibilidad al audio** — Ruido, micrófono, distancia e intensidad afectan los biomarcadores.
4. **Aproximaciones algorítmicas** — Varias medidas son aproximaciones propias, no equivalentes exactos de MDVP o Praat.
5. **Valores `0.0` como placeholder** — Cuando una feature no puede calcularse, se usa `0.0` por compatibilidad. Esto debe reemplazarse por una política formal de features parciales.
6. **Sin validación clínica** — No se ha evaluado con pacientes reales ni profesionales médicos.
7. **Riesgo de sobreinterpretación** — Una probabilidad puede malentenderse sin el contexto y advertencias adecuadas.

---

## Trabajo Futuro

- [ ] Congelar extractor clásico con Parselmouth/Praat para F0, jitter, shimmer y HNR
- [ ] Implementar servicio formal de control de calidad de audio
- [ ] Reemplazar uso de `0.0` por política `partial_features` o `missing_features`
- [ ] Diseñar pruebas con 3 repeticiones por persona, vocal `/a/` de 3-5s
- [ ] Comparar Parselmouth vs openSMILE y DisVoice
- [ ] Evaluar modelos: Random Forest, SVM, Logistic Regression, XGBoost
- [ ] Reentrenar modelo solo con features del pipeline definitivo
- [ ] Explorar embeddings profundos (Wav2Vec2, HuBERT, WavLM) con banco de audios suficiente

---

## Licencia

MIT © 2025-2026 — Proyecto Integrador — Ingeniería de Sistemas

**Autores:** Adrián Espinosa, Diana Huertas, David Ríos  
**Docente asesor:** Sandra Patricia Zabala Orrego  
**Universidad:** [Institución] — Medellín, Colombia

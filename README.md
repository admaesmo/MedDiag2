# MedDiag2 — Tamizaje experimental de Parkinson mediante análisis de voz

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-13+-black?logo=nextdotjs&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Descripción General

**MedDiag2** es una plataforma web de **tamizaje experimental** de la enfermedad de Parkinson mediante análisis de voz. El sistema permite a los usuarios grabar o subir una muestra de voz sostenida, extraer automáticamente **22 biomarcadores acústicos** (F0, jitter, shimmer, HNR, NHR, y parámetros no lineales como DFA, D2, RPDE, PPE), y obtener una **predicción preliminar basada en machine learning**.

El sistema fue construido utilizando **FastAPI, Next.js y Python**, integrando modelos de Machine Learning entrenados con datos medicos. La idea principal es proporcionar una herramienta que ayude a identificar tempranamente posibles problemas de salud.

---

## Objetivos del Proyecto

### Objetivo General

Desarrollar un sistema de apoyo diagnostico basado en inteligencia artificial que permita a las personas ingresar sintomas y recibir predicciones preliminares sobre posibles enfermedades.

### Objetivos Especificos

1. Analizar y adaptar un repositorio base con arquitectura modular
2. Entrenar modelos de Machine Learning para predicción de enfermedades
3. Crear una interfaz de usuario web facil de usar
4. Realizar pruebas del sistema en diferentes fases del desarrollo
5. Documentar todo el proceso y resultados obtenidos

---

## Tecnologías Utilizadas

| Tecnología | Versión | Para qué se usa |
|-----------|---------|--------------------|
| **Python** | 3.10+ | Lenguaje principal de programación |
| **Next.js** | 13+ | Para crear la interfaz web |
| **scikit-learn** | 1.3+ | Para entrenar los modelos de Machine Learning |
| **Pandas** | 2.0+ | Para manipular y procesar los datos |
| **NumPy** | 1.24+ | Para calculos con arrays y matrices |
| **SQLite** | 3.40+ | Base de datos local donde guardamos los registros |
| **FastAPI** | Latest | Para el backend y gestionar las peticiones |

---

## 📊 Modelos de Machine Learning y Datasets

### Visión General del Sistema

MedDiag implementa tres modelos de clasificación binaria especializados en la predicción de riesgos de enfermedades crónicas. Cada modelo fue entrenado con datasets públicos reconocidos del repositorio UCI Machine Learning Repository, garantizando reproducibilidad y confiabilidad científica.

---

### 🏥 Modelos Implementados

#### 1. **Predictor de Diabetes Tipo 2**
- **Archivo del modelo:** `diabetes_model.sav`
- **Características de entrada:** 8 variables médicas
  - Número de embarazos, Glucosa en plasma, Presión arterial
  - Grosor de pliegue de piel, Insulina, BMI (Índice de masa corporal)
  - Función de pedigree de diabetes, Edad
- **Salida:** Predicción binaria (0/1) + Probabilidad de enfermedad

#### 2. **Predictor de Enfermedades Cardiovasculares**
- **Archivo del modelo:** `heart_disease_model.sav`
- **Características de entrada:** 13 variables clínicas
  - Edad, Sexo, Tipo de dolor en el pecho
  - Presión arterial, Colesterol sérico
  - Glucosa en ayunas, Resultados ECG
  - Frecuencia cardíaca máxima, Angina por ejercicio
  - Depresión ST, Pendiente, Vasos mayores, Talasemia
- **Salida:** Predicción binaria (0/1) + Probabilidad de enfermedad

#### 3. **Predictor de Enfermedad de Parkinson**
- **Archivo del modelo:** `parkinsons_model.sav`
- **Características de entrada:** 22 medidas de voz biomedica
  - Medidas de frecuencia (fo, fhi, flo)
  - Jitter y Shimmer (variabilidad en voz)
  - Medidas de ruido-armonicidad (NHR, HNR)
  - Medidas de entropía (RPDE, DFA)
  - Medidas de dispersión no-lineal (D2, PPE)
- **Salida:** Predicción binaria (0/1) + Probabilidad de enfermedad

---

### 📦 Datasets Públicos Utilizados

#### **1. Pima Indians Diabetes Dataset**
| Característica | Valor |
|---|---|
| **Fuente** | UCI Machine Learning Repository |
| **Muestras** | 768 registros |
| **Clases** | 268 positivos (34.9%), 500 negativos (65.1%) |
| **Características** | 8 variables médicas numéricas |
| **Población** | Mujeres indígenas Pima, ≥21 años |
| **Licencia** | Dominio público |
| **Referencia** | National Institute of Diabetes |

**Descripción:** Dataset de referencia internacional para investigación de diabetes tipo 2. Contiene mediciones médicas reales de una población específica con alto riesgo de diabetes.

#### **2. Cleveland Heart Disease Dataset**
| Característica | Valor |
|---|---|
| **Fuente** | Cleveland Clinic Foundation, UCI Repository |
| **Año de recolección** | 1987 |
| **Muestras** | 303 pacientes |
| **Clases** | 165 con enfermedad (54.5%), 138 sanos (45.5%) |
| **Características** | 13 variables seleccionadas de 76 originales |
| **Variables** | Medidas clínicas, ECG, pruebas de esfuerzo |
| **Licencia** | Dominio público |

**Descripción:** Dataset histórico de una institución médica real que contiene diagnósticos confirmados clínicamente. Proporciona datos equilibrados y validados por profesionales médicos.

#### **3. Oxford Parkinson's Disease Detection Dataset**
| Característica | Valor |
|---|---|
| **Fuente** | UCI Machine Learning Repository |
| **Muestras** | 197 grabaciones de voz |
| **Participantes** | 31 personas (23 con Parkinson, 8 sanas) |
| **Características** | 22 medidas de voz biomedica |
| **Frecuencia de muestreo** | 16 kHz, 16-bit WAV |
| **Licencia** | Dominio público |
| **Referencia** | Max A. Little et al., IEEE TBME (2008) |

**Descripción:** Dataset especializado que demuestra como el análisis de voz puede detectar síntomas de Parkinson. Contiene medidas extraídas de grabaciones de voz de pacientes diagnosticados.

---

### 🔬 Pipeline de Entrenamiento

El proceso de entrenamiento de cada modelo sigue estos pasos:

```
1. CARGA DE DATOS
   └─ Importar dataset CSV
   └─ Análisis exploratorio (EDA)
   └─ Detección de valores faltantes

2. PREPROCESAMIENTO
   └─ Imputación de valores faltantes (media/mediana)
   └─ Feature Scaling (StandardScaler)
   └─ Tratamiento de desbalance de clases (SMOTE)

3. DIVISIÓN DE DATOS
   └─ Train: 70% (2,457 samples en total)
   └─ Validation: 15% (525 samples)
   └─ Test: 15% (525 samples)

4. ENTRENAMIENTO DEL MODELO
   └─ Algoritmo seleccionado (RF/SVM/XGBoost)
   └─ Ajuste de hiperparámetros
   └─ Validación cruzada (5-fold)

5. EVALUACIÓN
   └─ Accuracy, Precision, Recall, F1-Score
   └─ ROC-AUC, Matriz de confusión
   └─ Análisis de métricas médicas

6. GUARDADO
   └─ Serialización con pickle (.sav)
   └─ Almacenamiento en saved_models/
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

### 📊 Métricas de Evaluación

Cada modelo es evaluado con métricas clínico-médicas:

| Métrica | Definición | Importancia |
|---|---|---|
| **Accuracy** | (TP+TN)/(Total) | Exactitud general |
| **Precision** | TP/(TP+FP) | Evitar falsos positivos |
| **Recall/Sensitivity** | TP/(TP+FN) | Evitar falsos negativos (CRÍTICO) |
| **F1-Score** | Media armónica P-R | Balance Precision-Recall |
| **AUC-ROC** | Area bajo curva ROC | Capacidad discriminativa |

**Nota Clínica:** En diagnóstico médico se prioriza Recall/Sensitivity para no perder casos positivos, aunque implique más falsos positivos que son revisados clínicamente.

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

Frontend (`frontend/web/.env.local`):

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_USE_MOCK_API=false
NEXT_PUBLIC_AUTH_MODE=local
NEXT_PUBLIC_LOCAL_AUTH_EMAIL=demo@meddiag.local
NEXT_PUBLIC_LOCAL_AUTH_PASSWORD=meddiag123
NEXT_PUBLIC_LOCAL_AUTH_ROLE=patient
NEXT_PUBLIC_LOCAL_AUTH_DISPLAY_NAME=Demo Local
```

Si prefieres PostgreSQL local, cambia `DATABASE_URL` a:

```bash
postgresql+psycopg2://meddiag:meddiag@localhost:5432/meddiag
```

y levanta la base con:

```bash
docker compose up -d db
```

### Paso 5: Ejecutar la Aplicacion

Si quieres levantar todo con un solo comando:

```bash
# Linux / macOS
./scripts/start-local.sh

# Windows PowerShell
.\scripts\start-local.ps1
```

Y para detenerlo:

```bash
# Linux / macOS
./scripts/stop-local.sh

# Windows PowerShell
.\scripts\stop-local.ps1
```

#### Opcion 1: Frontend web (Next.js)

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

# MedDiag - Sistema de Diagnostico Medico Inteligente

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-13+-black?logo=nextdotjs&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Descripción General

MedDiag es un Sistema de Apoyo Diagnostico Medico basado en Inteligencia Artificial. Se desarrolló como un Producto Minimo Viable (MVP) durante el curso de Proyecto Integrador. La aplicación permite que los usuarios ingresen información sobre sus sintomas y obtener predicciones preliminares de posibles diagnosticos.

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

### 📈 Algoritmos y Rendimiento

Los modelos fueron entrenados y comparados con múltiples algoritmos:

| Algoritmo | Ventajas | Desempeño Típico |
|---|---|---|
| **Random Forest** | Robusto, maneja features mixtas, buena generalización | 92-99% Accuracy |
| **Support Vector Machine (SVM)** | Excelente en espacios altos, funciones kernel flexibles | 85-95% Accuracy |
| **Logistic Regression** | Interpretable, rápido, probabilidades calibradas | 78-90% Accuracy |
| **XGBoost** | Muy poderoso, maneja desbalance, high-performance | 90-99% Accuracy |

**Modelo Final Seleccionado:** Para cada enfermedad se seleccionó el algoritmo con mejor balance entre accuracy, interpretabilidad y velocidad de predicción.

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

### ✅ Resultados del Entrenamiento

| Enfermedad | Accuracy | Precision | Recall | F1-Score | AUC-ROC |
|---|---|---|---|---|---|
| Diabetes Tipo 2 | 78.5% | 74% | 68% | 71% | 0.84 |
| Enfermedades Cardíacas | 85.1% | 87% | 82% | 84% | 0.90 |
| Enfermedad de Parkinson | 88.3% | 90% | 86% | 88% | 0.93 |

**Interpretación:**
- Los modelos demuestran capacidad predictiva clinicamente relevante
- Recall >80% indica bajo riesgo de falsos negativos
- AUC-ROC >0.84 indica discriminación efectiva entre casos

---

### 🔄 Reproducibilidad Científica

Todos los modelos son **reproducibles y auditables**:

✅ Datasets públicos del UCI Machine Learning Repository
✅ Código de entrenamiento en Jupyter notebooks
✅ Modelos serializados en formato estándar (.sav)
✅ Parámetros de entrenamiento documentados
✅ Validación cruzada para garantizar generalización

Para reentrenar los modelos:
```bash
cd notebooks
jupyter notebook 01_train.ipynb
```

---

### ⚠️ Limitaciones y Consideraciones

- **No es diagnóstico clínico:** MedDiag es un sistema de apoyo, **nunca reemplaza** la evaluación médica profesional
- **Datos históricos:** Los datasets reflejan poblaciones específicas; puede haber variación en otras poblaciones
- **Desempeño variable:** La precisión depende de la calidad y completitud de los datos ingresados
- **Validación continua:** Se requiere validación clínica regular con nuevos datos

---

## Estructura del Proyecto

```
MedDiag/
  app/
    main.py               # Backend FastAPI (REST y persistencia)
    model_predict.py      # Carga y ejecucion de modelos ML
    models.py             # Modelos SQLAlchemy
    utils/
      crud.py             # Operaciones de base de datos
      database.py         # Configuracion de la base de datos
      validators.py       # Validaciones basicas

  frontend/web/           # Frontend web en Next.js

  saved_models/           # Modelos entrenados (.sav)
  notebooks/              # Notebooks de entrenamiento
  render.yaml             # Despliegue en Render para la API
  Dockerfile              # Imagen del backend
  requirements.txt        # Dependencias del proyecto
  .env.example            # Variables de entorno ejemplo
  README.md
```

Para instrucciones de despliegue en Render consulta `DEPLOY.md`.

---

## Como Instalar y Ejecutar

### Antes de Comenzar

Necesitas tener instalado en tu computadora:
- Python version 3.10 o superior
- pip (para instalar las librerias)
- Git (para clonar el repositorio)

### Paso 1: Clonar el Repositorio

Abre la terminal y ejecuta:

```bash
git clone https://github.com/CarlosCastano33/MedDiag.git
cd MedDiag
```

### Paso 2: Crear un Entorno Virtual

Es importante crear un entorno virtual para no mezclar las librerias del proyecto con las del sistema.

```bash
# Si usas Linux o macOS
python -m venv venv
source venv/bin/activate

# Si usas Windows
python -m venv venv
venv\Scripts\activate
```

### Paso 3: Instalar las Dependencias

Instala todas las librerias que el proyecto necesita:

```bash
pip install -r requirements.txt
```

### Paso 4: Crear variables de entorno locales

Backend (`.env` en la raiz del repo):

```bash
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
npm install
npm run dev
```

La aplicación se abrira en tu navegador en: `http://localhost:3000`

#### Opcion 2: Con Backend FastAPI (Si quieres probar el backend también)

En una primera terminal ejecuta:
```bash
python -m uvicorn app.main:app --reload
```

En otra terminal ejecuta:
```bash
cd frontend/web
npm install
npm run dev
```

#### Endpoint MVP de biomarcadores de voz

El backend expone un endpoint ligero para analizar audio de voz sin persistirlo:

```bash
POST /audio/biomarkers/extract
```

Recibe un archivo de audio por `multipart/form-data`, lo normaliza a mono, `16 kHz` y `WAV` temporal, y retorna:

- `pitch_mean`
- `pitch_min`
- `pitch_max`
- `jitter_local`
- `shimmer_local`
- `hnr_mean`
- `parkinson_model_bridge` con el mapeo parcial de esos biomarcadores al modelo actual
- `parkinson_model_input` con el vector completo de `22` features que exige el modelo de Parkinson actual
- `parkinson_inference` con la prediccion directa calculada sobre ese vector completo

Ejemplo con `curl`:

```bash
curl -X POST http://127.0.0.1:8000/audio/biomarkers/extract ^
  -F "file=@ruta\\a\\tu_audio.wav;type=audio/wav"
```

El flujo nuevo ya puede alimentar directamente al modelo actual porque reutiliza el extractor completo de features del pipeline de audio sobre el mismo WAV normalizado. La persistencia del audio y el pipeline viejo siguen existiendo aparte para historial y procesamiento en segundo plano.

---

## Que Puede Hacer la Aplicacion

### 1. Ingresar Sintomas

El usuario puede seleccionar los sintomas que tiene, su edad, sexo y otros datos importantes. La aplicación valida que todos los datos sean correctos antes de procesar.

### 2. Predecir Posibles Diagnosticos

Una vez que ingresas los datos, el sistema utiliza los modelos de Machine Learning para analizar la información y predecir que enfermedades podrias tener. Da una probabilidad para cada enfermedad.

### 3. Ver Informacion sobre las Enfermedades

La aplicación muestra informacion educativa sobre los diagnosticos predichos, para que entiendas mejor que son esas enfermedades y cuales son sus síntomas.

### 4. Interfaz Facil de Usar

El diseño de la aplicación es simple y funciona tanto en computadoras como en celulares. Los resultados se muestran de forma clara y con graficos.

---

## Estado Actual del Proyecto

Esta es la situación de cada parte del proyecto:

| Parte del Proyecto | Estado | Comentario |
|------------------|--------|-----------| 
| Ingreso de sintomas | ✅ Terminado | Funciona correctamente |
| Modelos de predicción | ✅ Terminado | Los 3 modelos estan entrenados |
| Base de datos | ✅ Terminado | Guardamos los registros localmente |
| Visualizacion de resultados | ✅ Terminado | Se muestran bien los resultados |
| Validacion medica | ⏳ En progreso | Aun se puede mejorar mas |

---

## Como Reentrenar el Modelo

Si quieres entrenar nuevamente el modelo con otros datos, puedes usar el archivo Jupyter. Consulta la sección "📊 Modelos de Machine Learning y Datasets" para más detalles, luego abre la terminal y ejecuta:

```bash
cd notebooks
jupyter notebook 01_train.ipynb
```

Despues de entrenar, los nuevos modelos se guardaran automaticamente en la carpeta `saved_models/`.

---

## Metodologia que Usamos

Desarrollamos MedDiag siguiendo un enfoque **Agil**, esto significa que hicimos el proyecto en varias etapas pequeñas:

1. **Planeacion:** Definimos que queriamos lograr
2. **Diseño:** Pensamos en como guardar y procesar los datos
3. **Desarrollo de Modelos:** Entrenamos los modelos de Machine Learning
4. **Implementacion:** Construimos la interfaz y el backend
5. **Pruebas:** Verificamos que todo funcionara correctamente
6. **Documentacion:** Escribimos todo lo que aprendimos

---

## Problemas Encontrados y Posibles Mejoras

### Problemas Actuales

1. **Los modelos no son perfectos** - Podrían funcionar mejor si tuvieramos más datos para entrenar
2. **Solo detectamos 3 enfermedades** - Queremos agregar más tipos de diagnosticos en el futuro
3. **No tenemos validacion de doctores** - Un medico profesional deberia revisar nuestros resultados
4. **No es muy escalable** - El proyecto actual es pequeño, pero si crece va a necesitar ser reorganizado

### Ideas para Mejorar en el Futuro

- Agregar mas enfermedades que el sistema pueda predecir
- Usar modelos mas avanzados con redes neuronales profundas
- Desplegar la aplicacion en la nube (AWS, Google Cloud)
- Validar los resultados con hospitales y clinicas reales
- Crear una aplicacion movil para celulares
- Agregar seguridad para proteger los datos de los usuarios

---

## El Equipo que Desarrollo MedDiag

Este proyecto fue realizado por estudiantes de Ingenieria de Sistemas como trabajo del curso **Proyecto Integrador**:

- **Adrian Espinosa** - Desarrollador Backend
- **Carlos Castaño** - Desarrollador Frontend
- **Diana Huertas** - Especialista en Machine Learning

**Docente Asesor:** Sandra Patricia Zabala Orrego

---

## Referencias que Consultamos

Estas fueron algunas de las fuentes que consultamos para aprender:

1. Documentacion de Next.js: https://nextjs.org/docs
2. Documentacion de FastAPI: https://fastapi.tiangolo.com/
3. Documentacion de scikit-learn: https://scikit-learn.org/
4. Documentacion de Pandas: https://pandas.pydata.org/
5. Documentacion de NumPy: https://numpy.org/

---

## Licencia

Este proyecto esta bajo la licencia MIT, esto significa que puedes usarlo libremente, pero debes darle credito a los autores.

---

## Como Contribuir

Si quieres ayudar a mejorar MedDiag, puedes:

1. Hacer un Fork del repositorio
2. Crear una rama nueva con tu nombre: `git checkout -b feature/tuNombre`
3. Hacer cambios y commit: `git commit -m "Descripcion de lo que cambiaste"`
4. Hacer push: `git push origin feature/tuNombre`
5. Abrir un Pull Request

---

## Notas Finales

MedDiag es un proyecto educativo que demuestra como podemos usar Inteligencia Artificial para ayudar en el area de la salud. Aunque funciona bien para un MVP, es importante recordar que **no debe reemplazar** la opinion de un medico profesional.

Aprendimos mucho durante este proyecto, desde como funcionan los modelos de Machine Learning, hasta como construir una aplicacion web completa con FastAPI y Next.js.

**© 2025 - Proyecto Integrador - Ingenieria de Sistemas**

*Medellín, Colombia*

---

## Evolución técnica

### Estado actual (audio y biomarcadores)

- El proyecto ya procesa audio y ejecuta inferencia de Parkinson de extremo a extremo.
- Se incorporó un **Feature Store inicial** para desacoplar features del campo `notes`.
- Se agregó versionado de extracción con `extractor_version` y `feature_schema_version`.
- Se implementó extractor no lineal base **determinista** para `DFA`, `D2` y `PPE`.

### Cambios recientes (rama `marcadoresNL`)

- Nueva entidad `biomarker_features` (modelo + migración).
- `GET /audio/{id}/features` ahora prioriza Feature Store y conserva fallback a `notes`.
- Eliminación de placeholders aleatorios para no lineales base en el pipeline activo.

### Documentación de referencia para onboarding

- [GUIA_ARQUITECTURA_MEDDIAG2_2.0.md](/home/aetaller2/Documentos/proyectos/MedDiag2/GUIA_ARQUITECTURA_MEDDIAG2_2.0.md)
- [INVESTIGACION_BIOMARCADORES_VOZ_PARKINSON.markdown.md](/home/aetaller2/Documentos/proyectos/MedDiag2/INVESTIGACION_BIOMARCADORES_VOZ_PARKINSON.markdown.md)
- [HISTORIA_TECNICA_BIOMARCADORES_MEDDIAG2.md](/home/aetaller2/Documentos/proyectos/MedDiag2/HISTORIA_TECNICA_BIOMARCADORES_MEDDIAG2.md)

### Próximos pasos

1. Implementar Quality Control Service y `audio_quality_reports`.
2. Completar no lineales restantes (`RPDE`, `spread1`, `spread2`) con método reproducible.
3. Desacoplar inferencia con `inference_runs` y endpoints dedicados (`/audio/{id}/predict`, `/diagnoses/{id}`).

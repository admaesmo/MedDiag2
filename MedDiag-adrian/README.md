

````markdown
#  MedDiag – MVP (Producto Mínimo Viable)

**MedDiag** es un prototipo de aplicación de apoyo diagnóstico médico que utiliza **Inteligencia Artificial** para analizar síntomas y sugerir posibles diagnósticos preliminares.  
Este MVP está desarrollado en **Python**, empleando frameworks livianos y fácilmente desplegables, con el propósito de validar la funcionalidad central del sistema antes de su versión empresarial.

---

##  Objetivo del MVP

El objetivo principal del MVP es **demostrar la viabilidad funcional del modelo de diagnóstico automático**, integrando un flujo simple que va desde la **entrada de síntomas** por parte del usuario hasta la **predicción de la posible enfermedad** basada en modelos entrenados.

---

##  Arquitectura General

El MVP sigue una arquitectura **monolítica** simple compuesta por tres capas principales:

1. **Interfaz de usuario (Frontend):**
   - Construida con **Streamlit**.
   - Permite ingresar síntomas, edad, sexo y otros parámetros básicos.
   - Muestra los resultados del modelo predictivo de forma clara y visual.

2. **Backend / API interna:**
   - Desarrollado con **FastAPI**.
   - Gestiona las peticiones entre la interfaz y los modelos de predicción.
   - Procesa los datos y devuelve el diagnóstico.

3. **Módulo de predicción:**
   - Implementado con modelos de **Machine Learning** (scikit-learn / TensorFlow).
   - Entrenado con dataset médico anonimizado.
   - Evalúa probabilidades de enfermedades basadas en los síntomas registrados.



##  Tecnologías Utilizadas

| Componente           | Tecnología                              | Descripción                               |
| -------------------- | --------------------------------------- | ----------------------------------------- |
| Lenguaje principal   | **Python 3.10+**                        | Desarrollo general del MVP                |
| Interfaz gráfica     | **Streamlit**                           | Aplicación interactiva para usuarios      |
| ML / IA              | **scikit-learn**, **pandas**, **numpy** | Entrenamiento y predicción de datos       |
| Base de datos        | **SQLite** (temporal)                   | Almacenamiento local de registros médicos |
| Control de versiones | **Git / GitHub**                        | Gestión de ramas y versiones del proyecto |

---

##  Estructura del Proyecto

```
MedDiag/
│
├── app/
│   ├── main.py              # Lógica principal del backend FastAPI
│   ├── model_predict.py     # Carga y ejecución del modelo de IA
│   ├── data/                # Dataset usado para entrenamiento
│   └── utils/               # Funciones auxiliares
│
├── frontend/
│   └── app_streamlit.py     # Interfaz de usuario (Streamlit)
│
├── models/
│   └── trained_model.pkl    # Modelo entrenado (versión MVP)
│
├── notebooks/
│   └── 01_train.ipynb       # Script de entrenamiento del modelo
│
├── requirements.txt         # Dependencias del proyecto
├── README.md                # Este archivo
└── LICENSE
```

---

##  Instalación y Ejecución

### 1️ Clonar el repositorio

```bash
git clone https://github.com/CarlosCastano33/MedDiag.git
cd MedDiag
git checkout carlos   # Rama MVP
```

### 2️ Crear y activar entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux / macOS
venv\Scripts\activate     # Windows
```

### 3️ Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4️ Ejecutar el backend (FastAPI)

```bash
cd app
uvicorn main:app --reload
```

### 5️ Ejecutar la interfaz (Streamlit)

```bash
cd frontend
streamlit run app_streamlit.py
```

---


##  Estado del MVP

| Módulo              | Estado       | Descripción                                 |
| ------------------- | ------------ | ------------------------------------------- |
| Carga de síntomas   | ✅ Completado | Entrada de datos funcional                  |
| Predicción IA       | ✅ Completado | Modelo de clasificación en producción local |
| Base de datos local | 🟡 Parcial   | Uso temporal de SQLite                      |
| Panel de resultados | 🟡 En mejora | Visualización de métricas de predicción     |
| Validación médica   | 🔴 Pendiente | En etapa de diseño y pruebas                |

---

##  Pruebas y Entrenamiento

Para ejecutar pruebas o reentrenar el modelo:

```bash
cd notebooks
jupyter notebook 01_train.ipynb
```

El modelo resultante se guarda en `models/trained_model.pkl`.

---

##  Equipo de Desarrollo

* **Dina Reale** 
* **Carlos Castaño**  
* **Adrian Espinosa** 





---



**© 2025 – Proyecto MedDiag**
Desarrollado como prototipo académico de apoyo diagnóstico con IA.

```


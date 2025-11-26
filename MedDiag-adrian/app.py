import os
import pickle
import streamlit as st
from streamlit_option_menu import option_menu
from translations import translations
from flags import get_flag

from database import engine, SessionLocal
from models import Base
from crud import (
    get_or_create_user,
    seed_default_diseases,
    create_diagnosis_with_single_candidate,
    get_recent_diagnoses,
    get_diagnoses_by_user_email,
)

# ------------------------------------------------------------
# CONFIGURACIÓN INICIAL
# ------------------------------------------------------------
st.set_page_config(
    page_title="Health Assistant",
    layout="wide",
    page_icon="⚕️"
)

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)

# Cargar enfermedades base
with SessionLocal() as db:
    seed_default_diseases(db)

# ------------------------------------------------------------
# CARGAR MODELOS DE ML
# ------------------------------------------------------------
working_dir = os.path.dirname(os.path.abspath(__file__))
diabetes_model = pickle.load(
    open(os.path.join(working_dir, "saved_models", "diabetes_model.sav"), "rb")
)
heart_disease_model = pickle.load(
    open(os.path.join(working_dir, "saved_models", "heart_disease_model.sav"), "rb")
)
parkinsons_model = pickle.load(
    open(os.path.join(working_dir, "saved_models", "parkinsons_model.sav"), "rb")
)

# ------------------------------------------------------------
# SIDEBAR DE NAVEGACIÓN
# ------------------------------------------------------------
with st.sidebar:
    st.markdown(
        f"<h2 style='text-align: center;'><img src='{get_flag('uk')}' width='30' height='20'> 🌐 "
        f"<img src='{get_flag('co')}' width='30' height='20'></h2>",
        unsafe_allow_html=True
    )

    col_toggle = st.columns([1, 1, 1])
    with col_toggle[1]:
        language = st.toggle("", value=True)
    selected_language = "es" if language else "en"
    t = translations[selected_language]

    st.write("")

    selected = option_menu(
        t["MultipleDPS"],
        [
            t["diabetes_prediction"],
            t["heart_disease_prediction"],
            t["parkinsons_prediction"],
            t["history"],  # NUEVO: opción de historial
        ],
        menu_icon="hospital-fill",
        icons=["activity", "heart", "person", "clock-history"],
        default_index=0
    )

# ------------------------------------------------------------
# FORMULARIO DE PACIENTE (REGISTRO EN BD)
# ------------------------------------------------------------
st.subheader("Datos básicos del paciente")
st.caption(
    "Estos datos se usan para registrar el resultado en la base de datos. "
    "No afectan la predicción del modelo."
)

col_u1, col_u2, col_u3 = st.columns(3)
with col_u1:
    user_name = st.text_input(
        "Nombre del paciente",
        value="Paciente Demo",
        help="Nombre o alias que permita identificar al paciente en los registros."
    )
with col_u2:
    user_email = st.text_input(
        "Correo (opcional)",
        help="Correo electrónico para asociar el resultado a un contacto."
    )
with col_u3:
    user_phone = st.text_input(
        "Teléfono (opcional)",
        help="Número de contacto del paciente (no obligatorio)."
    )

col_u4, col_u5 = st.columns(2)
with col_u4:
    user_age = st.number_input(
        "Edad",
        min_value=0,
        max_value=120,
        value=30,
        help="Edad del paciente en años."
    )
with col_u5:
    user_gender = st.selectbox(
        "Género",
        options=["M", "F", "O"],
        help="Género registrado en la historia clínica (M: masculino, F: femenino, O: otro)."
    )

# ------------------------------------------------------------
# FUNCIÓN AUXILIAR PARA GUARDAR RESULTADOS
# ------------------------------------------------------------
def save_diagnosis(disease_code: str, prediction_result, message: str):
    """Guarda un diagnóstico en la base de datos."""
    db = SessionLocal()
    try:
        user = get_or_create_user(
            db,
            name=user_name,
            email=user_email or None,
            age=int(user_age) if user_age is not None else None,
            gender=user_gender,
            phone_number=user_phone or None,
        )

        if hasattr(prediction_result["model"], "predict_proba"):
            probas = prediction_result["model"].predict_proba(
                [prediction_result["input"]]
            )[0]
            positive_proba = float(probas[1])
        else:
            positive_proba = 1.0 if prediction_result["value"] == 1 else 0.0

        create_diagnosis_with_single_candidate(
            db=db,
            user_id=user.id,
            disease_code=disease_code,
            probability=positive_proba,
            final_description=message,
        )

        db.commit()
        st.success("✅ Diagnóstico guardado correctamente en la base de datos.")
    except Exception as e:
        db.rollback()
        st.error(f"❌ Error al guardar el diagnóstico: {e}")
    finally:
        db.close()

# ------------------------------------------------------------
# CONFIGURACIÓN DE CAMPOS Y VALORES POR DEFECTO
# ------------------------------------------------------------

# Diabetes: orden estándar Pima
DIABETES_FEATURE_ORDER = [
    "Pregnancies",
    "Glucose",
    "BloodPressure",
    "SkinThickness",
    "Insulin",
    "BMI",
    "DiabetesPedigreeFunction",
    "Age",
]

DIABETES_DEFAULTS = {
    "Pregnancies": 0.0,
    "SkinThickness": 20.0,
    "Insulin": 80.0,
    "DiabetesPedigreeFunction": 0.5,
}

# Heart disease: orden estándar UCI
HEART_FEATURE_ORDER = [
    "age",
    "sex",
    "cp",
    "trestbps",
    "chol",
    "fbs",
    "restecg",
    "thalach",
    "exang",
    "oldpeak",
    "slope",
    "ca",
    "thal",
]

HEART_DEFAULTS = {
    "fbs": 0.0,
    "restecg": 0.0,
    "slope": 1.0,
    "thal": 2.0,
}

# Parkinson: 22 características originales
PARK_FEATURE_ORDER = [
    "fo", "fhi", "flo", "jitter_percent", "jitter_abs",
    "RAP", "PPQ", "DDP", "shimmer", "shimmer_dB",
    "APQ3", "APQ5", "APQ", "DDA", "NHR", "HNR",
    "RPDE", "DFA", "spread1", "spread2", "D2", "PPE",
]

PARK_DEFAULTS = {
    "flo": 100.0,
    "jitter_abs": 0.0001,
    "RAP": 0.003,
    "PPQ": 0.003,
    "DDP": 0.01,
    "APQ3": 0.015,
    "APQ5": 0.02,
    "APQ": 0.025,
    "DDA": 0.04,
    "RPDE": 0.5,
    "DFA": 0.75,
    "spread1": -5.0,
    "spread2": 0.5,
    "D2": 2.0,
}

# ------------------------------------------------------------
# BLOQUES DE PREDICCIÓN
# ------------------------------------------------------------

# ========== DIABETES ==========
if selected == t["diabetes_prediction"]:
    st.title(t["title_diabetes"])
    st.markdown(
        "Ingresa algunos parámetros metabólicos clave. Otros valores se "
        "completan automáticamente con parámetros clínicos promedio para "
        "simplificar el formulario."
    )

    with st.form("diabetes_form"):
        col1, col2 = st.columns(2)
        with col1:
            pregnancies = st.number_input(
                t["pregnancies"],
                min_value=0,
                max_value=20,
                value=0,
                help="Número de embarazos que ha tenido la persona (0 si no aplica).",
            )
        with col2:
            glucose = st.number_input(
                t["glucose_level"],
                min_value=0,
                max_value=300,
                value=110,
                help="Nivel de glucosa en sangre en ayunas (mg/dl).",
            )

        col3, col4 = st.columns(2)
        with col3:
            blood_pressure = st.number_input(
                t["blood_pressure"],
                min_value=0,
                max_value=200,
                value=80,
                help="Presión arterial diastólica (mm Hg).",
            )
        with col4:
            bmi = st.number_input(
                t["bmi"],
                min_value=10.0,
                max_value=60.0,
                value=25.0,
                step=0.1,
                help="Índice de masa corporal (kg/m²).",
            )

        col5, col6 = st.columns(2)
        with col5:
            dpf = st.number_input(
                t["diabetes_pedigree_function"],
                min_value=0.0,
                max_value=3.0,
                value=0.5,
                step=0.01,
                help="Indicador de carga hereditaria de diabetes en la familia.",
            )
        with col6:
            age = st.number_input(
                t["age"],
                min_value=18,
                max_value=100,
                value=40,
                help="Edad del paciente en años.",
            )

        submit_diab = st.form_submit_button(t["button_diabetes"])

    if submit_diab:
        features = {
            "Pregnancies": float(pregnancies),
            "Glucose": float(glucose),
            "BloodPressure": float(blood_pressure),
            "SkinThickness": DIABETES_DEFAULTS["SkinThickness"],
            "Insulin": DIABETES_DEFAULTS["Insulin"],
            "BMI": float(bmi),
            "DiabetesPedigreeFunction": float(dpf),
            "Age": float(age),
        }

        user_input = [features[f] for f in DIABETES_FEATURE_ORDER]
        diab_prediction = diabetes_model.predict([user_input])

        if diab_prediction[0] == 1:
            diab_diagnosis = t["positive_diabetes"]
        else:
            diab_diagnosis = t["negative_diabetes"]

        st.markdown("---")
        st.success(diab_diagnosis)
        st.caption(
            "⚠️ Este resultado es orientativo y no sustituye la valoración de un profesional de la salud."
        )

        save_diagnosis(
            "DIAB",
            {"model": diabetes_model, "input": user_input, "value": diab_prediction[0]},
            diab_diagnosis,
        )

# ========== HEART DISEASE ==========
elif selected == t["heart_disease_prediction"]:
    st.title(t["title_heart"])
    st.markdown(
        "Completa algunos parámetros cardiovasculares básicos. El resto de "
        "variables se completan automáticamente con valores estándar."
    )

    with st.form("heart_form"):
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input(
                t["age"],
                min_value=18,
                max_value=100,
                value=50,
                help="Edad del paciente en años.",
            )
        with col2:
            if selected_language == "es":
                sex_label = "Sexo biológico"
                sex_options = ["Masculino", "Femenino"]
            else:
                sex_label = "Biological sex"
                sex_options = ["Male", "Female"]

            sex_str = st.selectbox(
                sex_label,
                options=sex_options,
                help="Sexo biológico registrado. El modelo lo codifica como 1/0.",
            )
            sex = 1.0 if sex_str in ["Masculino", "Male"] else 0.0

        col3, col4 = st.columns(2)
        with col3:
            if selected_language == "es":
                cp_label = "Tipo de dolor en el pecho"
                cp_help = (
                    "0: típico anginoso, 1: atípico anginoso, "
                    "2: no anginoso, 3: asintomático."
                )
                cp_options = [
                    "0 - Típico anginoso",
                    "1 - Atípico anginoso",
                    "2 - No anginoso",
                    "3 - Asintomático",
                ]
            else:
                cp_label = "Chest pain type"
                cp_help = (
                    "0: typical angina, 1: atypical angina, "
                    "2: non-anginal, 3: asymptomatic."
                )
                cp_options = [
                    "0 - Typical angina",
                    "1 - Atypical angina",
                    "2 - Non-anginal",
                    "3 - Asymptomatic",
                ]

            cp_str = st.selectbox(cp_label, options=cp_options, help=cp_help)
            cp = float(cp_str.split(" - ")[0])

        with col4:
            trestbps = st.number_input(
                t["trestbps"],
                min_value=80,
                max_value=220,
                value=130,
                help="Presión arterial en reposo (mm Hg).",
            )

        col5, col6 = st.columns(2)
        with col5:
            chol = st.number_input(
                t["chol"],
                min_value=100,
                max_value=600,
                value=220,
                help="Colesterol sérico total (mg/dl) en ayunas.",
            )
        with col6:
            thalach = st.number_input(
                t["thalach"],
                min_value=60,
                max_value=220,
                value=150,
                help="Frecuencia cardíaca máxima alcanzada durante esfuerzo.",
            )

        col7, col8 = st.columns(2)
        with col7:
            if selected_language == "es":
                exang_label = "Angina inducida por ejercicio"
                exang_options = ["No", "Sí"]
            else:
                exang_label = "Exercise induced angina"
                exang_options = ["No", "Yes"]

            exang_str = st.selectbox(
                exang_label,
                options=exang_options,
                help="Dolor torácico que aparece o empeora con el ejercicio.",
            )
            exang = 1.0 if exang_str in ["Sí", "Yes"] else 0.0

        with col8:
            oldpeak = st.number_input(
                t["oldpeak"],
                min_value=0.0,
                max_value=10.0,
                value=1.0,
                step=0.1,
                help="Depresión del segmento ST inducida por el ejercicio (en relación con reposo).",
            )

        ca = st.number_input(
            t["ca"],
            min_value=0,
            max_value=4,
            value=0,
            help="Número de vasos principales coloreados por fluoroscopia (0–3 habitualmente).",
        )

        submit_heart = st.form_submit_button(t["button_heart"])

    if submit_heart:
        features = {
            "age": float(age),
            "sex": float(sex),
            "cp": float(cp),
            "trestbps": float(trestbps),
            "chol": float(chol),
            "fbs": HEART_DEFAULTS["fbs"],
            "restecg": HEART_DEFAULTS["restecg"],
            "thalach": float(thalach),
            "exang": float(exang),
            "oldpeak": float(oldpeak),
            "slope": HEART_DEFAULTS["slope"],
            "ca": float(ca),
            "thal": HEART_DEFAULTS["thal"],
        }

        user_input = [features[f] for f in HEART_FEATURE_ORDER]
        heart_prediction = heart_disease_model.predict([user_input])

        if heart_prediction[0] == 1:
            heart_diagnosis = t["positive_heart"]
        else:
            heart_diagnosis = t["negative_heart"]

        st.markdown("---")
        st.success(heart_diagnosis)
        st.caption(
            "⚠️ Este resultado es orientativo y no reemplaza el diagnóstico médico profesional."
        )

        save_diagnosis(
            "HEART",
            {"model": heart_disease_model, "input": user_input, "value": heart_prediction[0]},
            heart_diagnosis,
        )

# ========== PARKINSON ==========
elif selected == t["parkinsons_prediction"]:
    st.title(t["title_parkinson"])
    st.markdown(
        "Se utilizan algunos parámetros de la voz para estimar el riesgo. "
        "Otras variables del modelo se completan con valores promedio."
    )

    with st.form("parkinson_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            fo = st.number_input(
                t["fo"],
                min_value=50.0,
                max_value=300.0,
                value=150.0,
                step=1.0,
                help="Frecuencia fundamental media de la voz (Hz).",
            )
        with col2:
            fhi = st.number_input(
                t["fhi"],
                min_value=50.0,
                max_value=400.0,
                value=200.0,
                step=1.0,
                help="Frecuencia máxima de la voz (Hz).",
            )
        with col3:
            jitter_percent = st.number_input(
                t["jitter_percent"],
                min_value=0.0,
                max_value=1.0,
                value=0.01,
                step=0.001,
                help="Variación relativa del tono de un ciclo a otro (%).",
            )

        col4, col5, col6 = st.columns(3)
        with col4:
            shimmer = st.number_input(
                t["shimmer"],
                min_value=0.0,
                max_value=1.0,
                value=0.03,
                step=0.001,
                help="Variación relativa de la amplitud de un ciclo a otro.",
            )
        with col5:
            nhr = st.number_input(
                t["NHR"],
                min_value=0.0,
                max_value=1.0,
                value=0.03,
                step=0.001,
                help="Relación ruido/armónicos de la señal de voz.",
            )
        with col6:
            hnr = st.number_input(
                t["HNR"],
                min_value=0.0,
                max_value=50.0,
                value=20.0,
                step=0.1,
                help="Relación armónicos/ruido (dB). Valores menores indican más ruido.",
            )

        col7, col8 = st.columns(2)
        with col7:
            rpde = st.number_input(
                t["RPDE"],
                min_value=0.0,
                max_value=1.0,
                value=0.5,
                step=0.01,
                help="Medida de complejidad/no linealidad en la señal de voz.",
            )
        with col8:
            ppe = st.number_input(
                t["PPE"],
                min_value=0.0,
                max_value=1.0,
                value=0.3,
                step=0.01,
                help="Entropía del periodo del tono. Mayor valor indica mayor irregularidad.",
            )

        submit_park = st.form_submit_button(t["button_parkinson"])

    if submit_park:
        features = {
            "fo": float(fo),
            "fhi": float(fhi),
            "flo": PARK_DEFAULTS["flo"],
            "jitter_percent": float(jitter_percent),
            "jitter_abs": PARK_DEFAULTS["jitter_abs"],
            "RAP": PARK_DEFAULTS["RAP"],
            "PPQ": PARK_DEFAULTS["PPQ"],
            "DDP": PARK_DEFAULTS["DDP"],
            "shimmer": float(shimmer),
            "shimmer_dB": 0.02,
            "APQ3": PARK_DEFAULTS["APQ3"],
            "APQ5": PARK_DEFAULTS["APQ5"],
            "APQ": PARK_DEFAULTS["APQ"],
            "DDA": PARK_DEFAULTS["DDA"],
            "NHR": float(nhr),
            "HNR": float(hnr),
            "RPDE": float(rpde),
            "DFA": PARK_DEFAULTS["DFA"],
            "spread1": PARK_DEFAULTS["spread1"],
            "spread2": PARK_DEFAULTS["spread2"],
            "D2": PARK_DEFAULTS["D2"],
            "PPE": float(ppe),
        }

        user_input = [features[f] for f in PARK_FEATURE_ORDER]
        parkinsons_prediction = parkinsons_model.predict([user_input])

        if parkinsons_prediction[0] == 1:
            parkinsons_diagnosis = t["positive_parkinson"]
        else:
            parkinsons_diagnosis = t["negative_parkinson"]

        st.markdown("---")
        st.success(parkinsons_diagnosis)
        st.caption(
            "⚠️ Este resultado es orientativo y no reemplaza la valoración de un neurólogo."
        )

        save_diagnosis(
            "PARK",
            {"model": parkinsons_model, "input": user_input, "value": parkinsons_prediction[0]},
            parkinsons_diagnosis,
        )

# ========== HISTORIAL ==========
elif selected == t["history"]:
    st.title(t["history"])
    st.markdown(t["history_intro"])

    with st.form("history_form"):
        filter_email = st.text_input(t["history_filter_email"])
        limit = st.slider(
            "Número máximo de registros a mostrar",
            min_value=10,
            max_value=200,
            value=50,
            step=10,
            help="Controla cuántos diagnósticos se muestran en la tabla."
        )
        submit_history = st.form_submit_button(t["history_show_button"])

    if submit_history:
        with SessionLocal() as db:
            if filter_email.strip():
                rows = get_diagnoses_by_user_email(
                    db, filter_email.strip(), limit=limit
                )
            else:
                rows = get_recent_diagnoses(db, limit=limit)

        if not rows:
            st.info(t["history_empty"])
        else:
            # Construir una lista de diccionarios para mostrar en tabla
            data = []
            for r in rows:
                data.append(
                    {
                        "ID diagnóstico": r.id,
                        "Fecha / hora": r.generated_at,
                        "Paciente": r.user_name,
                        "Correo": r.user_email,
                        "Enfermedad": r.disease_name,
                        "Código": r.disease_code,
                        "Probabilidad": float(r.probability),
                        "Estado": r.status,
                    }
                )

            st.dataframe(data, use_container_width=True)

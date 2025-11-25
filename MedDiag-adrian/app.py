import os
import pickle
import streamlit as st
from streamlit_option_menu import option_menu
from translations import translations
from flags import get_flag

# --- Nuevas importaciones para persistencia ---
from database import engine, SessionLocal
from models import Base
from crud import (
    get_or_create_user,
    seed_default_diseases,
    create_diagnosis_with_single_candidate
)

# ------------------------------------------------------------
# CONFIGURACIÓN INICIAL
# ------------------------------------------------------------
st.set_page_config(page_title="Health Assistant",
                   layout="wide",
                   page_icon="⚕️")

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)

# Cargar enfermedades base
with SessionLocal() as db:
    seed_default_diseases(db)

# ------------------------------------------------------------
# CARGAR MODELOS DE ML
# ------------------------------------------------------------
working_dir = os.path.dirname(os.path.abspath(__file__))
diabetes_model = pickle.load(open(f'{working_dir}/saved_models/diabetes_model.sav', 'rb'))
heart_disease_model = pickle.load(open(f'{working_dir}/saved_models/heart_disease_model.sav', 'rb'))
parkinsons_model = pickle.load(open(f'{working_dir}/saved_models/parkinsons_model.sav', 'rb'))

# ------------------------------------------------------------
# SIDEBAR DE NAVEGACIÓN
# ------------------------------------------------------------
with st.sidebar:
    st.markdown(
        f"<h2 style='text-align: center;'><img src='{get_flag('uk')}' width='30' height='20'> 🌐 <img src='{get_flag('co')}' width='30' height='20'></h2>",
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
        [t["diabetes_prediction"],
         t['heart_disease_prediction'],
         t['parkinsons_prediction']],
        menu_icon='hospital-fill',
        icons=['activity', 'heart', 'person'],
        default_index=0
    )

# ------------------------------------------------------------
# FORMULARIO DE PACIENTE
# ------------------------------------------------------------
st.subheader("Datos básicos del paciente (para registrar el diagnóstico)")

col_u1, col_u2, col_u3 = st.columns(3)
with col_u1:
    user_name = st.text_input("Nombre del paciente", value="Paciente Demo")
with col_u2:
    user_email = st.text_input("Correo (opcional)")
with col_u3:
    user_phone = st.text_input("Teléfono (opcional)")

col_u4, col_u5 = st.columns(2)
with col_u4:
    user_age = st.number_input("Edad", min_value=0, max_value=120, value=30)
with col_u5:
    user_gender = st.selectbox("Género", options=["M", "F", "O"], index=0)

# ------------------------------------------------------------
# FUNCIÓN AUXILIAR PARA GUARDAR RESULTADOS
# ------------------------------------------------------------
def save_diagnosis(disease_code: str, prediction_result, message: str):
    """Guarda un diagnóstico en la base de datos"""
    db = SessionLocal()
    try:
        user = get_or_create_user(
            db,
            name=user_name,
            email=user_email or None,
            age=int(user_age) if user_age else None,
            gender=user_gender,
            phone_number=user_phone or None
        )

        # Obtener probabilidad si el modelo lo permite
        if hasattr(prediction_result["model"], "predict_proba"):
            probas = prediction_result["model"].predict_proba([prediction_result["input"]])[0]
            positive_proba = float(probas[1])
        else:
            positive_proba = 1.0 if prediction_result["value"] == 1 else 0.0

        create_diagnosis_with_single_candidate(
            db=db,
            user_id=user.id,
            disease_code=disease_code,
            probability=positive_proba,
            final_description=message
        )

        db.commit()
        st.success("✅ Diagnóstico guardado correctamente en la base de datos.")
    except Exception as e:
        db.rollback()
        st.error(f"❌ Error al guardar el diagnóstico: {e}")
    finally:
        db.close()

# ------------------------------------------------------------
# SECCIONES DE PREDICCIÓN
# ------------------------------------------------------------

# ========== DIABETES ==========
if selected == t["diabetes_prediction"]:
    st.title(t["title_diabetes"])

    col1, col2, col3 = st.columns(3)
    with col1:
        Pregnancies = st.text_input(t["pregnancies"])
    with col2:
        Glucose = st.text_input(t["glucose_level"])
    with col3:
        BloodPressure = st.text_input(t["blood_pressure"])
    with col1:
        SkinThickness = st.text_input(t["skin_thickness"])
    with col2:
        Insulin = st.text_input(t["insulin_level"])
    with col3:
        BMI = st.text_input(t["bmi"])
    with col1:
        DiabetesPedigreeFunction = st.text_input(t["diabetes_pedigree_function"])
    with col2:
        Age = st.text_input(t["age"])

    diab_diagnosis = ''

    if st.button(t['button_diabetes']):
        user_input = [Pregnancies, Glucose, BloodPressure, SkinThickness, Insulin,
                      BMI, DiabetesPedigreeFunction, Age]
        user_input = [float(x) for x in user_input]
        diab_prediction = diabetes_model.predict([user_input])

        if diab_prediction[0] == 1:
            diab_diagnosis = t['positive_diabetes']
        else:
            diab_diagnosis = t['negative_diabetes']

        st.success(diab_diagnosis)
        save_diagnosis("DIAB", {"model": diabetes_model, "input": user_input, "value": diab_prediction[0]}, diab_diagnosis)

# ========== HEART DISEASE ==========
if selected == t['heart_disease_prediction']:
    st.title(t['title_heart'])

    col1, col2, col3 = st.columns(3)
    with col1:
        age = st.text_input(t['age'])
    with col2:
        sex = st.text_input(t['sex'])
    with col3:
        cp = st.text_input(t['cp'])
    with col1:
        trestbps = st.text_input(t['trestbps'])
    with col2:
        chol = st.text_input(t['chol'])
    with col3:
        fbs = st.text_input(t['fbs'])
    with col1:
        restecg = st.text_input(t['restecg'])
    with col2:
        thalach = st.text_input(t['thalach'])
    with col3:
        exang = st.text_input(t['exang'])
    with col1:
        oldpeak = st.text_input(t['oldpeak'])
    with col2:
        slope = st.text_input(t['slope'])
    with col3:
        ca = st.text_input(t['ca'])
    with col1:
        thal = st.text_input(t['thal'])

    heart_diagnosis = ''

    if st.button(t['button_heart']):
        user_input = [age, sex, cp, trestbps, chol, fbs, restecg, thalach,
                      exang, oldpeak, slope, ca, thal]
        user_input = [float(x) for x in user_input]
        heart_prediction = heart_disease_model.predict([user_input])

        if heart_prediction[0] == 1:
            heart_diagnosis = t['positive_heart']
        else:
            heart_diagnosis = t['negative_heart']

        st.success(heart_diagnosis)
        save_diagnosis("HEART", {"model": heart_disease_model, "input": user_input, "value": heart_prediction[0]}, heart_diagnosis)

# ========== PARKINSON ==========
if selected == t['parkinsons_prediction']:
    st.title(t['title_parkinson'])

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: fo = st.text_input(t['fo'])
    with col2: fhi = st.text_input(t['fhi'])
    with col3: flo = st.text_input(t['flo'])
    with col4: jitter_percent = st.text_input(t['jitter_percent'])
    with col5: jitter_abs = st.text_input(t['jitter_abs'])
    with col1: RAP = st.text_input(t['RAP'])
    with col2: PPQ = st.text_input(t['PPQ'])
    with col3: DDP = st.text_input(t['DDP'])
    with col4: shimmer = st.text_input(t['shimmer'])
    with col5: shimmer_dB = st.text_input(t['shimmer_dB'])
    with col1: APQ3 = st.text_input(t['APQ3'])
    with col2: APQ5 = st.text_input(t['APQ5'])
    with col3: APQ = st.text_input(t['APQ'])
    with col4: DDA = st.text_input(t['DDA'])
    with col5: NHR = st.text_input(t['NHR'])
    with col1: HNR = st.text_input(t['HNR'])
    with col2: RPDE = st.text_input(t['RPDE'])
    with col3: DFA = st.text_input(t['DFA'])
    with col4: spread1 = st.text_input(t['spread1'])
    with col5: spread2 = st.text_input(t['spread2'])
    with col1: D2 = st.text_input(t['D2'])
    with col2: PPE = st.text_input(t['PPE'])

    parkinsons_diagnosis = ''

    if st.button(t["button_parkinson"]):
        user_input = [fo, fhi, flo, jitter_percent, jitter_abs,
                      RAP, PPQ, DDP, shimmer, shimmer_dB, APQ3, APQ5,
                      APQ, DDA, NHR, HNR, RPDE, DFA, spread1, spread2, D2, PPE]
        user_input = [float(x) for x in user_input]
        parkinsons_prediction = parkinsons_model.predict([user_input])

        if parkinsons_prediction[0] == 1:
            parkinsons_diagnosis = t['positive_parkinson']
        else:
            parkinsons_diagnosis = t['negative_parkinson']

        st.success(parkinsons_diagnosis)
        save_diagnosis("PARK", {"model": parkinsons_model, "input": user_input, "value": parkinsons_prediction[0]}, parkinsons_diagnosis)

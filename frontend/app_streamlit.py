import os
import sys
import requests
import streamlit as st
from streamlit_option_menu import option_menu

# Make root imports (translations, flags) available when running from /frontend
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from translations import translations  # noqa: E402
from flags import get_flag  # noqa: E402

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# ------------------------------------------------------------
# CONFIGURACION INICIAL
# ------------------------------------------------------------
st.set_page_config(page_title="Health Assistant", layout="wide", page_icon="MD")

# ------------------------------------------------------------
# SIDEBAR DE NAVEGACION
# ------------------------------------------------------------
with st.sidebar:
    st.markdown(
        f"<h2 style='text-align: center;'>MedDiag <img src='{get_flag('uk')}' width='30' height='20'> <img src='{get_flag('co')}' width='30' height='20'></h2>",
        unsafe_allow_html=True,
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
            t["welcome"],
            t["diabetes_prediction"],
            t["heart_disease_prediction"],
            t["parkinsons_prediction"],
            t["history"],
        ],
        menu_icon="hospital-fill",
        icons=["house", "activity", "heart", "person", "clock-history"],
        default_index=0,
        styles={
            "container": {"padding": "5px", "background-color": "#f4fbf7"},
            "icon": {"color": "#0f9b64", "font-size": "20px"},
            "nav-link": {
                "font-size": "15px",
                "color": "#0f2f1c",
                "padding": "8px",
                "border-radius": "10px",
                "text-align": "left",
                "--hover-color": "#e4f5eb",
            },
            "nav-link-selected": {
                "background-color": "#c9f0d9",
                "color": "#0f7f4a",
                "font-weight": "700",
            },
        },
    )


# ------------------------------------------------------------
# UTILIDADES
# ------------------------------------------------------------
def api_post(path: str, payload: dict):
    try:
        resp = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json(), None
    except requests.RequestException as exc:
        return None, str(exc)


def api_get(path: str, params: dict | None = None):
    try:
        resp = requests.get(f"{API_BASE_URL}{path}", params=params or {}, timeout=15)
        resp.raise_for_status()
        return resp.json(), None
    except requests.RequestException as exc:
        return None, str(exc)


def patient_payload(name, email, phone, gender):
    return {
        "name": name,
        "email": email or None,
        "phone_number": phone or None,
        "gender": gender,
    }


# ------------------------------------------------------------
# VISTA DE BIENVENIDA
# ------------------------------------------------------------
if selected == t["welcome"]:
    st.markdown(
        """
        <style>
        .welcome-hero{
            padding:24px 28px;
            border-radius:16px;
            background: linear-gradient(135deg, #0f9b64 0%, #35c48b 45%, #e8fff5 100%);
            color:#0a2f1a;
            margin-bottom:18px;
        }
        .welcome-card{
            padding:18px 16px;
            border:1px solid #cfe9dd;
            border-radius:14px;
            background: #f6fffa;
            height:100%;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="welcome-hero">
            <h1 style="margin:0;">{t["welcome_title"]}</h1>
            <p style="margin:8px 0 0; font-size:1.05rem;">{t["welcome_subtitle"]}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns([1.5, 1])
    with col_a:
        st.markdown(f"### {t['welcome_steps_title']}")
        st.markdown(f"- {t['welcome_step_1']}")
        st.markdown(f"- {t['welcome_step_2']}")
        st.markdown(f"- {t['welcome_step_3']}")
        st.info(t["welcome_next_steps"])

    with col_b:
        st.markdown(f"### {t['welcome_diseases_title']}")
        st.markdown(
            f"""<div class='welcome-card'><strong>Diabetes</strong><br>{t['welcome_disease_diabetes']}</div>""",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""<div class='welcome-card'><strong>Cardiovascular</strong><br>{t['welcome_disease_heart']}</div>""",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""<div class='welcome-card'><strong>Parkinson</strong><br>{t['welcome_disease_parkinson']}</div>""",
            unsafe_allow_html=True,
        )

    st.stop()

# ------------------------------------------------------------
# FORMULARIO DE PACIENTE (SE COMPARTE)
# ------------------------------------------------------------
st.subheader(t["patient_data_title"])
st.caption(t["patient_data_caption"])

col_u1, col_u2, col_u3 = st.columns(3)
with col_u1:
    user_name = st.text_input(t["patient_name"], value="Paciente Demo")
with col_u2:
    user_email = st.text_input(t["patient_email"])
with col_u3:
    user_phone = st.text_input(t["patient_phone"])

col_u4, col_u5 = st.columns(2)
with col_u4:
    user_gender = st.selectbox(t["patient_gender"], options=["M", "F", "O"])
with col_u5:
    st.write("")  # placeholder para mantener la grilla equilibrada

# Defaults used to fill missing optional variables
DIABETES_DEFAULTS = {
    "SkinThickness": 20.0,
    "Insulin": 80.0,
    "DiabetesPedigreeFunction": 0.5,
}

HEART_DEFAULTS = {
    "fbs": 0.0,
    "restecg": 0.0,
    "slope": 1.0,
    "thal": 2.0,
}

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
# BLOQUES DE PREDICCION
# ------------------------------------------------------------

if selected == t["diabetes_prediction"]:
    st.title(t["title_diabetes"])

    with st.form("diabetes_form"):
        col1, col2 = st.columns(2)
        with col1:
            pregnancies = st.number_input(
                t["pregnancies"],
                min_value=0,
                max_value=20,
                value=0,
                help=t["help_pregnancies"],
            )
        with col2:
            glucose = st.number_input(
                t["glucose_level"],
                min_value=0,
                max_value=300,
                value=110,
                help=t["help_glucose"],
            )

        col3, col4 = st.columns(2)
        with col3:
            blood_pressure = st.number_input(
                t["blood_pressure"],
                min_value=0,
                max_value=200,
                value=80,
                help=t["help_blood_pressure"],
            )
        with col4:
            bmi = st.number_input(
                t["bmi"],
                min_value=10.0,
                max_value=60.0,
                value=25.0,
                step=0.1,
                help=t["help_bmi"],
            )

        col5, col6 = st.columns(2)
        with col5:
            dpf = st.number_input(
                t["diabetes_pedigree_function"],
                min_value=0.0,
                max_value=3.0,
                value=0.5,
                step=0.01,
                help=t["help_dpf"],
            )
        with col6:
            age = st.number_input(
                t["age"],
                min_value=18,
                max_value=100,
                value=40,
                help=t["help_age"],
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
        payload = {"patient": patient_payload(user_name, user_email, user_phone, user_gender), "features": features}
        data, err = api_post("/predict/diabetes", payload)
        if err:
            st.error(f"Error al llamar la API: {err}")
        else:
            # AHORA VERIFICAMOS EL RESULTADO (data["prediction"] es 1 o 0)
            if data["prediction"] == 1:
               # Caso POSITIVO (RIESGO)
              st.error(data["message"]) # Mensaje corto del API
              st.markdown(t['positive_diabetes_reco']) # <-- RECOMENDACIÓN DETALLADA
            else:
             # Caso NEGATIVO (NO RIESGO)
                st.success(data["message"]) # Mensaje corto del API
                st.markdown(t['negative_diabetes_reco']) # <-- RECOMENDACIÓN DETALLADA
            st.caption("Este resultado es orientativo y no sustituye la valoracion de un profesional de la salud.")

elif selected == t["heart_disease_prediction"]:
    st.title(t["title_heart"])

    with st.form("heart_form"):
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input(
                t["age"],
                min_value=18,
                max_value=100,
                value=50,
                help=t["help_age"],
            )
        with col2:
            sex_str = st.selectbox(
                t["sex"],
                options=[t["sex_option_male"], t["sex_option_female"]],
                help=t["help_sex"],
            )
            sex = 1.0 if sex_str == t["sex_option_male"] else 0.0

        col3, col4 = st.columns(2)
        with col3:
            cp_str = st.selectbox(
                t["cp"],
                options=[
                    t["cp_option_0"],
                    t["cp_option_1"],
                    t["cp_option_2"],
                    t["cp_option_3"],
                ],
                help=t["help_cp"],
            )
            cp = float(cp_str.split(" - ")[0])
        with col4:
            trestbps = st.number_input(
                t["trestbps"],
                min_value=80,
                max_value=220,
                value=130,
                help=t["help_trestbps"],
            )

        col5, col6 = st.columns(2)
        with col5:
            chol = st.number_input(
                t["chol"],
                min_value=100,
                max_value=600,
                value=220,
                help=t["help_chol"],
            )
        with col6:
            thalach = st.number_input(
                t["thalach"],
                min_value=60,
                max_value=220,
                value=150,
                help=t["help_thalach"],
            )

        col7, col8 = st.columns(2)
        with col7:
            exang_str = st.selectbox(
                t["exang"],
                options=[t["exang_option_no"], t["exang_option_yes"]],
                help=t["help_exang"],
            )
            exang = 1.0 if exang_str == t["exang_option_yes"] else 0.0
        with col8:
            oldpeak = st.number_input(
                t["oldpeak"],
                min_value=0.0,
                max_value=10.0,
                value=1.0,
                step=0.1,
                help=t["help_oldpeak"],
            )

        ca = st.number_input(
            t["ca"],
            min_value=0,
            max_value=4,
            value=0,
            help=t["help_ca"],
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
        payload = {"patient": patient_payload(user_name, user_email, user_phone, user_gender), "features": features}
        data, err = api_post("/predict/heart", payload)
        if err:
            st.error(f"Error al llamar la API: {err}")
        else:
            # AHORA VERIFICAMOS EL RESULTADO (data["prediction"] es 1 o 0)
            if data["prediction"] == 1:
                # Caso POSITIVO (RIESGO)
                st.error(data["message"]) # Mensaje corto del API
                st.markdown(t['positive_heart_reco']) # <-- RECOMENDACIÓN DETALLADA
            else:
                # Caso NEGATIVO (NO RIESGO)
                st.success(data["message"]) # Mensaje corto del API
                st.markdown(t['negative_heart_reco']) # <-- RECOMENDACIÓN DETALLADA

            st.caption("Este resultado es orientativo y no reemplaza el diagnostico medico profesional.")

elif selected == t["parkinsons_prediction"]:
    st.title(t["title_parkinson"])

    with st.form("parkinson_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            fo = st.number_input(
                t["fo"],
                min_value=50.0,
                max_value=300.0,
                value=150.0,
                step=1.0,
                help=t["help_fo"],
            )
        with col2:
            fhi = st.number_input(
                t["fhi"],
                min_value=50.0,
                max_value=400.0,
                value=200.0,
                step=1.0,
                help=t["help_fhi"],
            )
        with col3:
            jitter_percent = st.number_input(
                t["jitter_percent"],
                min_value=0.0,
                max_value=1.0,
                value=0.01,
                step=0.001,
                help=t["help_jitter_percent"],
            )

        col4, col5, col6 = st.columns(3)
        with col4:
            shimmer = st.number_input(
                t["shimmer"],
                min_value=0.0,
                max_value=1.0,
                value=0.03,
                step=0.001,
                help=t["help_shimmer"],
            )
        with col5:
            nhr = st.number_input(
                t["NHR"],
                min_value=0.0,
                max_value=1.0,
                value=0.03,
                step=0.001,
                help=t["help_nhr"],
            )
        with col6:
            hnr = st.number_input(
                t["HNR"],
                min_value=0.0,
                max_value=50.0,
                value=20.0,
                step=0.1,
                help=t["help_hnr"],
            )

        col7, col8 = st.columns(2)
        with col7:
            rpde = st.number_input(
                t["RPDE"],
                min_value=0.0,
                max_value=1.0,
                value=0.5,
                step=0.01,
                help=t["help_rpde"],
            )
        with col8:
            ppe = st.number_input(
                t["PPE"],
                min_value=0.0,
                max_value=1.0,
                value=0.3,
                step=0.01,
                help=t["help_ppe"],
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
        payload = {"patient": patient_payload(user_name, user_email, user_phone, user_gender), "features": features}
        data, err = api_post("/predict/parkinson", payload)
        if err:
            st.error(f"Error al llamar la API: {err}")
        else:
            # AHORA VERIFICAMOS EL RESULTADO (data["prediction"] es 1 o 0)
            if data["prediction"] == 1:
                # Caso POSITIVO (RIESGO)
                st.error(data["message"]) # Mensaje corto del API
                st.markdown(t['positive_parkinson_reco']) # <-- RECOMENDACIÓN DETALLADA
            else:
                # Caso NEGATIVO (NO RIESGO)
                st.success(data["message"]) # Mensaje corto del API
                st.markdown(t['negative_parkinson_reco']) # <-- RECOMENDACIÓN DETALLADA

            st.caption("Este resultado es orientativo y no reemplaza la valoracion de un neurologo.")

# ------------------------------------------------------------
# HISTORIAL
# ------------------------------------------------------------
elif selected == t["history"]:
    st.title(t["history"])
    st.markdown(t["history_intro"])

    with st.form("history_form"):
        filter_name = st.text_input(t["history_filter_name"])
        filter_email = st.text_input(t["history_filter_email"])
        limit = st.slider(t["history_limit_label"], min_value=10, max_value=200, value=50, step=10)
        submit_history = st.form_submit_button(t["history_show_button"])

    if submit_history:
        params = {"limit": limit}
        if filter_name.strip():
            params["name"] = filter_name.strip()
        if filter_email.strip():
            params["email"] = filter_email.strip()
        data, err = api_get("/diagnoses/history", params=params)
        if err:
            st.error(f"Error al consultar historial: {err}")
        elif not data:
            st.info(t["history_empty"])
        else:
            st.dataframe(data, use_container_width=True)

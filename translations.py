translations = {
    "es": {
        # Navegacion y bienvenida
        "welcome": "Inicio",
        "welcome_title": "MedDiag - Asistente de diagnostico medico IA",
        "welcome_subtitle": "Aplicacion de apoyo para tres patologias: diabetes, enfermedad cardiaca y Parkinson.",
        "welcome_steps_title": "Como funciona",
        "welcome_step_1": "1) Completa los datos basicos del paciente y el formulario de la patologia.",
        "welcome_step_2": "2) El modelo de IA calcula el riesgo y muestra una recomendacion orientativa.",
        "welcome_step_3": "3) Guarda el resultado en la base local para auditarlo en Historial.",
        "welcome_diseases_title": "Modelos activos en esta demo",
        "welcome_disease_diabetes": "Diabetes: modelo con parametros metabolicos (glucosa, IMC, presion).",
        "welcome_disease_heart": "Enfermedad cardiaca: factores clinicos clasicos (colesterol, presion, esfuerzo).",
        "welcome_disease_parkinson": "Parkinson: analisis de voz con indicadores de inestabilidad y ruido.",
        "welcome_next_steps": "Selecciona una prueba en el menu lateral y ejecuta la prediccion.",
        "MultipleDPS": "Sistema de prediccion de multiples enfermedades",
        "diabetes_prediction": "Prediccion de Diabetes",
        "heart_disease_prediction": "Prediccion de Enfermedad Cardiaca",
        "parkinsons_prediction": "Prediccion de Parkinson",
        # Datos del paciente
        "patient_data_title": "Datos basicos del paciente",
        "patient_data_caption": "Se usan para registrar el resultado en la base de datos.",
        "patient_name": "Nombre del paciente",
        "patient_email": "Correo (opcional)",
        "patient_phone": "Telefono (opcional)",
        "patient_age": "Edad",
        "patient_gender": "Genero",
        # Diabetes
        "title_diabetes": "Prediccion de Diabetes con ML",
        "pregnancies": "Numero de embarazos",
        "glucose_level": "Nivel de glucosa",
        "blood_pressure": "Presion arterial",
        "skin_thickness": "Espesor de la piel",
        "insulin_level": "Nivel de insulina",
        "bmi": "Indice de masa corporal",
        "diabetes_pedigree_function": "Funcion de herencia de la diabetes",
        "age": "Edad",
        "button_diabetes": "Resultado del test de diabetes",
        "positive_diabetes": "La persona puede ser diabetica, consulte a su medico.",
        "negative_diabetes": "La persona no es diabetica.",
        "help_pregnancies": "Cantidad de embarazos que ha tenido la persona (0 si no aplica).",
        "help_glucose": "Glucosa en sangre en ayunas (mg/dl).",
        "help_blood_pressure": "Presion arterial diastolica (mm Hg).",
        "help_bmi": "Peso (kg) dividido por talla^2 (m).",
        "help_dpf": "Carga hereditaria de diabetes en la familia (0-3).",
        "help_age": "Edad del paciente en anos.",
        # Corazon
        "title_heart": "Prediccion de enfermedad cardiaca con ML",
        "sex": "Sexo biologico",
        "sex_option_male": "Masculino",
        "sex_option_female": "Femenino",
        "cp": "Tipo de dolor en el pecho",
        "cp_option_0": "0 - Tipico anginoso",
        "cp_option_1": "1 - Atipico anginoso",
        "cp_option_2": "2 - No anginoso",
        "cp_option_3": "3 - Asintomatico",
        "trestbps": "Presion arterial en reposo",
        "chol": "Colesterol serico (mg/dl)",
        "fbs": "Azucar en sangre en ayunas > 120 mg/dl",
        "restecg": "Resultados del electrocardiograma en reposo",
        "thalach": "Frecuencia cardiaca maxima alcanzada",
        "exang": "Angina inducida por ejercicio",
        "exang_option_no": "No",
        "exang_option_yes": "Si",
        "oldpeak": "Depresion del ST inducida por ejercicio",
        "slope": "Pendiente del segmento ST en el pico del ejercicio",
        "ca": "Vasos principales coloreados por fluoroscopia",
        "thal": "thal: 0 = normal; 1 = defecto fijo; 2 = defecto reversible",
        "button_heart": "Resultado del test de enfermedad cardiaca",
        "positive_heart": "La persona puede ser cardiaca, consulte a su medico.",
        "negative_heart": "La persona no es cardiaca.",
        "help_sex": "Sexo biologico registrado. Se codifica 1=M, 0=F.",
        "help_cp": "0: tipico, 1: atipico, 2: no anginoso, 3: asintomatico.",
        "help_trestbps": "Presion arterial en reposo (mm Hg).",
        "help_chol": "Colesterol total en ayunas (mg/dl).",
        "help_thalach": "Frecuencia cardiaca maxima alcanzada en esfuerzo.",
        "help_exang": "Dolor toracico que aparece o empeora con ejercicio.",
        "help_oldpeak": "Caida del segmento ST respecto a reposo.",
        "help_ca": "Numero de vasos principales coloreados (0-3).",
        # Parkinson
        "title_parkinson": "Prediccion de Parkinson con ML",
        "fo": "Frecuencia media (Hz)",
        "fhi": "Frecuencia maxima (Hz)",
        "flo": "Frecuencia minima (Hz)",
        "jitter_percent": "Variacion del tono (%)",
        "jitter_abs": "Variacion del tono (abs)",
        "RAP": "Inestabilidad del tono (RAP)",
        "PPQ": "Perturbacion del tono (PPQ)",
        "DDP": "Diferencia doble del tono (DDP)",
        "shimmer": "Variacion de la amplitud",
        "shimmer_dB": "Variacion de la amplitud (dB)",
        "APQ3": "Perturbacion de amplitud (3 ciclos)",
        "APQ5": "Perturbacion de amplitud (5 ciclos)",
        "APQ": "Perturbacion de amplitud (APQ)",
        "DDA": "Diferencia doble de amplitud (DDA)",
        "NHR": "Relacion ruido/armonicos",
        "HNR": "Relacion armonicos/ruido",
        "RPDE": "Entropia de recurrencia (RPDE)",
        "DFA": "Fluctuacion del habla (DFA)",
        "spread1": "Dispersion espectral 1",
        "spread2": "Dispersion espectral 2",
        "D2": "Complejidad del patron vocal (D2)",
        "PPE": "Entropia del tono (PPE)",
        "button_parkinson": "Resultado del test de Parkinson",
        "positive_parkinson": "La persona puede tener Parkinson, consulte a su medico.",
        "negative_parkinson": "La persona no tiene Parkinson.",
        "help_fo": "Frecuencia fundamental media de la voz (Hz).",
        "help_fhi": "Frecuencia maxima de la voz (Hz).",
        "help_jitter_percent": "Variacion relativa del tono de un ciclo a otro (%).",
        "help_shimmer": "Variacion relativa de la amplitud de un ciclo a otro.",
        "help_nhr": "Relacion ruido/armonicos de la voz.",
        "help_hnr": "Relacion armonicos/ruido en dB (mayor es mejor).",
        "help_rpde": "Medida de complejidad/no linealidad en la voz.",
        "help_ppe": "Irregularidad del periodo del tono (entropia).",
        # Historial
        "history": "Historial de diagnosticos",
        "history_intro": "Consulta los diagnosticos registrados por la aplicacion.",
        "history_filter_name": "Filtrar por nombre (opcional)",
        "history_filter_email": "Filtrar por correo (opcional)",
        "history_limit_label": "Numero maximo de registros a mostrar",
        "history_show_button": "Mostrar historial",
        "history_empty": "Aun no hay diagnosticos registrados.",

        # RECOMENDACIONES MÉDICAS (AÑADIDAS)
        "positive_heart_reco": """
**Recomendaciones médicas para riesgo cardíaco detectado:**
- Consulte su cardiólogo lo antes posible.
- Controle su presión arterial semanalmente.
- Reduzca el consumo de sal y alimentos grasos.
- Realice caminatas de 20–30 min al día.
- Si fuma, busque un plan para dejar de fumar.
- Controle colesterol y triglicéridos.
""",
        "negative_heart_reco": """
**No se observan indicios de enfermedad cardíaca.**
Recomendaciones:
- Mantenga una dieta equilibrada.
- Realice actividad física regularmente.
- Siga controles médicos anuales.
""",
        "positive_parkinson_reco": """
**Recomendaciones ante posible presencia de Parkinson:**
- Consulte a un neurólogo para confirmación del diagnóstico.
- Mantenga actividad física supervisada (fisioterapia).
- Evite estrés excesivo.
- Mantenga chequeos periódicos para evaluar progresión.
""",
        "negative_parkinson_reco": """
**No se detectan signos compatibles con Parkinson.**
Recomendaciones:
- Mantener hábitos saludables.
- Dormir bien y realizar actividad física suave.
""",
        "positive_diabetes_reco": """
**Recomendaciones ante posible presencia de Diabetes:**
- Consulte a un endocrinólogo para una evaluación completa.
- Realice control estricto y regular de los niveles de glucosa.
- Adopte una alimentación baja en azúcares y carbohidratos simples.
- Evite bebidas azucaradas y alimentos ultraprocesados.
- Realice actividad física al menos 150 minutos por semana.
- Controle el peso, la presión arterial y los niveles de colesterol.
""",
        "negative_diabetes_reco": """
**No se detectan signos compatibles con Diabetes.**
Recomendaciones:
- Mantener una alimentación balanceada rica en frutas, verduras y proteína magra.
- Evitar el consumo excesivo de azúcar y grasas saturadas.
- Realizar actividad física regular.
- Controlar los niveles de glucosa al menos una vez al año.
"""
    },
    "en": {
        # Navigation and welcome
        "welcome": "Home",
        "welcome_title": "MedDiag - AI medical triage assistant",
        "welcome_subtitle": "Assistant focused on three conditions: diabetes, heart disease, and Parkinson's.",
        "welcome_steps_title": "How it works",
        "welcome_step_1": "1) Enter basic patient data and the condition form.",
        "welcome_step_2": "2) The AI model estimates risk and shows an orientative recommendation.",
        "welcome_step_3": "3) Save the result to the local log and review it in History.",
        "welcome_diseases_title": "Models available in this demo",
        "welcome_disease_diabetes": "Diabetes: metabolic markers (glucose, BMI, blood pressure).",
        "welcome_disease_heart": "Heart disease: classic clinical factors (cholesterol, pressure, effort).",
        "welcome_disease_parkinson": "Parkinson's: voice-signal features capturing instability and noise.",
        "welcome_next_steps": "Pick a test from the sidebar and run a prediction.",
        "MultipleDPS": "Multiple Disease Prediction System",
        "diabetes_prediction": "Diabetes Prediction",
        "heart_disease_prediction": "Heart Disease Prediction",
        "parkinsons_prediction": "Parkinsons Prediction",
        # Patient data
        "patient_data_title": "Basic patient data",
        "patient_data_caption": "Used to save the result to the database.",
        "patient_name": "Patient name",
        "patient_email": "Email (optional)",
        "patient_phone": "Phone (optional)",
        "patient_age": "Age",
        "patient_gender": "Gender",
        # Diabetes
        "title_diabetes": "Diabetes Prediction with ML",
        "pregnancies": "Number of pregnancies",
        "glucose_level": "Glucose level",
        "blood_pressure": "Blood pressure",
        "skin_thickness": "Skin thickness",
        "insulin_level": "Insulin level",
        "bmi": "Body mass index",
        "diabetes_pedigree_function": "Diabetes pedigree function",
        "age": "Age",
        "button_diabetes": "Diabetes test result",
        "positive_diabetes": "The person may be diabetic, consult your doctor.",
        "negative_diabetes": "The person is not diabetic.",
        "help_pregnancies": "Number of pregnancies (0 if not applicable).",
        "help_glucose": "Fasting blood glucose (mg/dl).",
        "help_blood_pressure": "Diastolic blood pressure (mm Hg).",
        "help_bmi": "Weight (kg) divided by height^2 (m).",
        "help_dpf": "Family diabetes load (0-3).",
        "help_age": "Patient age in years.",
        # Heart
        "title_heart": "Heart disease prediction with ML",
        "sex": "Biological sex",
        "sex_option_male": "Male",
        "sex_option_female": "Female",
        "cp": "Chest pain type",
        "cp_option_0": "0 - Typical angina",
        "cp_option_1": "1 - Atypical angina",
        "cp_option_2": "2 - Non-anginal pain",
        "cp_option_3": "3 - Asymptomatic",
        "trestbps": "Resting blood pressure",
        "chol": "Serum cholesterol (mg/dl)",
        "fbs": "Fasting blood sugar > 120 mg/dl",
        "restecg": "Resting electrocardiographic results",
        "thalach": "Maximum heart rate achieved",
        "exang": "Exercise induced angina",
        "exang_option_no": "No",
        "exang_option_yes": "Yes",
        "oldpeak": "ST depression induced by exercise",
        "slope": "Slope of the peak exercise ST segment",
        "ca": "Major vessels colored by fluoroscopy",
        "thal": "thal: 0 = normal; 1 = fixed defect; 2 = reversible defect",
        "button_heart": "Heart disease test result",
        "positive_heart": "The person may have a heart condition, consult your doctor.",
        "negative_heart": "The person does not have a heart condition.",
        "help_sex": "Biological sex. Encoded 1=M, 0=F.",
        "help_cp": "0: typical, 1: atypical, 2: non-anginal, 3: asymptomatic.",
        "help_trestbps": "Resting blood pressure (mm Hg).",
        "help_chol": "Total fasting cholesterol (mg/dl).",
        "help_thalach": "Max heart rate achieved during effort.",
        "help_exang": "Chest pain that appears or worsens with exercise.",
        "help_oldpeak": "Drop of the ST segment compared to rest.",
        "help_ca": "Number of major vessels colored (0-3).",
        # Parkinson
        "title_parkinson": "Parkinson's Disease Prediction with ML",
        "fo": "MDVP:Fo(Hz)",
        "fhi": "MDVP:Fhi(Hz)",
        "flo": "MDVP:Flo(Hz)",
        "jitter_percent": "MDVP:Jitter(%)",
        "jitter_abs": "MDVP:Jitter(Abs)",
        "RAP": "MDVP:RAP",
        "PPQ": "MDVP:PPQ",
        "DDP": "Jitter:DDP",
        "shimmer": "MDVP:Shimmer",
        "shimmer_dB": "MDVP:Shimmer(dB)",
        "APQ3": "Shimmer:APQ3",
        "APQ5": "Shimmer:APQ5",
        "APQ": "MDVP:APQ",
        "DDA": "Shimmer:DDA",
        "NHR": "Noise-to-Harmonics Ratio (NHR)",
        "HNR": "Harmonics-to-Noise Ratio (HNR)",
        "RPDE": "Recurrence Period Density Entropy (RPDE)",
        "DFA": "Speech fluctuation (DFA)",
        "spread1": "Spectral spread 1",
        "spread2": "Spectral spread 2",
        "D2": "Vocal pattern complexity (D2)",
        "PPE": "Pitch period entropy (PPE)",
        "button_parkinson": "Parkinson's test result",
        "positive_parkinson": "The person may have Parkinson's disease, consult your doctor.",
        "negative_parkinson": "The person does not have Parkinson's disease.",
        "help_fo": "Average fundamental frequency of the voice (Hz).",
        "help_fhi": "Maximum voice frequency (Hz).",
        "help_jitter_percent": "Relative pitch variation from cycle to cycle (%).",
        "help_shimmer": "Relative amplitude variation from cycle to cycle.",
        "help_nhr": "Noise-to-harmonics ratio of the voice.",
        "help_hnr": "Harmonics-to-noise ratio in dB (higher is better).",
        "help_rpde": "Measure of non-linearity/complexity in the voice.",
        "help_ppe": "Irregularity of the pitch period (entropy).",
        # History
        "history": "Diagnosis history",
        "history_intro": "Browse the diagnoses stored by the application.",
        "history_filter_name": "Filter by name (optional)",
        "history_filter_email": "Filter by email (optional)",
        "history_limit_label": "Max records to show",
        "history_show_button": "Show history",
        "history_empty": "No diagnoses have been stored yet.",

        # RECOMENDACIONES MÉDICAS (AÑADIDAS)
        "positive_heart_reco": """
**Medical recommendations for detected heart risk:**
- Consult your cardiologist as soon as possible.
- Check your blood pressure weekly.
- Reduce consumption of salt and fatty foods.
- Take 20–30 min walks daily.
- If you smoke, seek a plan to quit smoking.
- Control cholesterol and triglycerides.
""",
        "negative_heart_reco": """
**No signs of heart disease observed.**
Recommendations:
- Maintain a balanced diet.
- Exercise regularly.
- Follow annual medical check-ups.
""",
        "positive_parkinson_reco": """
**Recommendations for possible presence of Parkinson's:**
- Consult a neurologist for diagnosis confirmation.
- Maintain supervised physical activity (physiotherapy).
- Avoid excessive stress.
- Maintain periodic check-ups to assess progression.
""",
        "negative_parkinson_reco": """
**No signs compatible with Parkinson's detected.**
Recommendations:
- Maintain healthy habits.
- Sleep well and perform gentle physical activity.
""",
        "positive_diabetes_reco": """
**Recommendations for possible presence of Diabetes:**
- Consult an endocrinologist for a complete evaluation.
- Perform strict and regular control of glucose levels.
- Adopt a diet low in sugars and simple carbohydrates.
- Avoid sugary drinks and ultra-processed foods.
- Exercise at least 150 minutes per week.
- Control weight, blood pressure, and cholesterol levels.
""",
        "negative_diabetes_reco": """
**No signs compatible with Diabetes detected.**
Recommendations:
- Maintain a balanced diet rich in fruits, vegetables, and lean protein.
- Avoid excessive consumption of sugar and saturated fats.
- Perform regular physical activity.
- Control glucose levels at least once a year.
"""
    },
}
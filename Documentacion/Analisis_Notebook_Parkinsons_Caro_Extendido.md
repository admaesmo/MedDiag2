# Análisis Técnico Extendido: Notebook `Parkinsons_Caro(1).ipynb`

**Documento generado a partir del análisis del notebook de Diana Carolina Huertas González**  
**Proyecto:** MedDiag2 — Sistema de Diagnóstico Médico Basado en IA  
**Enfermedad:** Enfermedad de Parkinson  
**Dataset base:** UCI ML Parkinson's Dataset (Kaggle)  
**Fecha del análisis:** Mayo 2026

---

## Tabla de Contenidos

1. [Resumen ejecutivo](#1-resumen-ejecutivo)
2. [Arquitectura general del notebook](#2-arquitectura-general-del-notebook)
3. [Fase 1: Entrenamiento con dataset tabular](#3-fase-1-entrenamiento-con-dataset-tabular)
   - 3.1 Carga y exploración de datos
   - 3.2 Distribución de clases
   - 3.3 Preparación de datos
   - 3.4 Normalización con StandardScaler
4. [Fase 2: Modelado y evaluación](#4-fase-2-modelado-y-evaluación)
   - 4.1 Screening inicial con LazyPredict
   - 4.2 Modelos entrenados manualmente
   - 4.3 Ensemble con VotingClassifier
   - 4.4 Métricas y criterio de selección
   - 4.5 Resultados reportados
5. [Problemas críticos de reproducibilidad](#5-problemas-críticos-de-reproducibilidad)
   - 5.1 Variables no definidas (`best_model_name`, `best_model_idx`, `expected`)
   - 5.2 Dependencia de estado de sesión de Colab
   - 5.3 Errores NameError en celdas clave
   - 5.4 Ejecución fuera de orden
6. [Fase 3: Extracción de biomarcadores desde audio](#6-fase-3-extracción-de-biomarcadores-desde-audio)
   - 6.1 Función `extraer_biomarcadores()` y Parselmouth
   - 6.2 Biomarcadores extraídos vs. rellenos
   - 6.3 Imputación de variables no lineales con promedios fijos
7. [Punto crítico: Ruptura del contrato de features](#7-punto-crítico-ruptura-del-contrato-de-features)
   - 7.1 El problema de las 22 vs. 14 columnas
   - 7.2 Implicaciones para StandardScaler
   - 7.3 Consecuencias en la inferencia
8. [Fase 4: Inferencia sobre audios reales](#8-fase-4-inferencia-sobre-audios-reales)
   - 8.1 Función `diagnosticar_audio()`
   - 8.2 Pipeline de predicción multicaptura
9. [Fase 5: Componentes exploratorios adicionales](#9-fase-5-componentes-exploratorios-adicionales)
   - 9.1 Espectrogramas y experimentos con CNN
   - 9.2 Procesamiento de lenguaje natural con spaCy
10. [Recomendaciones para integración en MedDiag2](#10-recomendaciones-para-integración-en-meddiag2)
    - 10.1 Correcciones al notebook
    - 10.2 Contrato de features
    - 10.3 Paquete de despliegue
    - 10.4 Mejoras al extractor de audio
11. [Conclusión](#11-conclusión)

---

## 1. Resumen ejecutivo

El notebook `Parkinsons_Caro(1).ipynb` es un cuaderno de Google Colab desarrollado por **Diana Carolina Huertas González** como parte del proyecto MedDiag. Su objetivo es doble:

1. **Entrenar y seleccionar** modelos de clasificación binaria (Parkinson vs. Sano) usando el dataset clásico de UCI/Kaggle, que contiene 195 muestras con 22 biomarcadores acústicos extraídos con MDVP (Multi-Dimensional Voice Program).
2. **Conectar ese modelo con audios reales** mediante la librería Parselmouth (interfaz Python de Praat) para extraer biomarcadores desde grabaciones de voz y alimentar al clasificador.

El notebook refleja un esfuerzo metodológicamente sólido en la fase de entrenamiento (comparación de modelos, uso de Recall como métrica clínica principal, estratificación en train/test), pero presenta **debilidades técnicas significativas** en la fase de inferencia que comprometen su integración directa en producción.

Este documento extiende, corrige y complementa el análisis original, identificando con precisión cada punto de fallo y proponiendo soluciones concretas para MedDiag2.

---

## 2. Arquitectura general del notebook

El notebook se organiza en 5 fases conceptuales:

| Fase | Celdas | Propósito | Estado |
|------|--------|-----------|--------|
| **Fase 1: Entrenamiento** | 27–57 | Carga, EDA, entrenamiento de 7 modelos, comparación por Recall | ✅ Funcional |
| **Fase 2: Selección y guardado** | 59–1 (reinicio) | Selección del mejor modelo, matriz de confusión, guardado .sav | ⚠️ Con errores NameError |
| **Fase 3: Extracción de audio** | — | Función `extraer_biomarcadores()` con Parselmouth | ✅ Definida, no ejecutada |
| **Fase 4: Inferencia** | — | Función `diagnosticar_audio()` y predicción multicaptura | ❌ Ruptura de features |
| **Fase 5: Exploración CNN/NLP** | — | Espectrogramas con librosa, spaCy para NLP | 🔬 Exploratorio |

> **Nota importante:** Las numeraciones de celdas (`execution_count`) revelan que el notebook fue ejecutado en múltiples sesiones de Colab, con reinicios del kernel y ejecución no lineal. Por ejemplo, la celda de guardado tiene `execution_count: 1`, mientras que celdas anteriores tienen `execution_count: 57, 59`, evidenciando que el kernel se reinició entre la Fase 2 y el guardado.

---

## 3. Fase 1: Entrenamiento con dataset tabular

### 3.1 Carga y exploración de datos

```python
df = pd.read_csv('/content/drive/My Drive/parkinsons.data')
```

El dataset se carga desde Google Drive. Según la documentación del dataset UCI/Kaggle original:

- **195 muestras** (filas)
- **24 columnas** en crudo: `name` (identificador del paciente), 22 biomarcadores MDVP, y `status` (variable objetivo)
- **0 valores nulos** reportados

### 3.2 Distribución de clases

La variable `status` está desbalanceada:

| Clase | Descripción | Muestras | Proporción |
|-------|-------------|----------|------------|
| 1 | Con Parkinson | 147 | 75.4% |
| 0 | Sin Parkinson | 48 | 24.6% |

Este desbalance (3:1) justifica que el notebook priorice **Recall** como métrica principal: es más crítico clínicamente evitar falsos negativos (no detectar Parkinson) que evitar falsos positivos.

### 3.3 Preparación de datos

```python
y = df[target_column]  # 'status'
X = df.drop(target_column, axis=1).select_dtypes(include=[np.number])
```

Esta operación:
- Elimina la columna `status` (target)
- Excluye columnas no numéricas como `name` (identificador del paciente)
- Retiene las **22 features acústicas** numéricas originales

**Split entrenamiento/prueba:**

```python
train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
```

| Partición | Muestras | Proporción |
|-----------|----------|------------|
| Entrenamiento | 156 | 80% |
| Prueba | 39 | 20% |

El uso de `stratify=y` asegura que ambas particiones mantengan la misma proporción 75/25 de clases.

### 3.4 Normalización con StandardScaler

```python
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)
```

**Punto clave:** El `StandardScaler` se ajusta (fit) exclusivamente sobre los datos de entrenamiento, calculando media y desviación estándar para cada una de las **22 features**. Luego transforma tanto entrenamiento como prueba con esos parámetros.

> **Implicación para producción:** Cualquier dato nuevo que se quiera clasificar debe pasar por **el mismo scaler** (mismos parámetros de estandarización: medias y desviaciones por columna), y debe tener **exactamente las mismas 22 columnas en el mismo orden**.

---

## 4. Fase 2: Modelado y evaluación

### 4.1 Screening inicial con LazyPredict

```python
from lazypredict.Supervised import LazyClassifier
clf = LazyClassifier(verbose=0, ignore_warnings=True, custom_metric=None)
models, predictions = clf.fit(X_train, X_test, y_train, y_test)
```

LazyPredict entrena y evalúa automáticamente ~30 clasificadores, proporcionando una tabla comparativa de Accuracy, Balanced Accuracy, F1-Score, etc. Es útil como **filtro preliminar** para identificar qué familias de modelos funcionan mejor con estos datos.

**Nota:** LazyPredict usa los datos **sin escalar** porque aplica su propio preprocesamiento interno.

### 4.2 Modelos entrenados manualmente

El notebook entrena 6 modelos individuales + 1 ensemble:

| # | Modelo | Datos de entrada | Hiperparámetros clave |
|---|--------|-------------------|----------------------|
| 1 | **SVM** (SVC) | Escalados | kernel='rbf', C=1.0, probability=True |
| 2 | **Random Forest** | Sin escalar | n_estimators=200, max_depth=10 |
| 3 | **Logistic Regression** | Escalados | max_iter=1000 |
| 4 | **XGBoost** | Escalados | n_estimators=200, lr=0.05, max_depth=4 |
| 5 | **AdaBoost** | Escalados | n_estimators=100 |
| 6 | **LDA** | Escalados | — |

Y adicionalmente entrena un segundo XGBoost con parámetros diferentes (n_estimators=100, lr=0.1, max_depth=5) que es redundante.

### 4.3 Ensemble con VotingClassifier

```python
ensemble_model = VotingClassifier(
    estimators=[('xgb', xgb_model), ('rf', rf_model), ('svm', svm_model),
                ('lr', lr_model), ('ada', ada_model)],
    voting='soft',
    weights=[3, 2, 1, 1, 2]
)
```

Usa votación blanda (soft voting: promedia probabilidades) con pesos: XGBoost (3), Random Forest (2), AdaBoost (2), SVM (1), Logistic Regression (1).

### 4.4 Métricas y criterio de selección

La tabla de resultados se ordena por **Recall** (sensibilidad), con umbral de aceptación clínica ≥ 0.90:

```python
results_df = results_df.sort_values(by='Recall', ascending=False)
meta_recall = 0.90
```

Métricas calculadas para cada modelo:
- Accuracy
- Balanced Accuracy
- Precision
- **Recall** (métrica principal)
- F1-Score
- AUC-ROC

### 4.5 Resultados reportados

Según los `print()` visibles en las celdas ejecutadas:

**SVM (mejor Recall):**
| Métrica | Valor |
|---------|-------|
| Accuracy | 0.9231 |
| Precision | 0.9062 |
| **Recall** | **1.0000** |
| F1-Score | 0.9508 |
| AUC-ROC | 0.9552 |

**XGBoost (segundo mejor):**
| Métrica | Valor |
|---------|-------|
| Accuracy | 92.31% |
| Recall | 0.9655 |
| F1 | 0.9492 |
| ROC AUC | 0.9862 |

**Interpretación:** SVM detecta el 100% de los casos positivos en el conjunto de prueba, pero puede estar sobreajustado al desbalance (clase mayoritaria). XGBoost tiene mejor AUC-ROC (0.9862 vs 0.9552), lo que sugiere mejor capacidad discriminativa general.

---

## 5. Problemas críticos de reproducibilidad

### 5.1 Variables no definidas

Varias celdas del notebook utilizan variables que **nunca se definen explícitamente** en celdas anteriores visibles:

| Variable | Usada en celda | Problema |
|----------|---------------|----------|
| `best_model_name` | Celda 59 (selección del mejor modelo) | No se define antes del bloque condicional |
| `best_model_idx` | Celda de resumen final: `results_df.loc[best_model_idx]` | No se define en ninguna celda visible |
| `expected` | Celda de resumen final: `expected['Accuracy']` | Se usa como diccionario pero nunca se inicializa |

### 5.2 Dependencia de estado de sesión de Colab

El notebook asume que ciertas variables persisten en memoria porque fueron definidas en ejecuciones previas de la misma sesión de Colab. Esto es evidente porque:

1. La celda con `execution_count: 1` (guardado del modelo) usa `best_model_name`, que debió definirse en una celda anterior no visible o en una ejecución fuera de orden.
2. La celda de resumen final (`execution_count: null`) usa `best_model_idx` y `expected`, que no aparecen en ninguna celda previa.

### 5.3 Errores NameError documentados

En los metadatos del notebook se registran explícitamente errores:

- Celda 59 (`execution_count: 59`): `"status": "error"` — indica que la celda falló al ejecutarse.
- Celda de guardado (`execution_count: 1`): `"status": "error"` — también falló.

Esto confirma que el notebook **no es reproducible** ejecutándolo secuencialmente de arriba a abajo.

### 5.4 Ejecución fuera de orden

La secuencia de `execution_count` revela el orden real de ejecución:

```
27 → 28 → 29 → 56 → 31 → 32 → 33 → 34 → 35 → 36 → 41 → 48 → 51 → 52 → 53 → 57 → 59 → 1
```

Notar que:
- La celda 56 (importación de librerías) se ejecutó **después** de la celda 29 (conversión de audio), indicando que el kernel se reinició y se reimportaron librerías.
- La celda 59 (selección de mejor modelo) se ejecutó **antes** que la celda 1 (guardado), pero la 59 falló y la 1 también.
- Hay celdas con `execution_count: null` que nunca se ejecutaron.

---

## 6. Fase 3: Extracción de biomarcadores desde audio

### 6.1 Función `extraer_biomarcadores()` y Parselmouth

```python
def extraer_biomarcadores(audio_path):
    sound = parselmouth.Sound(audio_path)
    pitch = call(sound, "To Pitch", 0.0, 75, 500)
    # ... extrae F0, jitter, shimmer, HNR
```

La función utiliza **Parselmouth** (binding Python de Praat) para extraer biomarcadores acústicos desde un archivo `.wav`. Específicamente:

- **F0:** `To Pitch` con rango 75–500 Hz (típico para voz humana)
- **Jitter:** `Get jitter (local)`, `(local, absolute)`, `(rap)`, `(ppq5)` desde PointProcess
- **Shimmer:** `Get shimmer (local)`, `(local_db)`, `(apq3)`, `(apq5)` desde Sound+PointProcess
- **HNR:** `To Harmonicity (cc)` — Harmonics-to-Noise Ratio por correlación cruzada
- **NHR:** Calculado como `1 / (10^(HNR/10))` — conversión inversa desde HNR

**Aciertos metodológicos:**
- Usa Parselmouth, que implementa los algoritmos estándar de Praat, ampliamente validados en fonética clínica.
- Rango de pitch 75–500 Hz adecuado para voz humana.
- Multiplica `Jitter(%)` por 100 para igualar la escala del dataset MDVP original.

### 6.2 Biomarcadores extraídos vs. rellenos

De los 22 biomarcadores requeridos:

| Tipo | Biomarcadores | Método |
|------|--------------|--------|
| **Reales** (16) | MDVP:Fo(Hz), MDVP:Fhi(Hz), MDVP:Flo(Hz), MDVP:Jitter(%), MDVP:Jitter(Abs), MDVP:RAP, MDVP:PPQ, Jitter:DDP, MDVP:Shimmer, MDVP:Shimmer(dB), Shimmer:APQ3, Shimmer:APQ5, MDVP:APQ, Shimmer:DDA, NHR, HNR | Extraídos con Parselmouth |
| **Relleno** (6) | RPDE, DFA, spread1, spread2, D2, PPE | Valores promedio fijos del dataset |

### 6.3 Imputación de variables no lineales con promedios fijos

```python
'RPDE': 0.498,
'DFA': 0.718,
'spread1': -5.68,
'spread2': 0.226,
'D2': 2.38,
'PPE': 0.206
```

**Problema metodológico grave:** Estos valores son promedios del dataset de entrenamiento. Usarlos como constantes para cualquier audio entrante:

1. **Invalida la variabilidad inter-sujeto:** Si dos personas tienen valores radicalmente diferentes de RPDE, el modelo recibirá el mismo valor para ambas, perdiendo poder discriminativo.
2. **Sesga la predicción hacia la media:** Las variables no lineales actuarán como "sesgo constante", reduciendo la capacidad del modelo para detectar diferencias reales.
3. **Crea falsa confianza:** El modelo producirá una probabilidad que parece personalizada, pero 6 de 22 features (27%) son idénticas para todos los pacientes.

> **Para MedDiag2:** Es mejor implementar correctamente estos biomarcadores no lineales (como se ha hecho en la rama `marcadoresNL`) que usar promedios fijos. Alternativamente, se puede entrenar un modelo reducido con solo las 16 features extraíbles, o marcar explícitamente la inferencia como `partial_features` con advertencia al usuario.

---

## 7. Punto crítico: Ruptura del contrato de features

### 7.1 El problema de las 22 vs. 14 columnas

Este es **el error más grave** del notebook para propósitos de integración:

```python
# En diagnosticar_audio():
columnas_entrenamiento = [
    'MDVP:Fo(Hz)', 'MDVP:Fhi(Hz)', 'MDVP:Flo(Hz)', 'MDVP:Jitter(%)',
    'MDVP:Jitter(Abs)', 'MDVP:RAP', 'MDVP:PPQ', 'MDVP:Shimmer',
    'MDVP:Shimmer(dB)', 'Shimmer:APQ3', 'Shimmer:APQ5', 'MDVP:APQ',
    'Shimmer:DDA', 'HNR'
]  # ¡SOLO 14 COLUMNAS!
```

El modelo fue entrenado con **22 columnas**, pero la inferencia sobre audios nuevos usa **14 columnas**. Las columnas faltantes son:

```
Jitter:DDP         ← derivable de RAP (DDP = 3 × RAP)
NHR                ← calculable desde HNR
RPDE               ← no lineal
DFA                ← no lineal
spread1            ← no lineal
spread2            ← no lineal
D2                 ← no lineal
PPE                ← no lineal
```

Notar que `Jitter:DDP` y `NHR` son calculables desde variables presentes, pero aún así se excluyen del subconjunto.

### 7.2 Implicaciones para StandardScaler

El `StandardScaler` guardado fue entrenado con 22 features. Cuando se llama a:

```python
scaler = joblib.load(scaler_path)
datos_escalados = scaler.transform(df_nuevo)  # df_nuevo tiene 14 columnas
```

**`scaler.transform()` espera exactamente 22 columnas.** Recibir 14 columnas causará:

- **En scikit-learn ≥ 1.0:** `ValueError: The number of features of the input is different from the number of features in the transformer.`
- **En versiones anteriores:** Comportamiento indefinido o error silencioso.

### 7.3 Consecuencias en la inferencia

Incluso si el error de dimensiones se evitara (por ejemplo, con un scaler que acepte cualquier número de columnas, que no es el caso de `StandardScaler`), el resultado sería:

- **El modelo recibiría un vector de 14 features** cuando espera 22.
- La predicción sería **numéricamente inválida** desde la perspectiva del modelo entrenado.
- Cualquier probabilidad generada sería **espuria**.

---

## 8. Fase 4: Inferencia sobre audios reales

### 8.1 Función `diagnosticar_audio()`

```python
def diagnosticar_audio(audio_path, modelo_path, scaler_path):
    dict_biomarcadores = extraer_biomarcadores(audio_path)
    df_nuevo = pd.DataFrame([dict_biomarcadores])
    modelo = joblib.load(modelo_path)
    scaler = joblib.load(scaler_path)
    df_nuevo = df_nuevo[columnas_entrenamiento]  # 14 columnas — ERROR
    datos_escalados = scaler.transform(df_nuevo)   # Fallará
    prediccion = modelo.predict(datos_escalados)[0]
    probabilidad = modelo.predict_proba(datos_escalados)[0][1]
```

**Flujo correcto debería ser:**
```python
# 1. Extraer diccionario completo (22 keys)
dict_biomarcadores = extraer_biomarcadores(audio_path)
# 2. Crear DataFrame
df_nuevo = pd.DataFrame([dict_biomarcadores])
# 3. Asegurar el orden exacto de las 22 columnas
columnas_originales = [
    'MDVP:Fo(Hz)', 'MDVP:Fhi(Hz)', 'MDVP:Flo(Hz)', 'MDVP:Jitter(%)',
    'MDVP:Jitter(Abs)', 'MDVP:RAP', 'MDVP:PPQ', 'Jitter:DDP',
    'MDVP:Shimmer', 'MDVP:Shimmer(dB)', 'Shimmer:APQ3', 'Shimmer:APQ5',
    'MDVP:APQ', 'Shimmer:DDA', 'NHR', 'HNR',
    'RPDE', 'DFA', 'spread1', 'spread2', 'D2', 'PPE'
]
df_nuevo = df_nuevo[columnas_originales]  # 22 columnas
# 4. Escalar y predecir
datos_escalados = scaler.transform(df_nuevo)
```

### 8.2 Pipeline de predicción multicaptura

El notebook propone un enfoque interesante para robustecer la predicción:

```python
mis_archivos = ['toma1.wav', 'toma2.wav', 'toma3.wav']
# ... procesar cada uno ...
promedio_confianza = sum(probabilidades) / len(probabilidades)
veredicto_final = "POSITIVO" if promedio_confianza > 0.5 else "NEGATIVO"
```

La idea de **promediar 3 tomas** es metodológicamente sólida: reduce el impacto de variaciones aleatorias en la grabación (tos, ruido ambiental, fatiga vocal). Sin embargo:

- Solo considera promediar la confianza, no usa lógica de votación mayoritaria.
- El umbral de 0.5 es naive; un umbral calibrado (dado el desbalance) sería más apropiado.

---

## 9. Fase 5: Componentes exploratorios adicionales

### 9.1 Espectrogramas y experimentos con CNN

El notebook incluye celdas para generación de espectrogramas con `librosa`:

```python
S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)
S_dB = librosa.power_to_db(S, ref=np.max)
```

Además importa TensorFlow y TensorFlow Hub, sugiriendo la intención de explorar redes convolucionales sobre espectrogramas, aunque **no hay implementación concreta de entrenamiento CNN** en el notebook visible.

### 9.2 Procesamiento de lenguaje natural con spaCy

```python
import spacy
nlp = spacy.load("es_core_news_lg")
```

Se instala y carga el modelo grande de spaCy en español, lo cual es inusual en un notebook de clasificación de Parkinson. Posiblemente sea para un experimento separado de análisis lingüístico (por ejemplo, análisis de habla conectada), pero no hay integración con el pipeline de diagnóstico.

---

## 10. Recomendaciones para integración en MedDiag2

### 10.1 Correcciones al notebook

Para hacer el notebook reproducible:

1. **Definir explícitamente las variables faltantes** antes de usarlas:

```python
best_model_name = results_df.iloc[0]['Modelo']    # 'SVM'
best_model_idx = results_df.index[0]
expected = {
    'Accuracy': 0.85,
    'Precision': 0.85,
    'Recall': 0.90,
    'F1-Score': 0.87,
    'AUC-ROC': 0.90
}
```

2. **Reordenar las celdas** para que el flujo de ejecución sea secuencial.
3. **Eliminar redundancias** (el segundo entrenamiento de XGBoost que duplica al primero).
4. **Documentar la selección final del modelo** con criterios claros.

### 10.2 Contrato de features

Establecer un **contrato formal** entre el extractor de biomarcadores y el modelo:

```
CONTRATO DE FEATURES — Modelo Parkinson v1
------------------------------------------------
Número de features: 22
Orden exacto:
  1.  MDVP:Fo(Hz)
  2.  MDVP:Fhi(Hz)
  3.  MDVP:Flo(Hz)
  4.  MDVP:Jitter(%)
  5.  MDVP:Jitter(Abs)
  6.  MDVP:RAP
  7.  MDVP:PPQ
  8.  Jitter:DDP
  9.  MDVP:Shimmer
  10. MDVP:Shimmer(dB)
  11. Shimmer:APQ3
  12. Shimmer:APQ5
  13. MDVP:APQ
  14. Shimmer:DDA
  15. NHR
  16. HNR
  17. RPDE
  18. DFA
  19. spread1
  20. spread2
  21. D2
  22. PPE

Scaler: StandardScaler con 22 dimensiones
Formato esperado: numpy array de shape (n_samples, 22)
Rango de valores: sin rango fijo (datos estandarizados, media=0, std=1)
```

### 10.3 Paquete de despliegue

Guardar un único paquete serializado que contenga:

```python
deploy_package = {
    'model': best_model,         # clasificador entrenado
    'scaler': scaler,            # StandardScaler ajustado
    'feature_names': columnas,   # lista ordenada de 22 nombres
    'model_name': best_model_name,
    'metrics': best_metrics,
    'version': '1.0.0',
    'training_date': '2025-04-01',
    'dataset_size': 195,
    'feature_contract': {
        'n_features': 22,
        'scaler_mean': scaler.mean_.tolist(),
        'scaler_std': scaler.scale_.tolist()
    }
}
joblib.dump(deploy_package, 'parkinsons_deploy_v1.pkl')
```

### 10.4 Mejoras al extractor de audio

Para cerrar la brecha entre las 16 features extraíbles y las 22 del modelo:

| Estrategia | Descripción | Riesgo |
|------------|-------------|--------|
| **Implementar no lineales** | Calcular RPDE, DFA, D2, PPE, spread1, spread2 desde la señal | Requiere validación científica |
| **Modelo reducido** | Reentrenar con solo 16 features extraíbles | Pierde poder predictivo potencial |
| **Imputación avanzada** | Usar modelos de imputación (MICE, KNN) en vez de promedios fijos | Más robusto pero más complejo |
| **Partial features flag** | Marcar inferencia como parcial si alguna feature no pudo calcularse | Transparencia sobre certeza |

**Recomendación para MedDiag2:** Implementar las 6 variables no lineales (como se ha comenzado en la rama `marcadoresNL`), validar contra dataset de referencia, y solo entonces usarlas en producción. Mientras tanto, usar `is_partial=True` y `missing_features` para trazabilidad.

---

## 11. Conclusión

El notebook de Diana representa un trabajo valioso como **base académica de entrenamiento**: compara rigurosamente múltiples modelos, prioriza métricas clínicas relevantes (Recall), documenta visualizaciones y establece la conexión conceptual entre biomarcadores de voz y clasificación de Parkinson.

Sin embargo, para integrarlo seriamente en MedDiag2 como pipeline de producción, es necesario resolver:

1. **✅ Reproducibilidad:** Definir explícitamente todas las variables (`best_model_name`, `best_model_idx`, `expected`) y reordenar la ejecución secuencialmente.
2. **❌ Contrato de features:** Eliminar la discrepancia 22 vs. 14 columnas en `diagnosticar_audio()`. El modelo debe recibir **exactamente** el mismo vector que usó en entrenamiento.
3. **⚠️ Variables no lineales:** Reemplazar los promedios fijos con implementaciones reales (ramas `marcadoresNL`), o reducir el modelo a features extraíbles.
4. **📦 Paquete unificado:** Empaquetar `modelo + scaler + orden_features` como una sola unidad desplegable.

La visión del notebook está bien encaminada: un clasificador tabular sobre biomarcadores acústicos, con extracción desde audio vía Parselmouth. Lo que falta es **cerrar el contrato** entre el extractor y el clasificador para que producción no alimente al modelo con un vector distinto al de entrenamiento.

---

## Apéndice A: Mapa de errores por celda

| execution_count | Descripción | Estado | Error |
|----------------|-------------|--------|-------|
| 27 | Instalación de dependencias | ✅ | — |
| 28 | Montar Google Drive | ✅ | — |
| 29 | Conversión m4a → wav | ✅ | — |
| 56 | Importar librerías | ✅ | — |
| 31 | Cargar dataset | ✅ | — |
| 32 | Estadísticas descriptivas | ✅ | — |
| 33 | Identificar columna objetivo | ✅ | — |
| 34 | Visualizar distribución | ✅ | — |
| 35 | Separar X/y | ✅ | — |
| 36 | Train/test split | ✅ | — |
| 41 | Normalizar con StandardScaler | ✅ | — |
| 48 | LazyPredict | ✅ | — |
| 51 | Entrenamiento de modelos | ✅ | — |
| 52 | Segundo XGBoost | ✅ | — |
| 53 | Ensemble | ✅ | — |
| 57 | Evaluación y tabla comparativa | ✅ | — |
| **59** | **Selección mejor modelo** | **❌** | **NameError: best_model_name** |
| **1** | **Guardar modelo** | **❌** | **NameError: best_model_name** |
| null | Resumen final | ⛔ No ejecutada | — |
| null | Matriz de confusión adicional | ⛔ No ejecutada | — |
| null | Curva ROC adicional | ⛔ No ejecutada | — |
| null | Importancia de features | ⛔ No ejecutada | — |
| null | extraer_biomarcadores() | ⛔ Solo definición | — |
| null | diagnosticar_audio() | ⛔ Solo definición | ❌ 14 col vs 22 |
| null | Inferencia multicaptura | ⛔ No ejecutada | — |
| null | Espectrogramas | ✅ (audio de ejemplo) | — |

## Apéndice B: Diccionario completo de biomarcadores

| # | Nombre MDVP | Descripción | Tipo | Extraíble con Parselmouth |
|---|-------------|-------------|------|--------------------------|
| 1 | MDVP:Fo(Hz) | Frecuencia fundamental media | Frecuencia | ✅ Sí |
| 2 | MDVP:Fhi(Hz) | Frecuencia fundamental máxima | Frecuencia | ✅ Sí |
| 3 | MDVP:Flo(Hz) | Frecuencia fundamental mínima | Frecuencia | ✅ Sí |
| 4 | MDVP:Jitter(%) | Variación relativa del período | Jitter | ✅ Sí |
| 5 | MDVP:Jitter(Abs) | Variación absoluta del período | Jitter | ✅ Sí |
| 6 | MDVP:RAP | Perturbación del período relativa | Jitter | ✅ Sí |
| 7 | MDVP:PPQ | Cuasiente de perturbación del pitch | Jitter | ✅ Sí |
| 8 | Jitter:DDP | Difference of Differences of Period | Jitter | ✅ Sí (3×RAP) |
| 9 | MDVP:Shimmer | Variación de amplitud relativa | Shimmer | ✅ Sí |
| 10 | MDVP:Shimmer(dB) | Variación de amplitud en dB | Shimmer | ✅ Sí |
| 11 | Shimmer:APQ3 | Cuasiente de perturbación de amplitud (3-punto) | Shimmer | ✅ Sí |
| 12 | Shimmer:APQ5 | Cuasiente de perturbación de amplitud (5-punto) | Shimmer | ✅ Sí |
| 13 | MDVP:APQ | Cuasiente de perturbación de amplitud | Shimmer | ✅ Sí |
| 14 | Shimmer:DDA | Difference of Differences of Amplitude | Shimmer | ✅ Sí (3×APQ3) |
| 15 | NHR | Noise-to-Harmonics Ratio | Ruido | ⚠️ Aproximado |
| 16 | HNR | Harmonics-to-Noise Ratio | Ruido | ✅ Sí |
| 17 | RPDE | Recurrence Period Density Entropy | No lineal | ❌ No |
| 18 | DFA | Detrended Fluctuation Analysis | No lineal | ❌ No |
| 19 | spread1 | Dispersión de frecuencia fundamental | No lineal | ❌ No |
| 20 | spread2 | Dispersión de frecuencia fundamental | No lineal | ❌ No |
| 21 | D2 | Correlation Dimension | No lineal | ❌ No |
| 22 | PPE | Pitch Period Entropy | No lineal | ❌ No |

---

*Documento generado como parte del análisis técnico del proyecto MedDiag2.*  
*Notebook analizado: `Parkinsons_Caro(1).ipynb` de Diana Carolina Huertas González.*

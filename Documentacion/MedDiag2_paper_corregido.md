> **Documento formato IEEE — Versión 1.0**
> *Este documento sigue el estilo de las transacciones IEEE (IEEEtran.cls).*

# MedDiag2: Plataforma Experimental de Tamizaje de Parkinson Basada en Voz, Control de Calidad y Biomarcadores Acústicos Trazables

Adrián Espinosa, *Student Member, IEEE*, Diana Huertas, *Student Member, IEEE*,
and David Ríos, *Student Member, IEEE*

---

**Resumen—** MedDiag2 evoluciona desde un prototipo de apoyo diagnóstico basado en variables clínicas ingresadas manualmente hacia una plataforma académica de tamizaje experimental centrada en captura de voz, control de calidad, extracción de biomarcadores acústicos y trazabilidad de inferencia. El proyecto integra una aplicación web, un backend en FastAPI, almacenamiento de audios, procesamiento digital de señales y modelos de aprendizaje automático orientados al análisis preliminar de patrones vocales asociados a la enfermedad de Parkinson. La ruta técnica actual conserva un enfoque basado en biomarcadores interpretables porque el modelo histórico de Parkinson fue entrenado con variables acústicas estructuradas, no con audio crudo. Por ello, el reto central no consiste solamente en recibir archivos de audio desde el usuario, sino en garantizar que las características extraídas sean comparables, reproducibles, auditables y metodológicamente defendibles.

En la rama `marcadoresNL`, MedDiag2 incorpora implementaciones determinísticas iniciales para biomarcadores no lineales como DFA, D2, PPE, RPDE, spread1 y spread2. Estas implementaciones sustituyen aproximaciones no reproducibles previas, pero todavía deben entenderse como una etapa experimental que requiere validación frente a herramientas de referencia y audios controlados. Adicionalmente, la versión actual incorpora un módulo de control de calidad de audio que calcula duración, energía RMS, saturación, relación señal-ruido, proporción de silencio, piso de ruido y ancho de banda antes de permitir la extracción de biomarcadores. Este avance convierte el control de calidad en una compuerta metodológica previa a la inferencia y reduce el riesgo de generar predicciones sobre señales inválidas.

El documento sostiene que, en esta fase, MedDiag2 debe priorizar reproducibilidad, equivalencia de características, control de calidad, versionamiento y validación experimental antes que complejidad de infraestructura o modelos de caja negra. Se recomienda mantener Librosa como soporte de carga y procesamiento digital de señales, consolidar Parselmouth/Praat como núcleo para biomarcadores clásicos como F0, jitter, shimmer y HNR, e incorporar datasets más pertinentes para validación externa, especialmente PC-GITA y NeuroVoz. MedDiag2 se define expresamente como una herramienta académica de apoyo y tamizaje experimental, no como un sistema de diagnóstico clínico.

**Palabras clave—** Parkinson, biomarcadores de voz, FastAPI, Parselmouth, Praat, Librosa, control de calidad de audio, aprendizaje automático, procesamiento digital de señales, tamizaje experimental.

---

*Manuscript received May 15, 2026; revised May 15, 2026. This work was supported by the Universidad — Proyecto Integrador, Ingeniería de Sistemas.*
*A. Espinosa, D. Huertas, and D. Ríos are with the Facultad de Ingeniería, Universidad, Colombia (e-mail: {adrian.espinosa, diana.huertas, david.rios}@meddiag2.edu.co).*


---

## I. Introducción

La enfermedad de Parkinson puede producir alteraciones vocales relacionadas con hipofonía, inestabilidad de la fonación, variación de frecuencia fundamental, perturbaciones de amplitud y cambios en la relación armónico-ruido. Debido a ello, diversos estudios han explorado el uso de medidas acústicas como F0, jitter, shimmer, HNR, NHR, RPDE, DFA, D2 y PPE para construir modelos de clasificación, seguimiento o telemonitoreo de síntomas asociados a Parkinson [1], [2].

En MedDiag2, este enfoque resulta pertinente porque el modelo histórico de Parkinson fue entrenado sobre variables biomédicas de voz y no sobre audio crudo. Por esta razón, la evolución del proyecto no debe entenderse como una simple mejora de interfaz para recibir archivos de audio, sino como una reorganización metodológica alrededor del ciclo completo del biomarcador: captura, preprocesamiento, control de calidad, extracción, persistencia versionada, inferencia y auditoría.

La principal dificultad metodológica de MedDiag2 no radica únicamente en construir un endpoint capaz de recibir audio, sino en cerrar la brecha entre el dato usado para entrenar el modelo y el dato generado en producción. En el modelo histórico, las variables acústicas ya estaban previamente calculadas; en la versión actual, esas variables deben ser obtenidas desde grabaciones reales, con diferencias de micrófono, ruido, duración, intensidad y estabilidad fonatoria. Por tanto, el valor investigativo del proyecto no depende solo de producir una probabilidad de riesgo, sino de demostrar que el pipeline de captura, control de calidad, extracción y versionamiento puede generar biomarcadores comparables, auditables y reproducibles.

La selección de una ruta basada en biomarcadores interpretables permite mantener trazabilidad sobre las variables que alimentan el modelo, facilita la comparación con datasets clásicos y evita depender prematuramente de enfoques de aprendizaje profundo que requieren grandes volúmenes de audio etiquetado, control de sesgos y validación clínica robusta. En esta etapa, el proyecto prioriza coherencia entre datos de entrenamiento, extracción en producción y explicación técnica del resultado.

El objetivo de este documento es justificar la ruta técnica actual de MedDiag2, describir su funcionamiento, presentar los avances implementados y delimitar sus limitaciones. El documento se fundamenta en la documentación interna del proyecto, en el análisis del código de la rama `marcadoresNL` y en referencias científicas sobre análisis de voz en Parkinson.

---

## II. Planteamiento del Problema

La versión inicial de MedDiag funcionaba como una aplicación cliente-servidor con frontend, backend FastAPI y modelos serializados. Para Parkinson, el sistema recibía un vector de biomarcadores acústicos ya calculados: frecuencia fundamental, jitter, shimmer, HNR y parámetros no lineales, entre otros. Esta arquitectura era suficiente para probar integración de software, pero dejaba abierto el problema crítico de cómo obtener esos biomarcadores desde audio real.

En la evolución de MedDiag2 se identificaron tres riesgos principales:

1. **Ruptura entre entrenamiento e inferencia:** el modelo fue entrenado con variables estructuradas, pero en producción puede recibir valores calculados por métodos diferentes o bajo condiciones de audio no controladas.
2. **Uso de aproximaciones o placeholders:** algunas variables, especialmente las no lineales, no estaban calculadas de forma reproducible en versiones anteriores.
3. **Imputación silenciosa de valores `0.0`:** el sistema podía generar inferencias numéricamente válidas, pero biomédicamente discutibles, si completaba variables faltantes con ceros sin reportarlo.

Por tanto, la pregunta técnica central del proyecto no debe formularse como "¿qué modelo obtiene mayor exactitud sobre un dataset controlado?", sino como:

> ¿Qué ruta de captura, control de calidad, extracción, versionamiento y validación permite que los biomarcadores usados por el modelo de Parkinson sean comparables con los datos de entrenamiento y suficientemente trazables para una herramienta de tamizaje experimental?

Esta formulación evita reducir el proyecto a una competencia de algoritmos y centra la investigación en la confiabilidad del dato que alimenta el modelo.

---

## III. Objetivos

### A. Objetivo General

Desarrollar y documentar un prototipo web de tamizaje experimental de Parkinson basado en análisis de voz, capaz de capturar o recibir grabaciones de usuario, aplicar control de calidad, extraer biomarcadores acústicos trazables y utilizarlos como entrada de un modelo de aprendizaje automático bajo una lógica de apoyo académico, no de diagnóstico clínico.

### B. Objetivos Específicos

1. Integrar un flujo de carga, almacenamiento y procesamiento de audios dentro de una arquitectura web.
2. Estandarizar el preprocesamiento de audio para reducir variabilidad por formato, frecuencia de muestreo, canales, duración y silencios.
3. Implementar una compuerta de control de calidad previa a la extracción de biomarcadores y a la inferencia.
4. Generar un vector de características acústicas compatible con el esquema clásico del dataset de Parkinson, registrando explícitamente features faltantes o parciales.
5. Implementar aproximaciones determinísticas iniciales para biomarcadores no lineales como DFA, D2, PPE, RPDE, `spread1` y `spread2`.
6. Persistir los biomarcadores extraídos junto con información de versionamiento del extractor, esquema de características y estado de completitud.
7. Ejecutar una predicción preliminar de Parkinson a partir del vector de biomarcadores, delimitando su alcance como resultado experimental.
8. Identificar limitaciones técnicas, metodológicas y clínicas que deben resolverse antes de cualquier interpretación diagnóstica.

---

## IV. Metodología de Investigación Aplicada

Este trabajo se plantea como una investigación aplicada de desarrollo tecnológico, con enfoque experimental y orientación a validación de pipeline. Su propósito no es demostrar validez clínica final, sino construir una ruta técnica defendible para capturar audio, evaluar su calidad, extraer biomarcadores, registrar trazabilidad e integrar los datos con un modelo predictivo existente.

La metodología se fundamenta en una decisión central: adoptar un enfoque basado en biomarcadores acústicos interpretables antes que un enfoque end-to-end de aprendizaje profundo. Esta decisión responde a cuatro razones. Primero, el modelo histórico de Parkinson espera un vector estructurado de características acústicas. Segundo, los biomarcadores permiten comparar la salida del extractor con literatura previa y herramientas de referencia. Tercero, el proyecto todavía no cuenta con un banco amplio de audios etiquetados, metadatos clínicos y consentimiento para entrenar modelos profundos robustos. Cuarto, en un sistema con implicaciones en salud, la trazabilidad del dato de entrada es tan importante como la métrica de clasificación.

La metodología se organiza en seis momentos:

1. **Revisión del estado técnico:** análisis del funcionamiento anterior de MedDiag, del modelo histórico de Parkinson y de la arquitectura actual de MedDiag2.
2. **Selección del enfoque biomarcador:** adopción de variables acústicas interpretables para mantener compatibilidad con datasets existentes y facilitar auditoría.
3. **Diseño del pipeline de audio:** definición de una secuencia de captura, decodificación, preprocesamiento, control de calidad, extracción de características, persistencia e inferencia.
4. **Implementación progresiva:** incorporación de Feature Store, versionado de extractor, aproximaciones determinísticas de biomarcadores no lineales, reportes de calidad de audio y endpoints de consulta.
5. **Delimitación de alcance:** definición del sistema como tamizaje experimental, no como diagnóstico clínico.
6. **Identificación de brechas:** documentación de riesgos asociados a equivalencia de medidas, ruido, micrófonos, datasets limitados, validación clínica y manejo de features faltantes.

Este enfoque permite que el proyecto avance como prototipo académico sin presentar sus resultados como diagnóstico médico. Además, permite separar el logro de ingeniería —tener un flujo funcional— del reto científico —validar que los biomarcadores extraídos sean equivalentes, estables y clínicamente interpretables.

---

## V. Marco Conceptual

### A. Biomarcadores de Voz en Parkinson

Diversos estudios han explorado la relación entre enfermedad de Parkinson y alteraciones vocales. La hipofonía, la inestabilidad de la frecuencia fundamental y los cambios en la calidad vocal pueden reflejar afectaciones del control motor del habla. Por ello, las grabaciones de vocal sostenida han sido usadas como fuente de características acústicas para modelos de clasificación [1].

El conjunto clásico de Parkinson usado por el proyecto incluye 22 variables, como se muestra en la Tabla I.

| Categoría | Variables |
|-----------|-----------|
| **Frecuencia** | MDVP:Fo(Hz), MDVP:Fhi(Hz), MDVP:Flo(Hz) |
| **Jitter** | MDVP:Jitter(%), MDVP:Jitter(Abs), MDVP:RAP, MDVP:PPQ, Jitter:DDP |
| **Shimmer** | MDVP:Shimmer, MDVP:Shimmer(dB), Shimmer:APQ3, Shimmer:APQ5, MDVP:APQ, Shimmer:DDA |
| **Ruido-armonicidad** | NHR, HNR |
| **No lineales** | RPDE, DFA, spread1, spread2, D2, PPE |

**Tabla I:** Conjunto de 22 biomarcadores acústicos del pipeline de MedDiag2, compatibles con el dataset Oxford Parkinson's Disease Detection.

Estas variables no deben asumirse automáticamente como equivalentes entre herramientas. El valor obtenido depende del algoritmo, de los parámetros de extracción, de la calidad del audio, de la frecuencia de muestreo y de las condiciones de grabación [3].

### B. Jitter, Shimmer y HNR

El jitter representa variaciones ciclo a ciclo de la frecuencia fundamental. El shimmer describe variaciones ciclo a ciclo de la amplitud. El HNR expresa la relación entre componentes armónicos y ruido en la señal de voz [8]. Estas medidas son sensibles a la calidad de la grabación y a la configuración del algoritmo de extracción, por lo que no deben interpretarse de manera aislada ni como equivalentes directos entre herramientas distintas [9].

Praat es una herramienta ampliamente usada para análisis acústico de voz y Parselmouth permite acceder a funcionalidades de Praat desde Python [4], [5]. Por esta razón, Parselmouth/Praat constituye la ruta recomendada para consolidar F0, jitter, shimmer y HNR en el extractor clínico del proyecto.

### C. Biomarcadores No Lineales

Las variables no lineales buscan capturar propiedades complejas de la señal vocal que no siempre son evidentes en medidas lineales tradicionales. En la rama `marcadoresNL`, MedDiag2 implementa:

- **DFA:** analiza fluctuaciones de la señal tras remover tendencias locales.
- **D2:** aproxima la dimensión de correlación mediante una estrategia tipo Grassberger-Procaccia.
- **PPE:** estima la entropía de la distribución del pitch en escala logarítmica.
- **RPDE:** aproxima la entropía de densidad de periodos recurrentes a partir de retardos de recurrencia.
- **`spread1` y `spread2`:** describen desplazamiento y dispersión de la distribución del log-pitch.

Estas variables enriquecen el vector de entrada del modelo, pero en el estado actual deben entenderse como aproximaciones experimentales. Su validación requiere comparar valores frente a implementaciones de referencia y audios controlados. Los estudios sobre análisis no lineal de voz en Parkinson muestran que estas medidas pueden ser útiles, pero también requieren estandarización metodológica y validación cuidadosa [2].

### D. Librosa como Soporte de Procesamiento Digital de Señales

Librosa es una biblioteca de Python ampliamente usada para análisis de audio, carga de señales, extracción espectral y procesamiento digital de señales [6]. En MedDiag2, su papel debe entenderse como soporte de carga, preprocesamiento y análisis auxiliar. No debe presentarse como sustituto clínico directo de Praat para jitter, shimmer o HNR, ya que estas medidas requieren algoritmos y definiciones específicas de perturbación vocal.

---

## VI. Ruta Técnica Actual

La ruta actual se organiza en capas progresivas, como se describe en la Tabla II.

| Capa | Elección actual | Justificación | Riesgo controlado |
|------|----------------|---------------|-------------------|
| Captura de voz | Vocal sostenida, idealmente `/a/` | Reduce variabilidad y facilita perturbaciones de F0 y amplitud | Muestras no comparables |
| Preprocesamiento | Mono, frecuencia de muestreo controlada y decodificación robusta | Estandariza la señal antes de extraer biomarcadores | Sesgos por dispositivo o formato |
| Control de calidad | `AudioQualityReport` con duración, RMS, clipping, SNR, silencio, piso de ruido y ancho de banda | Bloquea o marca señales no aptas antes de biomarcadores | Inferencias sobre audio inválido |
| Extracción base | Librosa, SciPy y Pydub | Carga, compatibilidad y cálculos auxiliares | Fallos de formato o pipeline rígido |
| Extracción clínica recomendada | Parselmouth/Praat | Ruta defendible para F0, jitter, shimmer y HNR | Desviación de medidas vocales |
| Biomarcadores no lineales | Implementaciones determinísticas en `marcadoresNL` | Completa el vector histórico del modelo | Placeholders y variables incompletas |
| Persistencia | Feature Store con versión de extractor y esquema | Permite auditoría y comparación entre corridas | Resultados no trazables |
| Inferencia | Modelo actual de Parkinson | Reutiliza el clasificador disponible | Entrada incompatible con entrenamiento |

**Tabla II:** Organización por capas de la ruta técnica actual de MedDiag2.

La decisión metodológica más importante es separar responsabilidades: el audio no es el centro del sistema; el centro es la confiabilidad del biomarcador que llega al modelo.

---

## VII. Arquitectura del Sistema

MedDiag2 utiliza una arquitectura web dividida en frontend, backend, servicios de procesamiento y persistencia.

### A. Frontend

El frontend está construido en Next.js. Permite autenticación, acceso a rutas privadas, carga de audios y consulta de registros procesados. La aplicación ofrece una interfaz para que el usuario grabe o suba una muestra de voz, revise su estado de procesamiento y consulte los biomarcadores extraídos.

### B. Backend

El backend está construido con FastAPI. Expone los siguientes endpoints REST:

- `POST /audio/upload` — Carga de audio
- `GET /audio/me` — Listar audios del usuario
- `GET /audio/{audio_id}` — Consultar un audio específico
- `POST /audio/{audio_id}/process` — Procesar un audio
- `GET /audio/{audio_id}/features` — Obtener biomarcadores
- `GET /audio/{audio_id}/quality` — Consultar el último reporte de calidad del audio
- `POST /audio/{audio_id}/quality/check` — Ejecutar o repetir control de calidad de audio
- `POST /audio/batch-process` — Procesar lotes de audios
- `GET /audio/analysis/summary` — Resumen de análisis

### C. Almacenamiento y Trazabilidad

El sistema guarda los archivos de audio en un backend de almacenamiento configurable y registra metadatos en base de datos. Cada audio conserva información como usuario, nombre original, tipo MIME, tamaño, ruta de almacenamiento, estado de procesamiento, notas y marcas temporales.

Además, la entidad `BiomarkerFeature` permite almacenar el conjunto de biomarcadores asociado a un audio, junto con:

- `extractor_version`;
- `feature_schema_version`;
- `features_json`;
- `missing_features_json`;
- `is_partial`.

Esta separación permite auditar los resultados y comparar versiones del extractor.

La versión actual también incorpora la entidad `AudioQualityReport`, asociada a cada registro de audio. Esta tabla almacena el veredicto de calidad (`is_valid`), la puntuación (`quality_score`), la razón de rechazo y métricas de señal como duración, energía RMS, amplitud pico, recorte, SNR, proporción de silencio, piso de ruido y ancho de banda. Con ello, el sistema deja de tratar la calidad del audio como una advertencia documental y la convierte en un artefacto persistido y consultable.

---

## VIII. Funcionamiento del Módulo de Análisis de Voz

### A. Carga del Audio

El usuario envía un archivo de audio al endpoint de carga. El sistema valida tipo y tamaño, guarda el archivo en almacenamiento y crea un registro en base de datos. Luego marca el audio como `processing` y ejecuta el procesamiento en segundo plano.

### B. Decodificación

El servicio de procesamiento intenta cargar el audio con Librosa. Si la decodificación falla y Pydub está disponible, utiliza Pydub como mecanismo alternativo. El sistema exige una duración mínima de 0.5 segundos para evitar procesar muestras demasiado cortas.

### C. Control de Calidad de Audio

Antes de extraer biomarcadores, el pipeline ejecuta una compuerta de control de calidad. Este módulo carga el audio desde almacenamiento, lo decodifica y calcula métricas de validez de señal. La implementación actual usa umbrales sobre duración mínima, razón de recorte, energía RMS, proporción de silencio y relación señal-ruido. También estima piso de ruido y ancho de banda ocupado.

El resultado se persiste como `AudioQualityReport`. Si el audio supera el control, el estado del registro puede avanzar a `quality_checked` y continuar hacia biomarcadores. Si falla, se marca como `rejected` y se registra una explicación, por ejemplo duración insuficiente, saturación, baja energía, exceso de silencio o SNR deficiente. Esta compuerta evita que el modelo reciba vectores derivados de señales degradadas.

### D. Extracción de Frecuencia Fundamental

La frecuencia fundamental se estima usando una estrategia escalonada:

1. `librosa.pyin` como método principal;
2. Parselmouth/Praat como alternativa si no se obtiene F0;
3. autocorrelación con SciPy como fallback.

A partir de F0 se calculan frecuencia mediana, máxima y mínima.

### E. Extracción de Biomarcadores

El extractor calcula o aproxima:

- jitter y medidas derivadas: RAP, PPQ y DDP;
- shimmer y medidas derivadas: APQ3, APQ5, APQ y DDA;
- NHR y HNR mediante una aproximación cepstral;
- biomarcadores no lineales: DFA, D2, PPE, RPDE, `spread1` y `spread2`.

Cuando una característica no puede calcularse por insuficiencia de datos o condiciones inválidas, el uso de `0.0` mantiene la compatibilidad técnica del vector de entrada. No obstante, esta decisión debe considerarse una solución transitoria. La ruta recomendada es registrar la variable en `missing_features_json`, marcar el conjunto como `is_partial = true` y decidir si se rechaza la muestra, se solicita nueva grabación o se ejecuta una inferencia explícitamente marcada como parcial.

### F. Inferencia Preliminar

Una vez generado el vector de biomarcadores, el pipeline valida que las características esperadas estén presentes y sean finitas. Luego invoca el modelo de Parkinson y crea un registro de diagnóstico preliminar con probabilidad asociada. El resultado se expresa como orientación experimental, no como diagnóstico médico.

---

## IX. Avances Implementados

### A. Extracción de Biomarcadores No Lineales

La rama `marcadoresNL` implementa funciones determinísticas para:

- `compute_dfa`;
- `compute_d2`;
- `compute_ppe`;
- `compute_rpde`;
- `compute_spread_features`.

Este avance permite que el sistema calcule o aproxime los seis biomarcadores no lineales esperados por el esquema de Parkinson, en lugar de depender únicamente de valores por defecto o placeholders aleatorios.

### B. Mayor Trazabilidad

El sistema persiste los biomarcadores en una entidad específica de base de datos. Cada conjunto de características queda asociado al audio procesado, a la versión del extractor y a la versión del esquema. Esto facilita auditoría, reproducción de resultados y comparación entre iteraciones.

### C. Control de Calidad de Audio

Se implementó un servicio dedicado de control de calidad que analiza la señal antes de la extracción de biomarcadores. El servicio calcula duración, energía RMS, amplitud pico, razón de recorte, SNR estimada, proporción de silencio, piso de ruido y ancho de banda. Estos resultados se guardan en `audio_quality_reports` mediante la migración `004_create_audio_quality_reports.py`.

Esta funcionalidad actualiza el flujo metodológico del proyecto: el audio ya no pasa directamente de carga a biomarcadores, sino que primero debe superar una etapa de QA/QC. Si el audio no cumple las condiciones mínimas, el sistema registra el motivo y evita continuar con una inferencia ordinaria. Esta decisión es relevante para el paper porque convierte una limitación reconocida en una funcionalidad implementada.

### D. Integración con Flujo de Usuario

El procesamiento de audio está integrado con endpoints protegidos por autenticación. Cada usuario puede cargar, listar y consultar sus propios audios. El sistema contempla control de acceso para que solo el propietario o un administrador puedan ver registros específicos.

### E. Procesamiento Asincrónico

Después de la carga, el audio se procesa en segundo plano. Esto mejora la experiencia de usuario, ya que la solicitud de carga no queda bloqueada hasta que termine la extracción de biomarcadores.

### F. Compatibilidad con el Modelo Existente

El pipeline conserva el esquema de 22 variables del modelo de Parkinson ya entrenado. Esto permite reutilizar el modelo actual mientras se mejora progresivamente la calidad de la extracción. Sin embargo, esta compatibilidad no debe confundirse con validación clínica. El modelo solo será metodológicamente más confiable cuando las características que recibe provengan de un extractor congelado, documentado y validado experimentalmente.

---

## X. Datasets para Fortalecimiento del Modelo y Validación Externa

El dataset clásico de Parkinson utilizado en múltiples trabajos de machine learning constituye una línea base útil para reproducir el modelo histórico de MedDiag2, pero no debe ser el único soporte empírico del proyecto. Su tamaño reducido, su dependencia de biomarcadores ya extraídos y la ausencia de audio crudo en su uso más frecuente limitan la posibilidad de validar el pipeline completo de captura, preprocesamiento, extracción y control de calidad.

Por esta razón, MedDiag2 debe incorporar una estrategia progresiva de evaluación con datasets más pertinentes. En el contexto colombiano, PC-GITA representa una alternativa especialmente relevante porque fue construido con hablantes nativos de español colombiano, incluyendo 50 pacientes con Parkinson y 50 controles sanos emparejados por edad y género [11]. Este corpus permitiría evaluar vocal sostenida, palabras, frases, lectura y habla continua en una población lingüísticamente cercana al contexto de uso del proyecto.

Como complemento, NeuroVoz constituye una opción importante para evaluar generalización en otra variante del español. Este corpus incluye hablantes nativos de español castellano, con pacientes de Parkinson y controles sanos, y contiene tareas de fonación sostenida, pruebas diadococinéticas, frases y monólogos [12]. La combinación de PC-GITA y NeuroVoz permitiría discutir la estabilidad de los biomarcadores entre variantes del español y fortalecer la validez externa del sistema.

Finalmente, datasets de mayor escala como mPower pueden reservarse para una fase avanzada, especialmente orientada a robustez frente a audio de smartphone, ruido ambiental y modelos basados en embeddings [13]. Sin embargo, por su heterogeneidad y complejidad de curaduría, no deberían desplazar en la fase actual a corpus más controlados y lingüísticamente pertinentes.

| Dataset | Utilidad para MedDiag2 | Ventaja principal | Limitación |
|---------|------------------------|-------------------|------------|
| UCI Parkinson clásico | Línea base histórica | Compatible con el modelo actual de 22 variables | Tamaño reducido y uso habitual sin audio crudo |
| UCI Multiple Audio | Prueba intermedia de tareas vocales | Incluye distintos tipos de grabación | Pocos sujetos |
| PC-GITA | Validación contextual para Colombia | Español colombiano, pacientes y controles | Puede requerir acceso académico |
| NeuroVoz | Validación externa en español | Corpus reciente en español castellano | Variante lingüística diferente a Colombia |
| mPower | Robustez y audio móvil | Gran volumen de datos | Alta heterogeneidad y curaduría exigente |

**Tabla III:** Datasets considerados para validación externa del pipeline de MedDiag2.

---

## XI. Modelos Actuales y Modelos por Explorar

El modelo histórico de Parkinson condiciona el pipeline porque espera un vector de 22 características. Sin embargo, la compatibilidad dimensional del vector no garantiza por sí sola validez predictiva. Para que la inferencia sea metodológicamente defendible, las características extraídas en producción deben provenir de un extractor documentado, versionado y validado. Por ello, la comparación de modelos no debe centrarse únicamente en accuracy, sino en sensibilidad, F1-score, AUC, calibración, matriz de confusión, estabilidad entre repeticiones y desempeño en validación externa.

Dado que MedDiag2 utiliza modelos predictivos con posible interpretación en salud, su evolución debe alinearse progresivamente con guías de reporte y evaluación de riesgo de sesgo. TRIPOD+AI ofrece recomendaciones para reportar modelos predictivos desarrollados con regresión o aprendizaje automático [14], mientras que PROBAST+AI permite evaluar calidad, aplicabilidad y riesgo de sesgo en modelos predictivos con inteligencia artificial [15]. Estas guías no obligan a que MedDiag2 demuestre validez clínica en esta fase académica, pero sí ofrecen un marco para reportar con transparencia datos, predictores, partición de muestras, métricas, calibración, limitaciones y alcance del modelo.

| Métrica | Uso en MedDiag2 | Justificación |
|---------|-----------------|---------------|
| Recall / sensibilidad | Prioritaria | En tamizaje interesa reducir falsos negativos |
| F1-score | Comparación balanceada | Útil si hay desbalance de clases |
| AUC-ROC | Discriminación global | Evalúa separación entre clases |
| Matriz de confusión | Interpretación de errores | Permite observar falsos positivos y falsos negativos |
| Calibración | Interpretación de probabilidades | Evita tratar probabilidades mal calibradas como riesgo clínico real |
| Validación cruzada | Estabilidad interna | Reduce dependencia de una sola partición |
| Validación externa | Generalización | Evalúa desempeño en datasets distintos |

**Tabla IV:** Métricas recomendadas para evaluación de modelos en MedDiag2.

La Tabla V presenta los modelos considerados para el pipeline.

| Tipo de modelo | Estado en MedDiag2 | Ventaja principal | Riesgo o limitación |
|----------------|---------------------|-------------------|---------------------|
| Modelo histórico de Parkinson | En uso | Compatible con el vector de 22 características | Depende de la equivalencia entre dataset original y features extraídas actualmente |
| Random Forest | A evaluar | Robusto, útil para datos tabulares, permite estimar importancia de variables | Puede sobreajustar datasets pequeños |
| SVM | A evaluar | Buen desempeño en espacios de alta dimensión | Sensible al escalamiento y a la selección del kernel |
| Logistic Regression | Línea base recomendada | Interpretable y útil como comparación mínima | Menor capacidad para relaciones no lineales |
| XGBoost | A explorar | Alto rendimiento en datos tabulares | Riesgo de sobreajuste y menor interpretabilidad directa |
| Wav2Vec2 / HuBERT / WavLM | Futuro | Aprende representaciones directamente desde audio | Requiere muchos datos etiquetados, mayor costo computacional y menor trazabilidad |

**Tabla V:** Comparación de modelos considerados para el pipeline de MedDiag2.

La decisión de no iniciar con deep learning end-to-end no debe interpretarse como una renuncia tecnológica. En esta fase, el proyecto no cuenta con un banco amplio de audios etiquetados, consentimiento, metadatos clínicos y control de sesgos. Por ello, un enfoque profundo podría producir resultados aparentemente altos sin trazabilidad suficiente. En cambio, el enfoque biomarcador permite explicar qué variables alimentan el modelo, comparar valores entre extractores y detectar errores de señal.

---

## XI. Hallazgos Técnicos

1. **La aplicación evolucionó de diagnóstico general a laboratorio de voz.** Aunque MedDiag nació como sistema de apoyo diagnóstico para varias enfermedades, el componente más novedoso en MedDiag2 es el módulo de Parkinson por voz.
2. **El vector del modelo condiciona el pipeline.** El modelo actual exige 22 características, lo que obliga a producir, marcar o rechazar todas las variables esperadas.
3. **Las variables no lineales son el principal punto de avance.** La rama `marcadoresNL` reduce una debilidad de versiones anteriores al calcular RPDE, DFA, D2, PPE, `spread1` y `spread2` mediante aproximaciones determinísticas.
4. **Parselmouth sigue siendo una ruta metodológica recomendada.** Aunque el pipeline actual usa Librosa como ruta principal para F0 y cálculos propios para varios biomarcadores, Parselmouth/Praat debe fortalecerse para jitter, shimmer y HNR [4].
5. **La calidad del audio es determinante.** Grabaciones cortas, ruidosas, saturadas o con poca fonación pueden producir valores poco confiables.
6. **La inferencia ahora depende del estado de calidad.** La versión actual implementa una compuerta QA/QC que persiste reportes y puede rechazar audios antes de calcular biomarcadores.
7. **La trazabilidad se amplió de biomarcadores a calidad de señal.** El proyecto ya no solo guarda el vector de features; también registra las condiciones bajo las cuales ese vector fue obtenido.

---

## XII. Resultados del Desarrollo

Como resultado de esta fase, MedDiag2 cuenta con un flujo funcional para analizar audios de voz en el contexto de tamizaje experimental de Parkinson. Los principales resultados son:

1. Endpoint de carga de audio con validación básica.
2. Almacenamiento de archivos y metadatos.
3. Procesamiento de audio en segundo plano.
4. Generación de un vector de 22 características compatible con el modelo histórico de Parkinson.
5. Implementación de biomarcadores no lineales en la rama `marcadoresNL`.
6. Persistencia versionada de conjuntos de biomarcadores.
7. Implementación de tabla `audio_quality_reports` y modelo `AudioQualityReport`.
8. Servicio de control de calidad con métricas de señal y veredicto `is_valid`.
9. Endpoints para consultar y ejecutar control de calidad por audio.
10. Endpoint de consulta de características extraídas.
11. Generación de predicción preliminar con probabilidad.
12. Documentación técnica sobre librerías, riesgos y ruta de investigación.

El proyecto también conserva modelos previamente entrenados para diabetes y enfermedad cardiovascular, pero el aporte principal de esta iteración corresponde al fortalecimiento del módulo de Parkinson por voz.

---

## XIII. Discusión

MedDiag2 demuestra que es posible integrar en una aplicación web un flujo completo de análisis de voz: captura, almacenamiento, control de calidad, extracción de biomarcadores, inferencia y visualización de resultados. Este logro es relevante desde el punto de vista académico porque combina ingeniería de software, ciencia de datos, procesamiento digital de señales y salud digital.

Sin embargo, el valor del prototipo no debe medirse solamente por la existencia de una predicción. El aspecto más importante es la trazabilidad del proceso. En aplicaciones de inteligencia artificial en salud, una predicción sin control sobre los datos de entrada y sin conocimiento de las características usadas puede generar interpretaciones erróneas. La incorporación de QA/QC fortalece esta trazabilidad, porque permite diferenciar entre un audio apto para análisis, un audio rechazado y un conjunto de biomarcadores potencialmente parcial.

La implementación de biomarcadores no lineales mejora la coherencia entre el modelo entrenado y el pipeline de inferencia. No obstante, las fórmulas actuales deben considerarse aproximaciones prácticas. La validación científica exigiría comparar sus salidas con herramientas de referencia, utilizar audios controlados y evaluar estabilidad intra-sujeto e inter-sujeto.

La decisión de no iniciar con deep learning end-to-end no es una renuncia tecnológica, sino una decisión metodológica. En ausencia de un banco amplio de audios etiquetados, con consentimiento, metadatos clínicos y control de sesgos, un modelo profundo puede ofrecer buen desempeño aparente sin trazabilidad suficiente. En cambio, un extractor basado en biomarcadores permite comparar valores, detectar errores, explicar inferencias y justificar ajustes del modelo.

---

## XIV. Limitaciones

1. **No es diagnóstico clínico:** MedDiag2 solo entrega una estimación preliminar de riesgo y no reemplaza evaluación neurológica, fonoaudiológica ni médica.
2. **Dataset histórico limitado:** el modelo actual se apoya en un dataset público pequeño, útil como línea base, pero insuficiente para afirmar generalización clínica [7].
3. **Diferencia entre entrenamiento y producción:** el modelo fue entrenado con variables ya extraídas, mientras que MedDiag2 produce esas variables desde audio real capturado en condiciones variables.
4. **Sensibilidad al audio:** ruido, micrófono, distancia, intensidad vocal, duración y estabilidad de la fonación afectan los biomarcadores.
5. **Equivalencia no garantizada entre herramientas:** jitter, shimmer, HNR y otras medidas pueden variar según software, configuración y método de extracción.
6. **Biomarcadores no lineales en etapa experimental:** aunque ahora son determinísticos, requieren comparación con referencias y validación de estabilidad.
7. **Valores por defecto y features parciales:** el uso de `0.0` para completar variables faltantes debe eliminarse o restringirse a ejecuciones marcadas explícitamente como parciales.
8. **Control de calidad heurístico:** los umbrales actuales de QA/QC deben validarse con audios controlados, distintos micrófonos y escenarios reales.
9. **Falta de validación externa:** aún se requiere probar el modelo en datasets diferentes, idealmente PC-GITA, NeuroVoz u otros corpus con audio crudo.
10. **Riesgo de sobreinterpretación:** el usuario podría interpretar una probabilidad experimental como diagnóstico si la interfaz no comunica claramente el alcance.

---

## XV. Recomendaciones y Trabajo Futuro

1. Consolidar Parselmouth/Praat como extractor principal para F0, jitter, shimmer y HNR.
2. Mantener Librosa como soporte de carga, preprocesamiento, análisis espectral y validaciones auxiliares.
3. Validar experimentalmente los umbrales del módulo de control de calidad.
4. Eliminar la imputación silenciosa con `0.0` y usar `missing_features_json`, `is_partial` y estados explícitos de features parciales.
5. Diseñar una batería experimental con vocal sostenida `/a/`, duración de 3 a 5 segundos, tres repeticiones por sujeto y condiciones controladas de ruido.
6. Comparar Parselmouth, openSMILE [16], DisVoice y Librosa/SciPy en términos de completitud, estabilidad, tiempo de procesamiento, errores y plausibilidad fisiológica.
7. Incorporar PC-GITA como dataset prioritario de validación contextual para población colombiana.
8. Incorporar NeuroVoz como dataset externo en español para evaluar generalización lingüística.
9. Reentrenar o calibrar modelos solo con features realmente medidas por el pipeline definitivo.
10. Evaluar Random Forest, SVM, Logistic Regression y XGBoost bajo validación cruzada y validación externa.
11. Reportar futuros modelos siguiendo criterios de TRIPOD+AI y evaluar riesgo de sesgo con PROBAST+AI.
12. Explorar Wav2Vec2, HuBERT o WavLM solo cuando exista un banco suficiente de audios etiquetados y controlados.
13. Incorporar en la interfaz mensajes claros cuando un audio sea rechazado y recomendaciones para repetir la grabación.
14. Mantener consentimiento informado y advertencia visible de uso experimental.

---

## XVI. Conclusiones

MedDiag2 puede consolidarse como una herramienta de tamizaje experimental basada en voz, no como un sistema de diagnóstico clínico. La ruta actual es adecuada porque prioriza control de calidad, extracción reproducible de biomarcadores, versionado de features, trazabilidad de inferencia y validación comparativa.

La rama `marcadoresNL` representa un avance significativo porque implementa biomarcadores no lineales que completan el vector requerido por el modelo de Parkinson mediante aproximaciones determinísticas. La incorporación posterior de QA/QC amplía ese avance al impedir que señales de baja calidad sean tratadas como entradas equivalentes a audios técnicamente aptos. En conjunto, biomarcadores no lineales, Feature Store y reportes de calidad convierten el sistema en una base de investigación más sólida, siempre que se mantenga una postura crítica frente a la calidad de los datos, la equivalencia de las medidas acústicas y la necesidad de validación médica.

En síntesis, MedDiag2 avanza desde un MVP de predicción médica general hacia una plataforma experimental especializada, centrada en biomarcadores de voz para Parkinson. Su estado actual es adecuado para una entrega académica de desarrollo e investigación aplicada, y ofrece una base clara para futuras mejoras metodológicas, clínicas y técnicas.

---

## Apéndice

### Glosario de Términos Técnicos

| Término | Definición |
|---------|------------|
| **F0** | Frecuencia fundamental de la voz |
| **Jitter** | Variación ciclo a ciclo de la frecuencia fundamental |
| **Shimmer** | Variación ciclo a ciclo de la amplitud |
| **HNR** | Relación armónico-ruido (*Harmonics-to-Noise Ratio*) |
| **NHR** | Relación ruido-armónico (*Noise-to-Harmonics Ratio*) |
| **DFA** | Análisis de fluctuaciones sin tendencia (*Detrended Fluctuation Analysis*) |
| **D2** | Dimensión de correlación |
| **PPE** | Entropía de distribución del pitch (*Pitch Period Entropy*) |
| **RPDE** | Entropía de densidad de periodos recurrentes (*Recurrence Period Density Entropy*) |
| **MDVP** | *Multi-Dimensional Voice Program* (software de análisis acústico) |
| **Parselmouth** | Interfaz de Python para acceder a funcionalidades de Praat |

---

## Agradecimientos

Los autores agradecen a Sandra Patricia Zabala Orrego, docente asesora del curso Proyecto Integrador, por su orientación y revisión del trabajo. Asimismo, agradecen a la Universidad por proporcionar el espacio académico para el desarrollo de esta investigación aplicada.

---

## Referencias

[1] M. A. Little, P. E. McSharry, E. J. Hunter, J. Spielman, and L. O. Ramig, "Suitability of dysphonia measurements for telemonitoring of Parkinson's disease," *IEEE Transactions on Biomedical Engineering*, vol. 56, no. 4, pp. 1015–1022, 2009. DOI: 10.1109/TBME.2008.2005954

[2] A. Tsanas, M. A. Little, P. E. McSharry, and L. O. Ramig, "Nonlinear speech analysis algorithms mapped to a standard metric achieve clinically useful quantification of average Parkinson's disease symptom severity," *Journal of the Royal Society Interface*, vol. 8, no. 59, pp. 842–855, 2011. DOI: 10.1098/rsif.2010.0456

[3] D. D. Deliyski, H. S. Shaw, and M. K. Evans, "Influence of sampling rate on accuracy and reliability of acoustic voice analysis," *Logopedics Phoniatrics Vocology*, vol. 30, no. 2, pp. 55–62, 2005.

[4] Y. Jadoul, B. Thompson, and B. de Boer, "Introducing Parselmouth: A Python interface to Praat," *Journal of Phonetics*, vol. 71, pp. 1–15, 2018. DOI: 10.1016/j.wocn.2018.07.001

[5] P. Boersma and D. Weenink, "Praat: Doing phonetics by computer" [Computer program], 2024. [Online]. Available: https://www.praat.org/

[6] B. McFee, C. Raffel, D. Liang, D. P. W. Ellis, M. McVicar, E. Battenberg, and O. Nieto, "librosa: Audio and music signal analysis in Python," in *Proc. 14th Python in Science Conf. (SciPy 2015)*, 2015, pp. 18–25.

[7] UCI Machine Learning Repository, "Oxford Parkinson's Disease Detection Dataset." [Online]. Available: https://archive.ics.uci.edu/ml/datasets/Parkinsons

[8] P. Boersma, "Accurate short-term analysis of the fundamental frequency and the harmonics-to-noise ratio of a sampled sound," in *Proc. Institute of Phonetic Sciences*, vol. 17, 1993, pp. 97–110.

[9] Y. Maryn, P. Corthals, M. De Bodt, P. Van Cauwenberge, and D. Deliyski, "Toward improved ecological validity in the acoustic measurement of overall voice quality: Combining continuous speech and sustained vowels," *Journal of Voice*, vol. 24, no. 5, pp. 540–555, 2010.

[10] Documentación interna del proyecto MedDiag2. *README.md, INVESTIGACION_BIOMARCADORES_VOZ_PARKINSON.markdown.md, DEPLOY.md y código fuente de la rama marcadoresNL*, 2026.

[11] J. R. Orozco-Arroyave, J. D. Arias-Londoño, J. F. Vargas-Bonilla, M. C. González-Rátiva, and E. Nöth, "New Spanish speech corpus database for the analysis of people suffering from Parkinson's disease," in *Proc. Ninth Int. Conf. Language Resources and Evaluation (LREC)*, 2014, pp. 342–347.

[12] J. Mendes-Laureano et al., "NeuroVoz: a Castillian Spanish corpus of parkinsonian speech," *Scientific Data*, vol. 11, 2024.

[13] B. M. Bot et al., "The mPower study, Parkinson disease mobile data collected using ResearchKit," *Scientific Data*, vol. 3, 160011, 2016.

[14] G. S. Collins et al., "TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regression or machine learning methods," *BMJ*, vol. 385, e078378, 2024.

[15] K. G. M. Moons et al., "PROBAST+AI: an updated quality, risk of bias, and applicability assessment tool for prediction models using regression or artificial intelligence methods," *BMJ*, vol. 388, e082505, 2025.

[16] F. Eyben et al., "The Geneva Minimalistic Acoustic Parameter Set (GeMAPS) for voice research and affective computing," *IEEE Trans. Affective Computing*, vol. 7, no. 2, pp. 190–202, 2016.

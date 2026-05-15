> **Documento formato IEEE — Versión 1.0**
> *Este documento sigue el estilo de las transacciones IEEE (IEEEtran.cls).*

# MedDiag2: Tamizaje Experimental de Parkinson Mediante Análisis de Voz y Biomarcadores Acústicos

Adrián Espinosa, *Student Member, IEEE*, Diana Huertas, *Student Member, IEEE*,
and David Ríos, *Student Member, IEEE*

---

**Abstract—** MedDiag2 evoluciona desde un prototipo de apoyo diagnóstico basado en variables clínicas ingresadas manualmente hacia una plataforma de tamizaje experimental centrada en voz sostenida, control de calidad, extracción de biomarcadores acústicos y trazabilidad de inferencia. El proyecto integra una aplicación web, un backend en FastAPI, almacenamiento de audios, modelos de aprendizaje automático y un pipeline de procesamiento digital de señales orientado al análisis preliminar de patrones asociados a la enfermedad de Parkinson. La ruta técnica actual conserva un enfoque basado en biomarcadores interpretables. Este enfoque se justifica porque el modelo histórico de Parkinson fue entrenado con variables acústicas estructuradas, no con audio crudo. Por ello, el reto principal no consiste solamente en recibir archivos de audio desde el usuario, sino en garantizar que las características extraídas sean comparables, reproducibles, auditables y metodológicamente defendibles. En la rama `marcadoresNL`, MedDiag2 implementa aproximaciones determinísticas para biomarcadores no lineales como DFA, D2, PPE, RPDE, `spread1` y `spread2`. Este avance reduce la dependencia de placeholders aleatorios utilizados en versiones anteriores. El documento sostiene que, en esta fase, MedDiag2 debe priorizar reproducibilidad, equivalencia de características, control de calidad y trazabilidad antes que complejidad de infraestructura o modelos de caja negra. MedDiag2 se define expresamente como una herramienta académica de apoyo y tamizaje experimental, no como un sistema de diagnóstico clínico.

**Index Terms—** Parkinson, biomarcadores de voz, FastAPI, Parselmouth, Praat, Librosa, aprendizaje automático, procesamiento digital de señales, tamizaje experimental.

---

*Manuscript received May 15, 2026; revised July 20, 2026. This work was supported by the Universidad — Proyecto Integrador, Ingeniería de Sistemas.*
*A. Espinosa, D. Huertas, and D. Ríos are with the Facultad de Ingeniería, Universidad, Colombia (e-mail: {adrian.espinosa, diana.huertas, david.rios}@meddiag2.edu.co).*


---

## I. Introducción

L a enfermedad de Parkinson puede producir alteraciones vocales relacionadas con hipofonía, inestabilidad de la fonación, variación de frecuencia fundamental, perturbaciones de amplitud y cambios en la relación armónico-ruido. Debido a ello, diversos estudios han explorado el uso de medidas acústicas como F0, jitter, shimmer, HNR, NHR, RPDE, DFA, D2 y PPE para construir modelos de clasificación, seguimiento o telemonitoreo de síntomas asociados a Parkinson [1], [2].

En MedDiag2, este enfoque resulta pertinente porque el modelo histórico de Parkinson fue entrenado sobre variables biomédicas de voz y no sobre audio crudo. Por esta razón, la evolución del proyecto no debe entenderse como una simple mejora de interfaz para recibir archivos de audio, sino como una reorganización metodológica alrededor del ciclo completo del biomarcador: captura, preprocesamiento, control de calidad, extracción, persistencia versionada, inferencia y auditoría.

La selección de una ruta basada en biomarcadores interpretables permite mantener trazabilidad sobre las variables que alimentan el modelo, facilita la comparación con datasets clásicos y evita depender prematuramente de enfoques de aprendizaje profundo que requieren grandes volúmenes de audio etiquetado, control de sesgos y validación clínica robusta. En esta etapa, el proyecto prioriza coherencia entre datos de entrenamiento, extracción en producción y explicación técnica del resultado.

El objetivo de este documento es justificar la ruta técnica actual de MedDiag2, describir su funcionamiento, presentar los avances implementados y delimitar sus limitaciones. El documento se fundamenta en la documentación interna del proyecto, en el análisis del código de la rama `marcadoresNL` y en referencias científicas sobre análisis de voz en Parkinson.

---

## II. Planteamiento del Problema

La versión inicial de MedDiag funcionaba como una aplicación cliente-servidor con frontend, backend FastAPI y modelos serializados. Para Parkinson, el sistema recibía un vector de biomarcadores acústicos ya calculados: frecuencia fundamental, jitter, shimmer, HNR y parámetros no lineales, entre otros. Esta arquitectura era suficiente para probar integración de software, pero dejaba abierto el problema crítico de cómo obtener esos biomarcadores desde audio real.

En la evolución de MedDiag2 se identificaron tres riesgos principales:

1. **Ruptura entre entrenamiento e inferencia:** el modelo fue entrenado con variables estructuradas, pero en producción puede recibir valores calculados por métodos diferentes o bajo condiciones de audio no controladas.
2. **Uso de aproximaciones o placeholders:** algunas variables, especialmente las no lineales, no estaban calculadas de forma reproducible en versiones anteriores.
3. **Imputación silenciosa de valores `0.0`:** el sistema podía generar inferencias numéricamente válidas, pero biomédicamente discutibles, si completaba variables faltantes con ceros sin reportarlo.

Por tanto, la pregunta técnica central no es solo qué modelo clasifica mejor en un dataset controlado, sino qué ruta garantiza que los datos que alimentan el modelo sean comparables, auditables y reproducibles.

---

## III. Objetivos

### A. Objetivo General

Desarrollar y documentar un prototipo web de tamizaje experimental de Parkinson basado en análisis de voz, capaz de extraer biomarcadores acústicos desde grabaciones de usuario y utilizarlos como entrada para un modelo de aprendizaje automático.

### B. Objetivos Específicos

1. Integrar un flujo de carga, almacenamiento y procesamiento de audios dentro de una arquitectura web.
2. Generar un vector de características acústicas compatible con el esquema clásico del dataset de Parkinson.
3. Implementar aproximaciones determinísticas para biomarcadores no lineales como DFA, D2, PPE, RPDE, `spread1` y `spread2`.
4. Persistir los biomarcadores extraídos junto con información de versionamiento del extractor y del esquema de características.
5. Generar una predicción preliminar de Parkinson a partir del vector de biomarcadores.
6. Identificar limitaciones técnicas, metodológicas y clínicas que deben considerarse antes de interpretar los resultados.

---

## IV. Metodología de Investigación Aplicada

Este trabajo se plantea como una investigación aplicada de desarrollo tecnológico, con enfoque experimental y orientación a validación de pipeline. El propósito no es demostrar validez clínica final, sino construir una ruta técnica defendible para capturar audio, procesarlo, extraer biomarcadores, registrar trazabilidad e integrar los datos con un modelo predictivo existente.

La metodología se organiza en cinco momentos:

1. **Revisión del estado técnico del proyecto:** análisis del funcionamiento anterior de MedDiag, del modelo histórico de Parkinson y de la arquitectura actual de MedDiag2.
2. **Selección de enfoque biomarcador:** adopción de un enfoque basado en variables acústicas interpretables, en lugar de modelos end-to-end, por su mayor trazabilidad y compatibilidad con datasets existentes.
3. **Diseño del pipeline de audio:** definición de una secuencia mínima de captura, decodificación, preprocesamiento, extracción de características, persistencia e inferencia.
4. **Implementación progresiva:** incorporación de Feature Store, versionado de extractor, aproximaciones determinísticas de biomarcadores no lineales y endpoints de consulta.
5. **Identificación de brechas:** documentación de riesgos asociados a calidad del audio, equivalencia de medidas, uso transitorio de `0.0`, falta de validación clínica y necesidad de comparación con herramientas de referencia.

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

El jitter representa variaciones ciclo a ciclo de la frecuencia fundamental. El shimmer describe variaciones ciclo a ciclo de la amplitud. El HNR expresa la relación entre componentes armónicos y ruido en la señal de voz. Estas medidas son sensibles a la calidad de la grabación y a la configuración del algoritmo de extracción, por lo que no deben interpretarse de manera aislada ni como equivalentes directos entre herramientas distintas.

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

---

## VIII. Funcionamiento del Módulo de Análisis de Voz

### A. Carga del Audio

El usuario envía un archivo de audio al endpoint de carga. El sistema valida tipo y tamaño, guarda el archivo en almacenamiento y crea un registro en base de datos. Luego marca el audio como `processing` y ejecuta el procesamiento en segundo plano.

### B. Decodificación

El servicio de procesamiento intenta cargar el audio con Librosa. Si la decodificación falla y Pydub está disponible, utiliza Pydub como mecanismo alternativo. El sistema exige una duración mínima de 0.5 segundos para evitar procesar muestras demasiado cortas.

### C. Extracción de Frecuencia Fundamental

La frecuencia fundamental se estima usando una estrategia escalonada:

1. `librosa.pyin` como método principal;
2. Parselmouth/Praat como alternativa si no se obtiene F0;
3. autocorrelación con SciPy como fallback.

A partir de F0 se calculan frecuencia mediana, máxima y mínima.

### D. Extracción de Biomarcadores

El extractor calcula o aproxima:

- jitter y medidas derivadas: RAP, PPQ y DDP;
- shimmer y medidas derivadas: APQ3, APQ5, APQ y DDA;
- NHR y HNR mediante una aproximación cepstral;
- biomarcadores no lineales: DFA, D2, PPE, RPDE, `spread1` y `spread2`.

Cuando una característica no puede calcularse por insuficiencia de datos o condiciones inválidas, el uso de `0.0` mantiene la compatibilidad técnica del vector de entrada. No obstante, esta decisión debe considerarse una solución transitoria. La ruta recomendada es registrar la variable en `missing_features_json`, marcar el conjunto como `is_partial = true` y decidir si se rechaza la muestra, se solicita nueva grabación o se ejecuta una inferencia explícitamente marcada como parcial.

### E. Inferencia Preliminar

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

### C. Integración con Flujo de Usuario

El procesamiento de audio está integrado con endpoints protegidos por autenticación. Cada usuario puede cargar, listar y consultar sus propios audios. El sistema contempla control de acceso para que solo el propietario o un administrador puedan ver registros específicos.

### D. Procesamiento Asincrónico

Después de la carga, el audio se procesa en segundo plano. Esto mejora la experiencia de usuario, ya que la solicitud de carga no queda bloqueada hasta que termine la extracción de biomarcadores.

### E. Compatibilidad con el Modelo Existente

El pipeline conserva el esquema de 22 variables del modelo de Parkinson ya entrenado. Esto permite reutilizar el modelo actual mientras se mejora progresivamente la calidad de la extracción. Sin embargo, esta compatibilidad no debe confundirse con validación clínica. El modelo solo será metodológicamente más confiable cuando las características que recibe provengan de un extractor congelado, documentado y validado experimentalmente.

---

## X. Modelos Actuales y Modelos por Explorar

El modelo histórico de Parkinson condiciona el pipeline porque espera un vector de 22 características. Sin embargo, MedDiag2 debe comparar progresivamente otros modelos para determinar cuál ofrece mejor balance entre desempeño, interpretabilidad, estabilidad y riesgo de sobreajuste. La Tabla III presenta los modelos considerados.

| Tipo de modelo | Estado en MedDiag2 | Ventaja principal | Riesgo o limitación |
|----------------|---------------------|-------------------|---------------------|
| Modelo histórico de Parkinson | En uso | Compatible con el vector de 22 características | Depende de la equivalencia entre dataset original y features extraídas actualmente |
| Random Forest | A evaluar | Robusto, útil para datos tabulares, permite estimar importancia de variables | Puede sobreajustar datasets pequeños |
| SVM | A evaluar | Buen desempeño en espacios de alta dimensión | Sensible al escalamiento y a la selección del kernel |
| Logistic Regression | Línea base recomendada | Interpretable y útil como comparación mínima | Menor capacidad para relaciones no lineales |
| XGBoost | A explorar | Alto rendimiento en datos tabulares | Riesgo de sobreajuste y menor interpretabilidad directa |
| Wav2Vec2 / HuBERT / WavLM | Futuro | Aprende representaciones directamente desde audio | Requiere muchos datos etiquetados, mayor costo computacional y menor trazabilidad |

**Tabla III:** Comparación de modelos considerados para el pipeline de MedDiag2.

La decisión de no iniciar con deep learning end-to-end no debe interpretarse como una renuncia tecnológica. En esta fase, el proyecto no cuenta con un banco amplio de audios etiquetados, consentimiento, metadatos clínicos y control de sesgos. Por ello, un enfoque profundo podría producir resultados aparentemente altos sin trazabilidad suficiente. En cambio, el enfoque biomarcador permite explicar qué variables alimentan el modelo, comparar valores entre extractores y detectar errores de señal.

---

## XI. Hallazgos Técnicos

1. **La aplicación evolucionó de diagnóstico general a laboratorio de voz.** Aunque MedDiag nació como sistema de apoyo diagnóstico para varias enfermedades, el componente más novedoso en MedDiag2 es el módulo de Parkinson por voz.
2. **El vector del modelo condiciona el pipeline.** El modelo actual exige 22 características, lo que obliga a producir, marcar o rechazar todas las variables esperadas.
3. **Las variables no lineales son el principal punto de avance.** La rama `marcadoresNL` reduce una debilidad de versiones anteriores al calcular RPDE, DFA, D2, PPE, `spread1` y `spread2` mediante aproximaciones determinísticas.
4. **Parselmouth sigue siendo una ruta metodológica recomendada.** Aunque el pipeline actual usa Librosa como ruta principal para F0 y cálculos propios para varios biomarcadores, Parselmouth/Praat debe fortalecerse para jitter, shimmer y HNR [4].
5. **La calidad del audio es determinante.** Grabaciones cortas, ruidosas, saturadas o con poca fonación pueden producir valores poco confiables.
6. **La inferencia debe depender del estado de calidad.** No debe ejecutarse predicción ordinaria sobre señales inválidas o conjuntos de características parciales sin advertencia explícita.

---

## XII. Resultados del Desarrollo

Como resultado de esta fase, MedDiag2 cuenta con un flujo funcional para analizar audios de voz en el contexto de tamizaje experimental de Parkinson. Los principales resultados son:

1. Endpoint de carga de audio con validación básica.
2. Almacenamiento de archivos y metadatos.
3. Procesamiento de audio en segundo plano.
4. Generación de un vector de 22 características compatible con el modelo histórico de Parkinson.
5. Implementación de biomarcadores no lineales en la rama `marcadoresNL`.
6. Persistencia versionada de conjuntos de biomarcadores.
7. Endpoint de consulta de características extraídas.
8. Generación de predicción preliminar con probabilidad.
9. Documentación técnica sobre librerías, riesgos y ruta de investigación.

El proyecto también conserva modelos previamente entrenados para diabetes y enfermedad cardiovascular, pero el aporte principal de esta iteración corresponde al fortalecimiento del módulo de Parkinson por voz.

---

## XIII. Discusión

MedDiag2 demuestra que es posible integrar en una aplicación web un flujo completo de análisis de voz: captura, almacenamiento, extracción de biomarcadores, inferencia y visualización de resultados. Este logro es relevante desde el punto de vista académico porque combina ingeniería de software, ciencia de datos, procesamiento digital de señales y salud digital.

Sin embargo, el valor del prototipo no debe medirse solamente por la existencia de una predicción. El aspecto más importante es la trazabilidad del proceso. En aplicaciones de inteligencia artificial en salud, una predicción sin control sobre los datos de entrada y sin conocimiento de las características usadas puede generar interpretaciones erróneas.

La implementación de biomarcadores no lineales mejora la coherencia entre el modelo entrenado y el pipeline de inferencia. No obstante, las fórmulas actuales deben considerarse aproximaciones prácticas. La validación científica exigiría comparar sus salidas con herramientas de referencia, utilizar audios controlados y evaluar estabilidad intra-sujeto e inter-sujeto.

La decisión de no iniciar con deep learning end-to-end no es una renuncia tecnológica, sino una decisión metodológica. En ausencia de un banco amplio de audios etiquetados, con consentimiento, metadatos clínicos y control de sesgos, un modelo profundo puede ofrecer buen desempeño aparente sin trazabilidad suficiente. En cambio, un extractor basado en biomarcadores permite comparar valores, detectar errores, explicar inferencias y justificar ajustes del modelo.

---

## XIV. Limitaciones

1. **No es diagnóstico clínico:** la aplicación solo entrega una proyección preliminar y no reemplaza evaluación neurológica.
2. **Dataset limitado:** el modelo de Parkinson se basa en un dataset público pequeño y no necesariamente representativo de la población general [7].
3. **Sensibilidad al audio:** ruido, micrófono, distancia, intensidad vocal y duración afectan los biomarcadores.
4. **Aproximaciones algorítmicas:** varias medidas se calculan mediante aproximaciones propias y no deben interpretarse como equivalentes exactos de MDVP o Praat.
5. **Valores por defecto:** cuando una variable no puede calcularse, el sistema todavía puede usar `0.0` como compatibilidad técnica. Esto debe ser reemplazado por una política formal de características faltantes o parciales.
6. **Falta de validación clínica:** aún no se cuenta con evaluación por médicos ni con pruebas en población real.
7. **Riesgo de sobreinterpretación:** una probabilidad generada por el modelo puede ser mal entendida si no se acompaña de advertencias y contexto.
8. **Falta de control de calidad consolidado:** aunque la arquitectura objetivo contempla control de calidad, este debe formalizarse como compuerta previa a inferencia.

---

## XV. Recomendaciones y Trabajo Futuro

1. Congelar una versión mínima del extractor clásico: F0, jitter, shimmer y HNR con Parselmouth/Praat.
2. Implementar formalmente un servicio de control de calidad de audio antes de inferir.
3. Mantener Feature Store con `extractor_version`, `feature_schema_version`, `missing_features_json` e `is_partial`.
4. Evitar el uso silencioso de `0.0` para completar features faltantes; rechazar o marcar `partial_features`.
5. Diseñar pruebas con tres repeticiones por persona, vocal `/a/` de 3 a 5 segundos y condiciones controladas de ruido.
6. Comparar Parselmouth contra openSMILE y DisVoice antes de cambiar el extractor base.
7. Reentrenar o calibrar modelos solo con features realmente medidas y generadas por el pipeline definitivo.
8. Mantener consentimiento informado y advertencia visible: herramienta experimental de apoyo, no diagnóstico.
9. Evaluar modelos como Random Forest, SVM, Logistic Regression y XGBoost bajo un protocolo comparativo.
10. Explorar embeddings profundos como Wav2Vec2, HuBERT o WavLM solo cuando exista un banco de audios suficiente y bien etiquetado.

---

## XVI. Conclusiones

MedDiag2 puede consolidarse como una herramienta de tamizaje experimental basada en voz, no como un sistema de diagnóstico clínico. La ruta actual es adecuada porque prioriza control de calidad, extracción reproducible de biomarcadores, versionado de features, trazabilidad de inferencia y validación comparativa.

La rama `marcadoresNL` representa un avance significativo porque implementa biomarcadores no lineales que completan el vector requerido por el modelo de Parkinson mediante aproximaciones determinísticas. Este avance permite convertir el sistema en una base de investigación más sólida, siempre que se mantenga una postura crítica frente a la calidad de los datos, la equivalencia de las medidas acústicas y la necesidad de validación médica.

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

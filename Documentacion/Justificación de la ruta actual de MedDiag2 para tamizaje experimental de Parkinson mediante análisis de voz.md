> ⚠️ **DOCUMENTO DEPRECADO** — Esta es una versión borrador anterior.  
> El documento vigente y corregido es: [`MedDiag2_paper_corregido.md`](./MedDiag2_paper_corregido.md)  
> Se conserva solo como referencia histórica de evolución del paper.

# MedDiag2: tamizaje experimental de Parkinson mediante analisis de voz y biomarcadores acusticos

**Autores:** Adrian Espinosa, Diana Huertas, David Rios  
**Proyecto:** MedDiag2  
**Curso:** Proyecto Integrador  
**Linea:** Inteligencia artificial aplicada a salud digital  
**Estado:** ⛔ DEPRECADO — Usar versión corregida

---

## Resumen

MedDiag2 evoluciona desde un prototipo de apoyo diagnostico basado en variables clinicas ingresadas manualmente hacia una plataforma de tamizaje experimental centrada en voz sostenida, control de calidad, extraccion de biomarcadores acusticos y trazabilidad de inferencia. El proyecto integra una aplicacion web, un backend en FastAPI, almacenamiento de audios, modelos de aprendizaje automatico y un pipeline de procesamiento digital de senales orientado al analisis preliminar de enfermedad de Parkinson.

La ruta tecnica actual conserva un enfoque basado en biomarcadores interpretables. El sistema extrae variables asociadas al conjunto clasico de Parkinson: frecuencia fundamental, jitter, shimmer, HNR/NHR y biomarcadores no lineales. En la rama `marcadoresNL` se implementan aproximaciones deterministicas para DFA, D2, PPE, RPDE, `spread1` y `spread2`, reduciendo la dependencia de valores faltantes o placeholders. El sistema tambien incorpora persistencia versionada de biomarcadores mediante un Feature Store, validacion de caracteristicas y asociacion entre audio, biomarcadores e inferencia.

Este documento describe el funcionamiento de MedDiag2, sus avances, hallazgos tecnicos y limitaciones. Se sostiene que, en esta fase, el proyecto debe priorizar reproducibilidad, equivalencia de features, control de calidad y trazabilidad antes que complejidad de infraestructura o modelos de caja negra. MedDiag2 se define expresamente como una herramienta academica de apoyo y tamizaje experimental, no como un sistema de diagnostico clinico.

**Palabras clave:** Parkinson, biomarcadores de voz, FastAPI, Parselmouth, Praat, Librosa, aprendizaje automatico, procesamiento digital de senales, tamizaje experimental.

---

## 1. Introduccion

La enfermedad de Parkinson puede producir alteraciones vocales tempranas asociadas con inestabilidad de la fonacion, variacion de frecuencia fundamental, perturbaciones de amplitud y cambios en la relacion armonico-ruido. Por esta razon, la literatura ha explorado el uso de medidas acusticas como F0, jitter, shimmer, HNR, NHR, RPDE, DFA, D2 y PPE para construir modelos de clasificacion o seguimiento clinico.

En MedDiag2, este enfoque resulta pertinente porque el modelo historico de Parkinson fue entrenado sobre variables biomedicas de voz y no sobre audio crudo. La evolucion del proyecto no debe entenderse como una simple mejora de interfaz para recibir archivos de audio, sino como una reorganizacion metodologica alrededor del ciclo completo del biomarcador: captura, preprocesamiento, control de calidad, extraccion, persistencia versionada, inferencia y auditoria.

El objetivo de este documento es justificar la ruta tecnica actual de MedDiag2, describir su funcionamiento, presentar los avances implementados y delimitar sus limitaciones. El documento se fundamenta en la documentacion interna del proyecto, en el analisis del codigo de la rama `marcadoresNL` y en referencias cientificas sobre analisis de voz en Parkinson.

---

## 2. Planteamiento del problema

La version inicial de MedDiag funcionaba como una aplicacion cliente-servidor con frontend, backend FastAPI y modelos serializados. Para Parkinson, el sistema recibia un vector de biomarcadores acusticos ya calculados: frecuencia fundamental, jitter, shimmer, HNR y parametros no lineales, entre otros. Esta arquitectura era suficiente para probar integracion de software, pero dejaba abierto el problema critico de como obtener esos biomarcadores desde audio real.

En la evolucion de MedDiag2 se identificaron tres riesgos principales:

1. **Ruptura entre entrenamiento e inferencia:** el modelo fue entrenado con variables estructuradas, pero en produccion podia recibir valores calculados por metodos diferentes o de baja calidad.
2. **Uso de aproximaciones o placeholders:** algunas variables no lineales no estaban calculadas de forma reproducible.
3. **Imputacion silenciosa de valores `0.0`:** el sistema podia generar inferencias numericamente validas, pero biomediamente discutibles.

Por tanto, la pregunta tecnica central no es solo que modelo clasifica mejor en un dataset controlado, sino que ruta garantiza que los datos que alimentan el modelo sean comparables, auditables y reproducibles.

---

## 3. Objetivo general

Desarrollar y documentar un prototipo web de tamizaje experimental de Parkinson basado en analisis de voz, capaz de extraer biomarcadores acusticos desde grabaciones de usuario y utilizarlos como entrada para un modelo de aprendizaje automatico.

## 4. Objetivos especificos

1. Integrar un flujo de carga, almacenamiento y procesamiento de audios dentro de una arquitectura web.
2. Extraer biomarcadores acusticos asociados al dataset clasico de Parkinson.
3. Implementar aproximaciones deterministicas para biomarcadores no lineales como DFA, D2, PPE, RPDE, `spread1` y `spread2`.
4. Persistir los biomarcadores extraidos junto con informacion de versionamiento del extractor y del esquema de caracteristicas.
5. Generar una prediccion preliminar de Parkinson a partir del vector de biomarcadores.
6. Identificar limitaciones tecnicas, metodologicas y clinicas que deben considerarse antes de interpretar los resultados.

---

## 5. Marco conceptual

### 5.1 Biomarcadores de voz en Parkinson

Diversos estudios han explorado la relacion entre enfermedad de Parkinson y alteraciones vocales. La hipofonia, la inestabilidad de la frecuencia fundamental y los cambios en la calidad vocal pueden reflejar afectaciones del control motor del habla. Por ello, las grabaciones de vocal sostenida han sido usadas como fuente de caracteristicas acusticas para modelos de clasificacion.

El conjunto clasico de Parkinson usado por el proyecto incluye 22 variables:

- frecuencia: `MDVP:Fo(Hz)`, `MDVP:Fhi(Hz)`, `MDVP:Flo(Hz)`;
- jitter: `MDVP:Jitter(%)`, `MDVP:Jitter(Abs)`, `MDVP:RAP`, `MDVP:PPQ`, `Jitter:DDP`;
- shimmer: `MDVP:Shimmer`, `MDVP:Shimmer(dB)`, `Shimmer:APQ3`, `Shimmer:APQ5`, `MDVP:APQ`, `Shimmer:DDA`;
- ruido-armonicidad: `NHR`, `HNR`;
- no lineales: `RPDE`, `DFA`, `spread1`, `spread2`, `D2`, `PPE`.

### 5.2 Jitter, shimmer y HNR

El jitter representa variaciones ciclo a ciclo de la frecuencia fundamental. El shimmer describe variaciones ciclo a ciclo de la amplitud. El HNR expresa la relacion entre componentes armonicos y ruido en la senal de voz. Estas medidas son sensibles a la calidad de la grabacion y a la configuracion del algoritmo de extraccion, por lo que no deben interpretarse de manera aislada ni como equivalentes directos entre herramientas distintas.

### 5.3 Biomarcadores no lineales

Las variables no lineales buscan capturar propiedades complejas de la senal vocal que no siempre son evidentes en medidas lineales tradicionales. En la rama `marcadoresNL`, MedDiag2 implementa:

- **DFA:** analiza fluctuaciones de la senal tras remover tendencias locales.
- **D2:** aproxima la dimension de correlacion mediante una estrategia tipo Grassberger-Procaccia.
- **PPE:** estima la entropia de la distribucion del pitch en escala logaritmica.
- **RPDE:** aproxima la entropia de densidad de periodos recurrentes a partir de retardos de recurrencia.
- **spread1 y spread2:** describen desplazamiento y dispersion de la distribucion del log-pitch.

Estas variables enriquecen el vector de entrada del modelo, pero en el estado actual deben entenderse como aproximaciones experimentales. Su validacion requiere comparar valores frente a implementaciones de referencia y audios controlados.

---

## 6. Ruta tecnica actual

La ruta actual se organiza en capas progresivas:

| Capa | Eleccion actual | Justificacion | Riesgo controlado |
|---|---|---|---|
| Captura de voz | Vocal sostenida, idealmente `/a/` | Reduce variabilidad y facilita perturbaciones de F0 y amplitud | Muestras no comparables |
| Preprocesamiento | Mono, frecuencia de muestreo controlada y decodificacion robusta | Estandariza la senal antes de extraer biomarcadores | Sesgos por dispositivo o formato |
| Extraccion base | Librosa, SciPy y Pydub | Carga, compatibilidad y calculos auxiliares | Fallos de formato o pipeline rigido |
| Extraccion clinica recomendada | Parselmouth/Praat | Ruta defendible para F0, jitter, shimmer y HNR | Desviacion de medidas vocales |
| Biomarcadores no lineales | Implementaciones deterministicas en `marcadoresNL` | Completa el vector historico del modelo | Placeholders y variables incompletas |
| Persistencia | Feature Store con version de extractor y esquema | Permite auditoria y comparacion entre corridas | Resultados no trazables |
| Inferencia | Modelo actual de Parkinson | Reutiliza el clasificador disponible | Entrada incompatible con entrenamiento |

La decision metodologica mas importante es separar responsabilidades: el audio no es el centro del sistema; el centro es la confiabilidad del biomarcador que llega al modelo.

---

## 7. Arquitectura del sistema

MedDiag2 utiliza una arquitectura web dividida en frontend, backend, servicios de procesamiento y persistencia.

### 7.1 Frontend

El frontend esta construido en Next.js. Permite autenticacion, acceso a rutas privadas, carga de audios y consulta de registros procesados. La aplicacion ofrece una interfaz para que el usuario grabe o suba una muestra de voz, revise su estado de procesamiento y consulte los biomarcadores extraidos.

### 7.2 Backend

El backend esta construido con FastAPI. Expone endpoints para:

- cargar audios mediante `POST /audio/upload`;
- listar audios del usuario mediante `GET /audio/me`;
- consultar un audio especifico mediante `GET /audio/{audio_id}`;
- procesar un audio mediante `POST /audio/{audio_id}/process`;
- obtener biomarcadores mediante `GET /audio/{audio_id}/features`;
- procesar lotes de audios mediante `POST /audio/batch-process`;
- obtener resumen de analisis mediante `GET /audio/analysis/summary`.

### 7.3 Almacenamiento y trazabilidad

El sistema guarda los archivos de audio en un backend de almacenamiento configurable y registra metadatos en base de datos. Cada audio conserva informacion como usuario, nombre original, tipo MIME, tamano, ruta de almacenamiento, estado de procesamiento, notas y marcas temporales.

Ademas, la entidad `BiomarkerFeature` permite almacenar el conjunto de biomarcadores asociado a un audio, junto con:

- `extractor_version`;
- `feature_schema_version`;
- `features_json`;
- `missing_features_json`;
- `is_partial`.

Esta separacion permite auditar los resultados y comparar versiones del extractor.

---

## 8. Funcionamiento del modulo de analisis de voz

### 8.1 Carga del audio

El usuario envia un archivo de audio al endpoint de carga. El sistema valida tipo y tamano, guarda el archivo en almacenamiento y crea un registro en base de datos. Luego marca el audio como `processing` y ejecuta el procesamiento en segundo plano.

### 8.2 Decodificacion

El servicio de procesamiento intenta cargar el audio con `librosa`. Si la decodificacion falla y `pydub` esta disponible, utiliza `pydub` como mecanismo alternativo. El sistema exige una duracion minima de 0.5 segundos para evitar procesar muestras demasiado cortas.

### 8.3 Extraccion de frecuencia fundamental

La frecuencia fundamental se estima usando una estrategia escalonada:

1. `librosa.pyin` como metodo principal;
2. Parselmouth/Praat como alternativa si no se obtiene F0;
3. autocorrelacion con SciPy como fallback.

A partir de F0 se calculan frecuencia mediana, maxima y minima.

### 8.4 Extraccion de biomarcadores

El extractor calcula:

- jitter y medidas derivadas: RAP, PPQ y DDP;
- shimmer y medidas derivadas: APQ3, APQ5, APQ y DDA;
- NHR y HNR mediante una aproximacion cepstral;
- biomarcadores no lineales: DFA, D2, PPE, RPDE, `spread1` y `spread2`.

Si una caracteristica no puede calcularse por insuficiencia de datos o condiciones invalidas, el sistema usa `0.0` como valor de compatibilidad. Esta decision mantiene el vector completo de 22 caracteristicas, pero debe interpretarse como una limitacion metodologica.

### 8.5 Inferencia preliminar

Una vez extraido el vector de biomarcadores, el pipeline valida que las caracteristicas esperadas esten presentes y sean finitas. Luego invoca el modelo de Parkinson y crea un registro de diagnostico preliminar con probabilidad asociada. El resultado se expresa como orientacion experimental, no como diagnostico medico.

---

## 9. Avances implementados

### 9.1 Extraccion de biomarcadores no lineales

La rama `marcadoresNL` implementa funciones deterministicas para:

- `compute_dfa`;
- `compute_d2`;
- `compute_ppe`;
- `compute_rpde`;
- `compute_spread_features`.

Este avance permite que el sistema calcule los seis biomarcadores no lineales esperados por el esquema de Parkinson, en lugar de depender unicamente de valores por defecto.

### 9.2 Mayor trazabilidad

El sistema persiste los biomarcadores en una entidad especifica de base de datos. Cada conjunto de caracteristicas queda asociado al audio procesado, a la version del extractor y a la version del esquema. Esto facilita auditoria, reproduccion de resultados y comparacion entre iteraciones.

### 9.3 Integracion con flujo de usuario

El procesamiento de audio esta integrado con endpoints protegidos por autenticacion. Cada usuario puede cargar, listar y consultar sus propios audios. El sistema contempla control de acceso para que solo el propietario o un administrador puedan ver registros especificos.

### 9.4 Procesamiento asincronico

Despues de la carga, el audio se procesa en segundo plano. Esto mejora la experiencia de usuario, ya que la solicitud de carga no queda bloqueada hasta que termine la extraccion de biomarcadores.

### 9.5 Compatibilidad con el modelo existente

El pipeline conserva el esquema de 22 variables del modelo de Parkinson ya entrenado. Esto permite reutilizar el modelo actual mientras se mejora progresivamente la calidad de la extraccion.

---

## 10. Hallazgos tecnicos

1. **La aplicacion evoluciono de diagnostico general a laboratorio de voz.** Aunque MedDiag nacio como sistema de apoyo diagnostico para varias enfermedades, el componente mas novedoso en MedDiag2 es el modulo de Parkinson por voz.
2. **El vector del modelo condiciona el pipeline.** El modelo actual exige 22 caracteristicas, lo que obliga a producir o marcar todas las variables esperadas.
3. **Las variables no lineales son el principal punto de avance.** La rama `marcadoresNL` reduce una debilidad de versiones anteriores al calcular RPDE, DFA, D2, PPE, `spread1` y `spread2`.
4. **Parselmouth sigue siendo una ruta metodologica recomendada.** Aunque el pipeline actual usa `librosa` como ruta principal para F0 y calculos propios para varios biomarcadores, Parselmouth/Praat debe fortalecerse para jitter, shimmer y HNR.
5. **La calidad del audio es determinante.** Grabaciones cortas, ruidosas, saturadas o con poca fonacion pueden producir valores poco confiables.

---

## 11. Resultados del desarrollo

Como resultado de esta fase, MedDiag2 cuenta con un flujo funcional para analizar audios de voz en el contexto de tamizaje experimental de Parkinson. Los principales resultados son:

1. endpoint de carga de audio con validacion basica;
2. almacenamiento de archivos y metadatos;
3. procesamiento de audio en segundo plano;
4. extraccion de 22 biomarcadores acusticos compatibles con el modelo de Parkinson;
5. implementacion de biomarcadores no lineales en la rama `marcadoresNL`;
6. persistencia versionada de conjuntos de biomarcadores;
7. endpoint de consulta de caracteristicas extraidas;
8. generacion de prediccion preliminar con probabilidad;
9. documentacion tecnica sobre librerias, riesgos y ruta de investigacion.

El proyecto tambien conserva modelos previamente entrenados para diabetes y enfermedad cardiovascular, pero el aporte principal de esta iteracion corresponde al fortalecimiento del modulo de Parkinson por voz.

---

## 12. Discusion

MedDiag2 demuestra que es posible integrar en una aplicacion web un flujo completo de analisis de voz: captura, almacenamiento, extraccion de biomarcadores, inferencia y visualizacion de resultados. Este logro es relevante desde el punto de vista academico porque combina ingenieria de software, ciencia de datos, procesamiento digital de senales y salud digital.

Sin embargo, el valor del prototipo no debe medirse solamente por la existencia de una prediccion. El aspecto mas importante es la trazabilidad del proceso. En aplicaciones de inteligencia artificial en salud, una prediccion sin control sobre los datos de entrada y sin conocimiento de las caracteristicas usadas puede generar interpretaciones erroneas.

La implementacion de biomarcadores no lineales mejora la coherencia entre el modelo entrenado y el pipeline de inferencia. No obstante, las formulas actuales deben considerarse aproximaciones practicas. La validacion cientifica exigiria comparar sus salidas con herramientas de referencia, utilizar audios controlados y evaluar estabilidad intra-sujeto e inter-sujeto.

La decision de no iniciar con deep learning end-to-end no es una renuncia tecnologica, sino una decision metodologica. En ausencia de un banco amplio de audios etiquetados, con consentimiento, metadatos clinicos y control de sesgos, un modelo profundo puede ofrecer buen desempeno aparente sin trazabilidad suficiente. En cambio, un extractor basado en biomarcadores permite comparar valores, detectar errores, explicar inferencias y justificar ajustes del modelo.

---

## 13. Limitaciones

1. **No es diagnostico clinico:** la aplicacion solo entrega una prediccion preliminar y no reemplaza evaluacion neurologica.
2. **Dataset limitado:** el modelo de Parkinson se basa en un dataset publico pequeno y no necesariamente representativo de la poblacion general.
3. **Sensibilidad al audio:** ruido, microfono, distancia, intensidad vocal y duracion afectan los biomarcadores.
4. **Aproximaciones algoritmicas:** varias medidas se calculan mediante aproximaciones propias y no deben interpretarse como equivalentes exactos de MDVP o Praat.
5. **Valores por defecto:** cuando una variable no puede calcularse, el sistema usa `0.0`, lo cual mantiene compatibilidad tecnica pero puede afectar la interpretacion del modelo.
6. **Falta de validacion clinica:** aun no se cuenta con evaluacion por medicos ni con pruebas en poblacion real.
7. **Riesgo de sobreinterpretacion:** una probabilidad generada por el modelo puede ser mal entendida si no se acompana de advertencias y contexto.

---

## 14. Recomendaciones y trabajo futuro

1. Congelar una version minima del extractor clasico: F0, jitter, shimmer y HNR con Parselmouth.
2. Implementar formalmente un servicio de control de calidad de audio antes de inferir.
3. Mantener Feature Store con `extractor_version`, `feature_schema_version`, `missing_features_json` e `is_partial`.
4. Evitar el uso silencioso de `0.0` para completar features faltantes; rechazar o marcar `partial_features`.
5. Disenar pruebas con tres repeticiones por persona, vocal `/a/` de 3 a 5 segundos y condiciones controladas de ruido.
6. Comparar Parselmouth contra openSMILE y DisVoice antes de cambiar el extractor base.
7. Reentrenar o calibrar modelos solo con features realmente medidas y generadas por el pipeline definitivo.
8. Mantener consentimiento informado y advertencia visible: herramienta experimental de apoyo, no diagnostico.
9. Evaluar modelos como Random Forest, SVM, Logistic Regression y XGBoost bajo un protocolo comparativo.
10. Explorar embeddings profundos como Wav2Vec2, HuBERT o WavLM solo cuando exista un banco de audios suficiente y bien etiquetado.

---

## 15. Conclusiones

MedDiag2 puede consolidarse como una herramienta de tamizaje experimental basada en voz, no como un sistema de diagnostico clinico. La ruta actual es adecuada porque prioriza control de calidad, extraccion reproducible de biomarcadores, versionado de features, trazabilidad de inferencia y validacion comparativa.

La rama `marcadoresNL` representa un avance significativo porque implementa biomarcadores no lineales que completan el vector requerido por el modelo de Parkinson. Este avance permite convertir el sistema en una base de investigacion mas solida, siempre que se mantenga una postura critica frente a la calidad de los datos, la equivalencia de las medidas acusticas y la necesidad de validacion medica.

En sintesis, MedDiag2 avanza desde un MVP de prediccion medica general hacia una plataforma experimental especializada, centrada en biomarcadores de voz para Parkinson. Su estado actual es adecuado para una entrega academica de desarrollo e investigacion aplicada, y ofrece una base clara para futuras mejoras metodologicas, clinicas y tecnicas.

---

## Referencias

Boersma, P. (1993). Accurate short-term analysis of the fundamental frequency and the harmonics-to-noise ratio of a sampled sound. *Proceedings of the Institute of Phonetic Sciences*, 17, 97-110.

Boersma, P., & Weenink, D. (2024). *Praat: Doing phonetics by computer* [Computer program]. https://www.praat.org/

Deliyski, D. D., Shaw, H. S., & Evans, M. K. (2005). Influence of sampling rate on accuracy and reliability of acoustic voice analysis. *Logopedics Phoniatrics Vocology*, 30(2), 55-62.

Jadoul, Y., Thompson, B., & de Boer, B. (2018). Introducing Parselmouth: A Python interface to Praat. *Journal of Phonetics*, 71, 1-15. https://doi.org/10.1016/j.wocn.2018.07.001

Little, M. A., McSharry, P. E., Hunter, E. J., Spielman, J., & Ramig, L. O. (2009). Suitability of dysphonia measurements for telemonitoring of Parkinson's disease. *IEEE Transactions on Biomedical Engineering*, 56(4), 1015-1022. https://doi.org/10.1109/TBME.2008.2005954

Maryn, Y., Corthals, P., De Bodt, M., Van Cauwenberge, P., & Deliyski, D. (2010). Toward improved ecological validity in the acoustic measurement of overall voice quality: Combining continuous speech and sustained vowels. *Journal of Voice*, 24(5), 540-555.

McFee, B., Raffel, C., Liang, D., Ellis, D. P. W., McVicar, M., Battenberg, E., & Nieto, O. (2015). librosa: Audio and music signal analysis in Python. *Proceedings of the 14th Python in Science Conference*, 18-25.

Tsanas, A., Little, M. A., McSharry, P. E., & Ramig, L. O. (2011). Nonlinear speech analysis algorithms mapped to a standard metric achieve clinically useful quantification of average Parkinson's disease symptom severity. *Journal of the Royal Society Interface*, 8(59), 842-855. https://doi.org/10.1098/rsif.2010.0456

UCI Machine Learning Repository. *Oxford Parkinson's Disease Detection Dataset*.

Documentacion interna del proyecto MedDiag2. `README.md`, `INVESTIGACION_BIOMARCADORES_VOZ_PARKINSON.markdown.md`, `DEPLOY.md` y codigo fuente de la rama `marcadoresNL`.

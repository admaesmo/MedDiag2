# Guia de Despliegue MedDiag2

Esta guia describe el despliegue objetivo de MedDiag2:

- Backend FastAPI en Render.
- Base de datos PostgreSQL en Render.
- Frontend Next.js en Vercel.
- Modelos ML incluidos desde `saved_models/`.
- Pipeline de audio con persistencia de calidad, biomarcadores e inferencia.

La arquitectura separa el frontend publico del backend API. Vercel consume la API de Render mediante `NEXT_PUBLIC_API_BASE_URL`, y Render permite el dominio de Vercel mediante `ALLOWED_ORIGINS`.

---

## 1. Estructura Relevante

```text
app/                         Backend FastAPI
alembic/                     Migraciones de base de datos
saved_models/                Modelos .sav
frontend/web/                Frontend Next.js
requirements.txt             Dependencias backend
render.yaml                  Blueprint de Render
Dockerfile                   Imagen alternativa para backend
frontend/web/package.json    Dependencias/scripts frontend
```

---

## 2. Variables De Entorno

### Backend Render

Configurar en el servicio `meddiag-api`:

```env
DATABASE_URL=<inyectada por Render PostgreSQL>
MODEL_DIR=./saved_models
ALLOWED_ORIGINS=https://<tu-frontend>.vercel.app,http://localhost:3000,http://127.0.0.1:3000

AUTH_PROVIDER=local
JWT_SECRET_KEY=<secreto-largo-y-privado>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

STORAGE_PROVIDER=local
STORAGE_LOCAL_PATH=./storage/audio
MAX_AUDIO_FILE_SIZE_MB=25
```

Si se usa Supabase para autenticacion:

```env
AUTH_PROVIDER=supabase
SUPABASE_JWT_SECRET=<jwt-secret>
SUPABASE_URL=<project-url>
SUPABASE_JWKS_URL=<jwks-url-si-aplica>
```

Notas:

- En produccion no usar `JWT_SECRET_KEY=dev-secret-change-me`.
- Evitar `ALLOWED_ORIGINS=*` en produccion.
- Render Free no garantiza almacenamiento local persistente. Para audio real en produccion se recomienda migrar `STORAGE_PROVIDER` a un storage externo.

### Frontend Vercel

Configurar en el proyecto Vercel:

```env
NEXT_PUBLIC_API_BASE_URL=https://<tu-api>.onrender.com
NEXT_PUBLIC_USE_MOCK_API=false
NEXT_PUBLIC_AUTH_MODE=local
NEXT_PUBLIC_LOCAL_AUTH_EMAIL=demo@meddiag.local
NEXT_PUBLIC_LOCAL_AUTH_PASSWORD=meddiag123
NEXT_PUBLIC_LOCAL_AUTH_ROLE=patient
NEXT_PUBLIC_LOCAL_AUTH_DISPLAY_NAME=Demo Local
```

Si se usa Supabase:

```env
NEXT_PUBLIC_AUTH_MODE=supabase
NEXT_PUBLIC_SUPABASE_URL=<project-url>
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY=<anon-or-publishable-key>
```

---

## 3. Despliegue Backend En Render

### Opcion A: Blueprint Con `render.yaml`

1. En Render, seleccionar **New -> Blueprint**.
2. Conectar el repositorio GitHub.
3. Seleccionar la rama que se quiere desplegar, normalmente `main`.
4. Render debe detectar:
   - Web service: `meddiag-api`
   - PostgreSQL: `meddiag-db`
5. Revisar variables de entorno.
6. Crear el blueprint.

El `render.yaml` actual usa:

```yaml
buildCommand: "pip install -r requirements.txt"
startCommand: "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
```

### Opcion B: Web Service Manual

Crear un Web Service desde GitHub:

```text
Runtime: Python
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Luego crear una base PostgreSQL en Render y copiar su connection string en `DATABASE_URL`.

---

## 4. Migraciones De Base De Datos

El proyecto usa Alembic. Despues de desplegar o cambiar el esquema, ejecutar:

```bash
alembic upgrade head
```

En Render se puede ejecutar como **Shell Command** desde el servicio backend.

Si una base existente no tiene `alembic_version`, primero validar manualmente en ambiente seguro. Para la base local historica del proyecto se uso:

```bash
alembic stamp 002
alembic upgrade head
```

No usar `stamp` en produccion sin confirmar que la estructura real coincide con la revision marcada.

Cambios de esquema recientes incluyen:

- `audio_quality_reports`
- `biomarker_features`
- nuevos estados de `audio_records`

---

## 5. Despliegue Frontend En Vercel

1. En Vercel, seleccionar **Add New Project**.
2. Importar el repositorio GitHub.
3. Configurar:

```text
Framework Preset: Next.js
Root Directory: frontend/web
Build Command: npm run build
Install Command: npm install
Output Directory: .next
```

4. Agregar variables de entorno de frontend.
5. Desplegar.
6. Copiar el dominio generado, por ejemplo:

```text
https://meddiag2.vercel.app
```

7. Volver a Render y actualizar:

```env
ALLOWED_ORIGINS=https://meddiag2.vercel.app
```

Si se mantienen ambientes de preview en Vercel, agregar tambien los dominios preview que vayan a consumir la API.

---

## 6. Verificacion Post-Deploy

### Backend

Abrir:

```text
https://<tu-api>.onrender.com/health
https://<tu-api>.onrender.com/docs
```

Debe responder:

```json
{"status": "ok"}
```

### Frontend

Abrir:

```text
https://<tu-frontend>.vercel.app
```

Validar:

- Login o modo local de autenticacion.
- Acceso a rutas privadas.
- Captura o carga de audio.
- Procesamiento de audio.
- Consulta de historico.
- Visualizacion de resultado.

### Pipeline De Audio

Validar end-to-end:

1. Subir audio.
2. Confirmar estado `preprocessing` / `quality_checked`.
3. Confirmar reporte en `GET /audio/{id}/quality`.
4. Confirmar features en `GET /audio/{id}/features`.
5. Confirmar estado final `inference_completed`, `partial_features` o `rejected`.

---

## 7. Ejecucion Local

Desde la raiz del repo:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Crear `.env`:

```env
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

Crear `frontend/web/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_USE_MOCK_API=false
NEXT_PUBLIC_AUTH_MODE=local
NEXT_PUBLIC_LOCAL_AUTH_EMAIL=demo@meddiag.local
NEXT_PUBLIC_LOCAL_AUTH_PASSWORD=meddiag123
NEXT_PUBLIC_LOCAL_AUTH_ROLE=patient
NEXT_PUBLIC_LOCAL_AUTH_DISPLAY_NAME=Demo Local
```

Instalar frontend:

```bash
cd frontend/web
npm install
cd ../..
```

Levantar todo:

```bash
./scripts/start-local.sh
```

Detener:

```bash
./scripts/stop-local.sh
```

URLs locales:

```text
Backend:  http://127.0.0.1:8000
Docs API: http://127.0.0.1:8000/docs
Frontend: http://127.0.0.1:3000
```

---

## 8. Consideraciones De Produccion

### Almacenamiento De Audio

Actualmente el backend soporta storage local mediante:

```env
STORAGE_PROVIDER=local
STORAGE_LOCAL_PATH=./storage/audio
```

En Render Free, el filesystem puede reiniciarse. Para una demo puede ser suficiente, pero para produccion o evaluacion persistente se recomienda:

- S3 compatible storage.
- Supabase Storage.
- Azure Blob Storage.
- Otro storage externo.

### Modelos ML

Los modelos `.sav` estan en `saved_models/`. Recomendaciones:

- Versionar modelos con `model_version`.
- Alinear `feature_schema_version` del modelo con `biomarker_features`.
- Evitar desplegar modelos entrenados con features no reproducibles.
- Revisar warnings de scikit-learn si el modelo fue serializado con otra version.

### Seguridad Y Consentimiento

Antes de usar audios reales:

- Mostrar consentimiento informado.
- Explicar que el sistema es apoyo experimental, no diagnostico medico.
- Evitar exponer secretos en variables `NEXT_PUBLIC_*`.
- Restringir CORS a dominios conocidos.

---

## 9. Troubleshooting

### Error CORS Desde Vercel

Actualizar en Render:

```env
ALLOWED_ORIGINS=https://<tu-frontend>.vercel.app
```

Reiniciar el servicio backend.

### Error De Migraciones

Verificar revision:

```bash
alembic current
alembic heads
```

Luego:

```bash
alembic upgrade head
```

### Audio No Se Procesa

Revisar logs de Render:

- dependencias de audio instaladas,
- existencia de `saved_models/`,
- valor de `MAX_AUDIO_FILE_SIZE_MB`,
- reporte de calidad en `/audio/{id}/quality`,
- estado final del audio.

### Frontend No Llama A La API Correcta

Verificar en Vercel:

```env
NEXT_PUBLIC_API_BASE_URL=https://<tu-api>.onrender.com
NEXT_PUBLIC_USE_MOCK_API=false
```

Volver a desplegar el frontend despues de cambiar variables `NEXT_PUBLIC_*`.

# MedDiag2 — Frontend Web (Next.js)

Frontend de MedDiag2 para tamizaje experimental de Parkinson mediante análisis de voz. Construido con **Next.js 13+**, **TypeScript** y **Atomic Design**.

---

## Tabla de Contenidos

- [Stack Tecnológico](#stack-tecnológico)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Arquitectura de Componentes](#arquitectura-de-componentes)
- [Rutas](#rutas)
- [Features / Hooks](#features--hooks)
- [Internacionalización (i18n)](#internacionalización-i18n)
- [Estado Global](#estado-global)
- [Autenticación](#autenticación)
- [Variables de Entorno](#variables-de-entorno)
- [Ejecución Local](#ejecución-local)
- [API / Backend](#api--backend)

---

## Stack Tecnológico

| Tecnología | Versión | Propósito |
|-----------|---------|-----------|
| **Next.js** | 13+ (App Router) | Framework principal |
| **TypeScript** | 5+ | Tipado estático |
| **Tailwind CSS** | 3+ | Estilos utilitarios |
| **Zustand** | — | Estado global liviano |
| **Supabase** | — | Autenticación (opcional) |
| **Lucide React** | — | Iconos |
| **ESLint** | — | Linting |

---

## Estructura del Proyecto

```
frontend/web/
├── app/                          # App Router (Next.js 13+)
│   ├── globals.css               # Estilos globales
│   ├── layout.tsx                # Layout raíz
│   ├── page.tsx                  # Página principal (pública)
│   ├── providers.tsx             # Providers globales
│   ├── (private)/                # Grupo de rutas privadas (requieren auth)
│   │   ├── layout.tsx            # Layout privado (sidebar + topbar)
│   │   ├── dashboard/page.tsx    # Panel principal
│   │   ├── history/page.tsx      # Historial de análisis
│   │   ├── parkinson/page.tsx    # Análisis de voz para Parkinson
│   │   └── settings/page.tsx     # Configuración del usuario
│   ├── auth/
│   │   └── callback/route.ts     # Callback de OAuth (Supabase)
│   ├── login/page.tsx            # Página de inicio de sesión
│   └── register/page.tsx         # Página de registro
│
├── components/                   # Sistema de Atomic Design
│   ├── atoms/                    # Componentes básicos
│   │   ├── badge.tsx             # Badge/Burbuja de estado
│   │   ├── button.tsx            # Botones
│   │   ├── card.tsx              # Tarjetas
│   │   ├── input.tsx             # Campos de entrada
│   │   └── skip-link.tsx         # Enlace de accesibilidad (skip to content)
│   ├── molecules/                # Combinaciones de átomos
│   │   └── nav-item.tsx          # Ítem de navegación
│   ├── organisms/                # Componentes complejos
│   │   ├── sidebar.tsx           # Barra lateral de navegación
│   │   └── topbar.tsx            # Barra superior
│   └── templates/                # Plantillas de página
│       └── private-shell.tsx     # Layout de rutas privadas
│
├── features/                     # Hooks y lógica por feature
│   ├── auth/
│   │   ├── schema.ts             # Schema de validación de auth
│   │   └── use-session.ts        # Hook de sesión de usuario
│   ├── dashboard/
│   │   └── queries.ts            # Queries del dashboard
│   ├── parkinson/
│   │   ├── audio-blob-to-wav.ts  # Conversión de grabación a WAV
│   │   ├── mutations.ts          # Mutaciones (subir audio, procesar)
│   │   └── use-audio-recording.ts # Hook de grabación de audio
│   └── settings/
│       └── schema.ts             # Schema de validación de settings
│
├── lib/                          # Utilidades y configuración
│   ├── api.ts                    # Cliente HTTP para el backend API
│   ├── auth-mode.ts              # Detección del modo de auth
│   ├── local-auth-shared.ts      # Estado compartido de auth local
│   ├── local-auth.ts             # Lógica de autenticación local
│   ├── utils.ts                  # Utilidades generales
│   └── i18n/                     # Internacionalización
│       ├── config.ts             # Configuración de i18n
│       ├── index.ts              # Índice y re-exportaciones
│       └── dictionaries/         # Diccionarios por idioma
│           ├── en.ts             # Inglés
│           ├── es.ts             # Español
│           └── pt-BR.ts          # Portugués (Brasil)
│
├── stores/                       # Estado global (Zustand)
│   └── ui-store.ts               # Estado de UI (sidebar, tema, etc.)
│
├── middleware.ts                  # Next.js middleware (protección de rutas)
├── next.config.js                 # Configuración de Next.js
├── tailwind.config.ts             # Configuración de Tailwind CSS
├── postcss.config.js              # Configuración de PostCSS
├── tsconfig.json                  # Configuración de TypeScript
├── package.json                   # Dependencias y scripts
└── .env.local.example             # Variables de entorno de ejemplo
```

---

## Rutas

| Ruta | Privada | Descripción |
|------|---------|-------------|
| `/` | No | Página principal (pública) |
| `/login` | No | Inicio de sesión |
| `/register` | No | Registro de usuario |
| `/dashboard` | Sí | Panel principal con resumen |
| `/history` | Sí | Historial de análisis realizados |
| `/parkinson` | Sí | Grabación/carga de audio y análisis de Parkinson |
| `/settings` | Sí | Configuración del perfil |
| `/auth/callback` | No | Callback OAuth (Supabase) |

Las rutas privadas están envueltas en el layout `(private)/layout.tsx` que renderiza el shell privado (`PrivateShell`) con sidebar y topbar.

---

## Internacionalización (i18n)

El proyecto soporta **3 idiomas**:

- **es** — Español (predeterminado)
- **en** — Inglés
- **pt-BR** — Portugués de Brasil

Ubicación: [`lib/i18n/`](./lib/i18n/)

```typescript
import { t } from '@/lib/i18n'
// Uso: t('common.save') // Retorna el texto en el idioma activo
```

La selección de idioma se maneja mediante el store de UI (`ui-store.ts`).

---

## Features / Hooks

### `features/parkinson/`

- **`use-audio-recording.ts`** — Hook para grabar audio desde el navegador usando la API `MediaRecorder`. Permite iniciar, detener, pausar y obtener el blob de audio grabado.
- **`audio-blob-to-wav.ts`** — Convierte el blob grabado (generalmente en formato WebM/Opus) a **WAV PCM** para compatibilidad con el pipeline de procesamiento del backend.
- **`mutations.ts`** — Mutaciones para subir audio (`POST /audio/upload`) y procesarlo (`POST /audio/{id}/process`). Usa el cliente API desde `lib/api.ts`.

### `features/auth/`

- **`use-session.ts`** — Hook que expone la sesión del usuario, el token JWT, y funciones de login/logout. Soporta tanto auth local como Supabase.
- **`schema.ts`** — Schemas de validación (formularios de login/register).

### `features/dashboard/`

- **`queries.ts`** — Consultas al backend para mostrar datos en el dashboard (resumen de audios, última actividad, etc.).

---

## Estado Global

Se usa **Zustand** para estado global liviano:

```typescript
// stores/ui-store.ts
interface UIState {
  sidebarOpen: boolean
  language: 'es' | 'en' | 'pt-BR'
  // ...
}
```

No se usa Redux ni Context API compleja. Zustand es suficiente para las necesidades del proyecto.

---

## Autenticación

El frontend soporta **dos modos de autenticación**, seleccionables vía variable de entorno:

### 1. Auth Local (para desarrollo)
- Configurar `NEXT_PUBLIC_AUTH_MODE=local`
- Usa credenciales fijas definidas en `.env.local`
- No requiere servicios externos

### 2. Auth Supabase (para producción)
- Configurar `NEXT_PUBLIC_AUTH_MODE=supabase`
- Requiere proyecto Supabase con autenticación habilitada
- Soporta OAuth y email/password

El **middleware** (`middleware.ts`) protege las rutas privadas redirigiendo a `/login` si no hay sesión activa.

---

## Variables de Entorno

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `NEXT_PUBLIC_API_BASE_URL` | Sí | URL del backend FastAPI (ej: `http://127.0.0.1:8000`) |
| `NEXT_PUBLIC_USE_MOCK_API` | No | Usar API mock (`true`/`false`) |
| `NEXT_PUBLIC_AUTH_MODE` | Sí | `local` o `supabase` |

### Si `NEXT_PUBLIC_AUTH_MODE=local`:
| Variable | Descripción |
|----------|-------------|
| `NEXT_PUBLIC_LOCAL_AUTH_EMAIL` | Email del usuario demo |
| `NEXT_PUBLIC_LOCAL_AUTH_PASSWORD` | Contraseña del usuario demo |
| `NEXT_PUBLIC_LOCAL_AUTH_ROLE` | Rol (`patient`, `admin`, etc.) |
| `NEXT_PUBLIC_LOCAL_AUTH_DISPLAY_NAME` | Nombre visible del usuario demo |

### Si `NEXT_PUBLIC_AUTH_MODE=supabase`:
| Variable | Descripción |
|----------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | URL del proyecto Supabase |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY` | Clave pública/anónima de Supabase |

---

## Ejecución Local

```bash
cd frontend/web
npm install
npm run dev
```

La aplicación estará disponible en `http://localhost:3000`.

Para desarrollo con el backend completo, consulta el [`README.md`](../../README.md) principal.

---

## API / Backend

El frontend se comunica con el backend FastAPI a través del cliente definido en `lib/api.ts`.

**Endpoints consumidos:**
- `POST /auth/login` — Inicio de sesión
- `POST /auth/register` — Registro
- `GET /audio/me` — Audios del usuario
- `POST /audio/upload` — Subir audio
- `POST /audio/{id}/process` — Procesar audio
- `GET /audio/{id}/features` — Obtener biomarcadores
- `GET /audio/{id}` — Detalle de audio

---

## Notas de Desarrollo

- Los componentes siguen el patrón **Atomic Design** (átomos → moléculas → organismos → templates).
- Las páginas dentro de `(private)/` están protegidas por el middleware y envueltas en el `PrivateShell`.
- La grabación de audio usa `MediaRecorder` con el formato por defecto del navegador y luego se convierte a WAV.
- Para agregar un nuevo idioma, crear el diccionario en `lib/i18n/dictionaries/` e importarlo en `config.ts`.

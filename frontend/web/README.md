# MedDiag Web (Next.js)

Frontend para autenticacion y rutas privadas usando Supabase o modo local de desarrollo.

## Documentacion

- [Guia de integracion Frontend/API](./FRONTEND_API_INTEGRATION.md)

## Variables de entorno

Se usa `.env.local` con:

- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_AUTH_MODE`
- `NEXT_PUBLIC_LOCAL_AUTH_EMAIL`
- `NEXT_PUBLIC_LOCAL_AUTH_PASSWORD`
- `NEXT_PUBLIC_LOCAL_AUTH_ROLE`
- `NEXT_PUBLIC_LOCAL_AUTH_DISPLAY_NAME`

Si `NEXT_PUBLIC_AUTH_MODE=local`, no necesitas Supabase para desarrollo local.

Si `NEXT_PUBLIC_AUTH_MODE` no es `local`, entonces tambien necesitas:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY`

El cliente tambien soporta fallback a `NEXT_PUBLIC_SUPABASE_ANON_KEY` si se define.

## Ejecutar

```bash
cd frontend/web
npm install
npm run dev
```

Aplicacion en `http://localhost:3000`.

## Rutas

- `/login`
- `/register`
- `/dashboard` (privada)
- `/auth/callback` (OAuth callback)

## Integracion backend

La pagina privada consulta `GET /audio/me` enviando `Authorization: Bearer <access_token>`.

Asegurate de que el backend este con una de estas configuraciones:

- Modo local:
  - `AUTH_PROVIDER=local`
  - `ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000`
- Modo Supabase:
  - `AUTH_PROVIDER=supabase`
  - `SUPABASE_JWT_SECRET=<jwt secret del proyecto>`
  - `ALLOWED_ORIGINS=http://localhost:3000`

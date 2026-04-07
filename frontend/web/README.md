# MedDiag Web (Next.js + Supabase)

Frontend nuevo para autenticación y rutas privadas usando Supabase.

## Documentacion

- [Guia de integracion Frontend/API](./FRONTEND_API_INTEGRATION.md)

## Variables de entorno

Se usa [.env.local](.env.local) con:

- NEXT_PUBLIC_SUPABASE_URL
- NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY
- NEXT_PUBLIC_API_BASE_URL

El cliente también soporta fallback a NEXT_PUBLIC_SUPABASE_ANON_KEY si se define.

## Ejecutar

```bash
cd frontend/web
npm install
npm run dev
```

Aplicación en http://localhost:3000.

## Rutas

- /login
- /register
- /dashboard (privada)
- /auth/callback (OAuth callback)

## Integración backend

La página privada consulta `GET /audio/me` enviando `Authorization: Bearer <access_token>`.

Asegúrate de que el backend esté con:

- AUTH_PROVIDER=supabase
- SUPABASE_JWT_SECRET=<jwt secret del proyecto>
- ALLOWED_ORIGINS=http://localhost:3000

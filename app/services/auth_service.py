"""
Servicio de autenticación: resuelve un token Bearer a un usuario local.

Soporta dos proveedores controlados por la variable de entorno AUTH_PROVIDER:
  • local: firma y verifica JWT con JWT_SECRET_KEY (desarrollo / pruebas)
  • supabase: verifica JWT firmados por Supabase usando SUPABASE_JWT_SECRET
"""

import os
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt
from sqlalchemy.orm import Session

from app.models import Role, User, UserRole
from app.utils.database import SessionLocal

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

AUTH_PROVIDER = os.getenv("AUTH_PROVIDER", "local")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_JWKS_URL = os.getenv("SUPABASE_JWKS_URL", "").strip() or (
    f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json" if SUPABASE_URL else ""
)
SUPABASE_ISSUER = f"{SUPABASE_URL}/auth/v1" if SUPABASE_URL else ""
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))
SUPABASE_JWKS_CACHE_SECONDS = int(os.getenv("SUPABASE_JWKS_CACHE_SECONDS", "600"))

security = HTTPBearer()

_JWKS_CACHE: dict[str, object] = {"fetched_at": 0.0, "jwks": None}

# ---------------------------------------------------------------------------
# Utilidades de token
# ---------------------------------------------------------------------------


def create_dev_token(
    sub: str,
    email: str,
    roles: List[str],
    display_name: Optional[str] = None,
) -> str:
    """Crea un JWT para desarrollo/pruebas locales."""
    payload = {
        "sub": sub,
        "email": email,
        "roles": roles,
        "display_name": display_name or email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRATION_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    """Decodifica y verifica un JWT usando el proveedor configurado."""
    # Soporte para tokens simulados "dev_*" cuando AUTH_PROVIDER=local
    # Esto permite que el frontend en Vercel use autenticación local sin JWT real
    if AUTH_PROVIDER == "local" and token.startswith("dev_"):
        try:
            import base64
            import json

            payload_b64 = token[len("dev_"):]
            decoded_bytes = base64.b64decode(payload_b64)
            payload = json.loads(decoded_bytes.decode("utf-8"))
            return {
                "sub": payload.get("email", "dev@local"),
                "email": payload.get("email", "dev@local"),
                "roles": [payload.get("role", "patient")],
                "display_name": payload.get("email", "dev@local"),
            }
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de desarrollo inválido.",
            )

    try:
        if AUTH_PROVIDER == "supabase":
            header = jwt.get_unverified_header(token)
            alg = header.get("alg")

            if alg in {"ES256", "RS256"}:
                if not SUPABASE_JWKS_URL or not SUPABASE_ISSUER:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="SUPABASE_URL es requerido para verificar las claves de firma de Supabase.",
                    )

                jwks = _load_supabase_jwks()
                verification_key = _select_jwks_key(jwks, header)
                payload = jwt.decode(
                    token,
                    verification_key,
                    algorithms=[alg],
                    issuer=SUPABASE_ISSUER,
                    audience="authenticated",
                )
            else:
                secret = SUPABASE_JWT_SECRET
                if not secret:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="SUPABASE_JWT_SECRET no está configurado para la validación JWT heredada de Supabase.",
                    )
                payload = jwt.decode(token, secret, algorithms=[alg or JWT_ALGORITHM])
        else:
            secret = JWT_SECRET_KEY
            payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido o expirado: {exc}",
        )

    return payload


def _load_supabase_jwks() -> dict:
    now = time.time()
    cached_jwks = _JWKS_CACHE["jwks"]
    fetched_at = float(_JWKS_CACHE["fetched_at"])

    if cached_jwks and now - fetched_at < SUPABASE_JWKS_CACHE_SECONDS:
        return cached_jwks  # type: ignore[return-value]

    try:
        response = requests.get(SUPABASE_JWKS_URL, timeout=5)
        response.raise_for_status()
        jwks = response.json()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No se pudo cargar JWKS de Supabase: {exc}",
        )

    if not isinstance(jwks, dict) or "keys" not in jwks:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Se recibió un documento JWKS inválido desde Supabase.",
        )

    _JWKS_CACHE["jwks"] = jwks
    _JWKS_CACHE["fetched_at"] = now
    return jwks


def _select_jwks_key(jwks: dict, header: dict) -> object:
    kid = header.get("kid")
    keys = jwks.get("keys", [])

    selected_key = None
    if kid:
        for key in keys:
            if key.get("kid") == kid:
                selected_key = key
                break
    elif len(keys) == 1:
        selected_key = keys[0]

    if not selected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se encontró una clave de firma de Supabase compatible con este token.",
        )

    try:
        key_obj = jwk.construct(selected_key)
        if hasattr(key_obj, "to_pem"):
            return key_obj.to_pem()
        return key_obj
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"No se pudo construir la clave de verificación: {exc}",
        )


# ---------------------------------------------------------------------------
# Resolución de usuario
# ---------------------------------------------------------------------------


def _get_or_create_user_from_token(db: Session, payload: dict) -> User:
    """Busca o crea el usuario local que corresponde al contenido del token."""
    sub = payload.get("sub")
    email = payload.get("email")
    display_name = payload.get("display_name") or email
    provider = AUTH_PROVIDER

    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token no incluye la declaración 'sub'.",
        )

    # Busca por (auth_provider, auth_subject).
    user = (
        db.query(User)
        .filter(User.auth_provider == provider, User.auth_subject == sub)
        .first()
    )

    if not user and email:
        # Pueden existir filas heredadas con este correo pero sin auth_subject.
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.auth_provider = provider
            user.auth_subject = sub
            user.display_name = user.display_name or display_name
            user.name = user.name or display_name
            user.is_active = True
            db.flush()

    if not user:
        user = User(
            auth_provider=provider,
            auth_subject=sub,
            email=email,
            display_name=display_name,
            name=display_name,
            is_active=True,
        )
        db.add(user)
        db.flush()

    # Asigna el rol predeterminado desde el token (o "patient") solo si falta.
    token_roles = payload.get("roles", ["patient"])
    existing_role_ids = {
        ur.role_id
        for ur in db.query(UserRole).filter(UserRole.user_id == user.id).all()
    }
    for role_code in token_roles:
        role = db.query(Role).filter(Role.code == role_code).first()
        if role and role.id not in existing_role_ids:
            db.add(UserRole(user_id=user.id, role_id=role.id))

    db.commit()

    return user


# ---------------------------------------------------------------------------
# Dependencias de FastAPI
# ---------------------------------------------------------------------------


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Dependencia: extrae el token Bearer, lo decodifica y devuelve un usuario."""
    payload = _decode_token(credentials.credentials)
    return _get_or_create_user_from_token(db, payload)


def _get_user_role_codes(db: Session, user: User) -> List[str]:
    """Devuelve la lista de códigos de rol asignados a un usuario."""
    return [
        ur.role.code
        for ur in db.query(UserRole).filter(UserRole.user_id == user.id).all()
    ]


def require_role(role_code: str):
    """Factory de dependencia: el usuario actual debe tener un rol específico."""

    def _check(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        codes = _get_user_role_codes(db, user)
        if role_code not in codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere el rol '{role_code}'.",
            )
        return user

    return _check


def require_any_role(role_codes: List[str]):
    """Factory de dependencia: el usuario actual debe tener al menos uno de los roles."""

    def _check(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        codes = _get_user_role_codes(db, user)
        if not set(role_codes) & set(codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere uno de estos roles: {role_codes}.",
            )
        return user

    return _check

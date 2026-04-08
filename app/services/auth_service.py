"""
Authentication service — resolves a Bearer token to a local User.

Supports two providers controlled by AUTH_PROVIDER env var:
  • local  – signs & verifies JWTs with JWT_SECRET_KEY  (dev / testing)
  • supabase – verifies JWTs signed by Supabase using SUPABASE_JWT_SECRET
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
# Config
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
# Token helpers
# ---------------------------------------------------------------------------


def create_dev_token(
    sub: str,
    email: str,
    roles: List[str],
    display_name: Optional[str] = None,
) -> str:
    """Create a JWT for local dev/testing."""
    payload = {
        "sub": sub,
        "email": email,
        "roles": roles,
        "display_name": display_name or email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRATION_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    """Decode and verify a JWT using the configured provider's secret."""
    try:
        if AUTH_PROVIDER == "supabase":
            header = jwt.get_unverified_header(token)
            alg = header.get("alg")

            if alg in {"ES256", "RS256"}:
                if not SUPABASE_JWKS_URL or not SUPABASE_ISSUER:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="SUPABASE_URL is required to verify Supabase signing keys.",
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
                        detail="SUPABASE_JWT_SECRET not configured for legacy Supabase JWT validation.",
                    )
                payload = jwt.decode(token, secret, algorithms=[alg or JWT_ALGORITHM])
        else:
            secret = JWT_SECRET_KEY
            payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
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
            detail=f"Failed to load Supabase JWKS: {exc}",
        )

    if not isinstance(jwks, dict) or "keys" not in jwks:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid JWKS document received from Supabase.",
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
            detail="No matching Supabase signing key found for this token.",
        )

    try:
        key_obj = jwk.construct(selected_key)
        if hasattr(key_obj, "to_pem"):
            return key_obj.to_pem()
        return key_obj
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to construct verification key: {exc}",
        )


# ---------------------------------------------------------------------------
# User resolution
# ---------------------------------------------------------------------------


def _get_or_create_user_from_token(db: Session, payload: dict) -> User:
    """Find or create the local user that matches the token payload."""
    sub = payload.get("sub")
    email = payload.get("email")
    display_name = payload.get("display_name") or email
    provider = AUTH_PROVIDER

    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing 'sub' claim.",
        )

    # Look up by (auth_provider, auth_subject)
    user = (
        db.query(User)
        .filter(User.auth_provider == provider, User.auth_subject == sub)
        .first()
    )

    if not user and email:
        # Legacy rows may already exist with this email but without auth_subject.
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

    # Assign default role from token (or "patient") only if missing.
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
# FastAPI dependencies
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
    """Dependency: extracts the Bearer token, decodes it, returns a User."""
    payload = _decode_token(credentials.credentials)
    return _get_or_create_user_from_token(db, payload)


def _get_user_role_codes(db: Session, user: User) -> List[str]:
    """Return the list of role codes assigned to a user."""
    return [
        ur.role.code
        for ur in db.query(UserRole).filter(UserRole.user_id == user.id).all()
    ]


def require_role(role_code: str):
    """Dependency factory: current user must have a specific role."""

    def _check(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        codes = _get_user_role_codes(db, user)
        if role_code not in codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role_code}' required.",
            )
        return user

    return _check


def require_any_role(role_codes: List[str]):
    """Dependency factory: current user must have at least one of the roles."""

    def _check(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        codes = _get_user_role_codes(db, user)
        if not set(role_codes) & set(codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of roles {role_codes} required.",
            )
        return user

    return _check

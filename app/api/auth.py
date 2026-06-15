"""
Endpoints de autenticación: generación de token dev e información del usuario.
"""

import os
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models import User, UserRole
from app.schemas.auth import DevTokenRequest, DevTokenResponse, LoginRequest, RegisterRequest, UserOut
from app.services.auth_service import (
    AUTH_PROVIDER,
    create_dev_token,
    get_current_user,
    get_db,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/dev/token", response_model=DevTokenResponse)
def issue_dev_token(body: DevTokenRequest):
    """
    Genera un JWT para desarrollo local o pruebas.
    Solo está disponible cuando AUTH_PROVIDER=local.
    """
    if AUTH_PROVIDER != "local":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Los tokens dev solo están disponibles cuando AUTH_PROVIDER=local.",
        )

    sub = str(_uuid.uuid4())  # UID sintético.
    token = create_dev_token(
        sub=sub,
        email=body.email,
        roles=[body.role],
        display_name=body.display_name,
    )
    return DevTokenResponse(access_token=token)


@router.post("/register", response_model=DevTokenResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Crea un usuario local con email/contraseña. Solo AUTH_PROVIDER=local."""
    if AUTH_PROVIDER != "local":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registro solo disponible cuando AUTH_PROVIDER=local.",
        )

    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El email ya está registrado.",
        )

    sub = str(_uuid.uuid4())
    display = body.display_name or body.email.split("@")[0]
    user = User(
        auth_provider="local",
        auth_subject=sub,
        email=body.email,
        display_name=display,
        name=display,
        password_hash=hash_password(body.password),
        is_active=True,
    )
    db.add(user)
    db.flush()

    from app.models import Role, UserRole
    role = db.query(Role).filter(Role.code == "patient").first()
    if role:
        db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()

    token = create_dev_token(sub=sub, email=body.email, roles=["patient"], display_name=display)
    return DevTokenResponse(access_token=token)


@router.post("/login", response_model=DevTokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Autentica con email/contraseña local. Solo AUTH_PROVIDER=local."""
    if AUTH_PROVIDER != "local":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Login local solo disponible cuando AUTH_PROVIDER=local.",
        )

    user = db.query(User).filter(User.email == body.email).first()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta inactiva.",
        )

    from app.models import UserRole
    roles = [ur.role.code for ur in db.query(UserRole).filter(UserRole.user_id == user.id).all()]
    token = create_dev_token(
        sub=user.auth_subject,
        email=user.email,
        roles=roles or ["patient"],
        display_name=user.display_name,
    )
    return DevTokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Devuelve información del usuario autenticado."""
    role_codes = [
        ur.role.code
        for ur in db.query(UserRole).filter(UserRole.user_id == current_user.id).all()
    ]
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        auth_provider=current_user.auth_provider,
        is_active=current_user.is_active,
        roles=role_codes,
    )

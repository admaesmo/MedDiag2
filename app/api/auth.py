"""
Endpoints de autenticación: generación de token dev e información del usuario.
"""

import os
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models import User, UserRole
from app.schemas.auth import DevTokenRequest, DevTokenResponse, UserOut
from app.services.auth_service import (
    AUTH_PROVIDER,
    create_dev_token,
    get_current_user,
    get_db,
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

from typing import Optional, List
from pydantic import BaseModel, Field


# ---- Token / autenticación ----

class TokenPayload(BaseModel):
    """Contenido decodificado del JWT."""
    sub: str                            # auth_subject (UID)
    email: Optional[str] = None
    roles: List[str] = []


class DevTokenRequest(BaseModel):
    """Cuerpo de solicitud para el endpoint de token de desarrollo."""
    email: str = Field(..., example="dev@meddiag.com")
    role: str = Field("patient", example="patient")
    display_name: Optional[str] = Field(None, example="Usuario Dev")


class DevTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---- Información del usuario actual ----

class UserOut(BaseModel):
    id: int
    email: Optional[str] = None
    display_name: Optional[str] = None
    auth_provider: Optional[str] = None
    is_active: bool = True
    roles: List[str] = []

    class Config:
        from_attributes = True

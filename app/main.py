import os
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.utils.database import SessionLocal, Base, engine
from app.utils import crud
from app.model_predict import (
    PARKINSON_NEGATIVE_MESSAGE,
    PARKINSON_POSITIVE_MESSAGE,
    DIABETES_FEATURE_ORDER,
    HEART_FEATURE_ORDER,
    PARK_FEATURE_ORDER,
    PARKINSON_THRESHOLD,
    predict_diabetes,
    predict_heart,
    predict_parkinson,
)
from app.models import Disease, Role, User
from app.utils.validators import validate_required_features
from app.services.auth_service import get_current_user

# Routers
from app.api.auth import router as auth_router
from app.api.voice_biomarkers import router as voice_biomarker_router
from app.api.audio import router as audio_router
from app.api.sessions import router as sessions_router

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="MedDiag API", version="2.0.0")

# ---------------------------------------------------------------------------
# CORS manual — garantiza que TODAS las respuestas (incluso errores 400/422)
# incluyan Access-Control-Allow-Origin.
# El middleware CORSMiddleware de FastAPI tiene un bug que no agrega las
# cabeceras CORS a respuestas de error (400, 422, etc.).
#
# Estrategia: devolver el origin exacto que el navegador envió (reflejado).
# Esto funciona con cualquier dominio (producción, previews de Vercel, etc.)
# y es compatible con allow_credentials=true.
# ---------------------------------------------------------------------------

class ManualCORSMiddleware(BaseHTTPMiddleware):
    """Middleware CORS que se ejecuta SIEMPRE, incluso en respuestas de error."""

    async def dispatch(self, request, call_next):
        origin = request.headers.get("origin", "")

        # Normalizar: quitar barra final del origin para evitar discrepancias
        origin = origin.rstrip("/")

        # Reflejar el origin exacto que el navegador envió.
        # Esto permite cualquier dominio (producción, previews de Vercel, etc.)
        # y es compatible con allow_credentials=true.
        if origin:
            allow_origin = origin
        else:
            allow_origin = "*"

        # Manejar preflight OPTIONS inmediatamente
        if request.method == "OPTIONS":
            response = Response()
            response.headers["Access-Control-Allow-Origin"] = allow_origin
            response.headers["Access-Control-Allow-Methods"] = "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
            response.headers["Access-Control-Max-Age"] = "600"
            if allow_origin != "*":
                response.headers["Access-Control-Allow-Credentials"] = "true"
            return response

        # BaseHTTPMiddleware NO ejecuta el resto del dispatch si call_next lanza
        # una excepción no controlada (500): Starlette responde con un 500 plano
        # SIN cabeceras CORS, y el navegador lo reporta como "CORS missing".
        # Capturamos la excepción aquí para devolver un 500 CON cabeceras CORS.
        try:
            response: Response = await call_next(request)
        except Exception as exc:  # noqa: BLE001
            import traceback
            traceback.print_exc()  # queda en los logs de Render
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal Server Error", "error": str(exc)},
            )

        # Agregar cabeceras CORS a TODAS las respuestas (incluso errores)
        response.headers["Access-Control-Allow-Origin"] = allow_origin
        response.headers["Access-Control-Allow-Methods"] = "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        response.headers["Access-Control-Max-Age"] = "600"

        # allow_credentials solo si no es "*"
        if allow_origin != "*":
            response.headers["Access-Control-Allow-Credentials"] = "true"

        return response


app.add_middleware(ManualCORSMiddleware)

# ---- Register new routers ----
app.include_router(auth_router)
app.include_router(voice_biomarker_router)
app.include_router(audio_router)
app.include_router(sessions_router)


# ---- Legacy schemas (unchanged) ----

class Patient(BaseModel):
    name: str = Field(..., example="Paciente Demo")
    email: Optional[str] = Field(None, example="demo@meddiag.com")
    gender: Optional[str] = Field(None, pattern="^(M|F|O)$", example="M")
    phone_number: Optional[str] = Field(None, example="+57 3000000000")


class DiabetesRequest(BaseModel):
    patient: Patient
    features: dict


class HeartRequest(BaseModel):
    patient: Patient
    features: dict


class ParkinsonRequest(BaseModel):
    patient: Patient
    features: dict
    audio_record_id: Optional[int] = None


class DiagnosisResponse(BaseModel):
    disease_code: str
    prediction: int
    probability: float
    message: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---- Startup ----

@app.on_event("startup")
def startup_seed():
    with SessionLocal() as db:
        crud.seed_default_diseases(db)
        _seed_default_roles(db)


def _seed_default_roles(db: Session) -> None:
    """Create the default roles if they don't exist."""
    defaults = [
        ("admin", "Administrador", "Acceso operativo completo"),
        ("doctor", "Doctor", "Puede ver audios de pacientes asignados"),
        ("patient", "Paciente", "Puede subir y ver sus propios audios"),
    ]
    for code, name, desc in defaults:
        exists = db.query(Role).filter(Role.code == code).first()
        if not exists:
            db.add(Role(code=code, name=name, description=desc))
    db.commit()


# ---- Legacy endpoints (unchanged) ----

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/users")
def create_user(patient: Patient, db: Session = Depends(get_db)):
    user = crud.get_or_create_user(
        db,
        name=patient.name,
        email=patient.email,
        gender=patient.gender,
        phone_number=patient.phone_number,
    )
    db.commit()
    return {"id": user.id, "name": user.name, "email": user.email}


@app.get("/diagnoses/history")
def diagnoses_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if limit <= 0 or limit > 500:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 500")

    rows = crud.get_diagnoses_by_user_id(db, current_user.id, limit)

    def _result_for(disease_code: str, probability: float) -> str:
        threshold = PARKINSON_THRESHOLD if disease_code == "PARK" else 0.5
        return "positive" if probability >= threshold else "negative"

    return [
        {
            "id": r.id,
            "generated_at": r.generated_at,
            "status": r.status,
            "result": _result_for(r.disease_code, float(r.probability)),
            "final_description": r.final_description,
            "user_name": r.user_name,
            "user_email": r.user_email,
            "disease_name": r.disease_name,
            "disease_code": r.disease_code,
            "probability": float(r.probability),
            "audio_record_id": r.audio_record_id,
            "audio_filename": r.audio_filename,
        }
        for r in rows
    ]


def _save_and_response(
    db: Session,
    patient: Patient,
    features: dict,
    ordered_features: list,
    disease_code: str,
    predictor,
    positive_msg: str,
    negative_msg: str,
    audio_record_id: Optional[int] = None,
) -> DiagnosisResponse:
    validate_required_features(features, ordered_features)
    label, proba = predictor(features)
    message = positive_msg if label == 1 else negative_msg

    user = crud.get_or_create_user(
        db,
        name=patient.name,
        email=patient.email,
        gender=patient.gender,
        phone_number=patient.phone_number,
    )

    crud.create_diagnosis_with_single_candidate(
        db=db,
        user_id=user.id,
        disease_code=disease_code,
        probability=proba,
        final_description=message,
        audio_record_id=audio_record_id,
    )
    db.commit()

    return DiagnosisResponse(
        disease_code=disease_code,
        prediction=label,
        probability=proba,
        message=message,
    )


@app.post("/predict/diabetes", response_model=DiagnosisResponse)
def predict_diabetes_endpoint(payload: DiabetesRequest, db: Session = Depends(get_db)):
    return _save_and_response(
        db=db,
        patient=payload.patient,
        features=payload.features,
        ordered_features=DIABETES_FEATURE_ORDER,
        disease_code="DIAB",
        predictor=predict_diabetes,
        positive_msg="La persona puede ser diabética, consulte a su médico.",
        negative_msg="La persona no es diabética.",
    )


@app.post("/predict/heart", response_model=DiagnosisResponse)
def predict_heart_endpoint(payload: HeartRequest, db: Session = Depends(get_db)):
    return _save_and_response(
        db=db,
        patient=payload.patient,
        features=payload.features,
        ordered_features=HEART_FEATURE_ORDER,
        disease_code="HEART",
        predictor=predict_heart,
        positive_msg="La persona puede ser cardiaca, consulte a su médico.",
        negative_msg="La persona no es cardiaca.",
    )


@app.post("/predict/parkinson", response_model=DiagnosisResponse)
def predict_parkinson_endpoint(payload: ParkinsonRequest, db: Session = Depends(get_db)):
    return _save_and_response(
        db=db,
        patient=payload.patient,
        features=payload.features,
        ordered_features=PARK_FEATURE_ORDER,
        disease_code="PARK",
        predictor=predict_parkinson,
        positive_msg=PARKINSON_POSITIVE_MESSAGE,
        negative_msg=PARKINSON_NEGATIVE_MESSAGE,
        audio_record_id=payload.audio_record_id,
    )

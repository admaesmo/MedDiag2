import os
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.utils.database import SessionLocal, Base, engine
from app.utils import crud
from app.model_predict import (
    DIABETES_FEATURE_ORDER,
    HEART_FEATURE_ORDER,
    PARK_FEATURE_ORDER,
    predict_diabetes,
    predict_heart,
    predict_parkinson,
)
from app.models import Disease
from app.utils.validators import validate_required_features

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="MedDiag API", version="1.0.0")

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in allowed_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.on_event("startup")
def startup_seed():
    with SessionLocal() as db:
        crud.seed_default_diseases(db)


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
    name: Optional[str] = None,
    email: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    if limit <= 0 or limit > 500:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 500")

    if name:
        rows = crud.get_diagnoses_by_user_name(db, name, limit)
    elif email:
        rows = crud.get_diagnoses_by_user_email(db, email, limit)
    else:
        rows = crud.get_recent_diagnoses(db, limit)

    return [
        {
            "id": r.id,
            "generated_at": r.generated_at,
            "status": r.status,
            "final_description": r.final_description,
            "user_name": r.user_name,
            "user_email": r.user_email,
            "disease_name": r.disease_name,
            "disease_code": r.disease_code,
            "probability": float(r.probability),
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
        positive_msg="La persona puede tener Parkinson, consulte a su médico.",
        negative_msg="La persona no tiene Parkinson.",
    )

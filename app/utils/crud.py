from sqlalchemy.orm import Session
from app.models import User, Disease, Diagnosis, DiagnosisDetail
from app.utils.validators import validate_probability


def get_or_create_user(
    db: Session,
    name: str,
    email: str | None = None,
    gender: str | None = None,
    phone_number: str | None = None,
) -> User:
    user = None
    if email:
        user = db.query(User).filter(User.email == email).first()

    if not user:
        user = User(
            name=name or "Paciente sin nombre",
            email=email,
            gender=gender,
            phone_number=phone_number,
        )
        db.add(user)
        db.flush()
    return user


def seed_default_diseases(db: Session) -> None:
    defaults = [
        ("DIAB", "Riesgo de Diabetes (modelo ML)", "Modelo basado en dataset Pima."),
        ("HEART", "Riesgo de Enfermedad Cardíaca", "Modelo basado en dataset UCI Heart."),
        ("PARK", "Riesgo de Parkinson", "Modelo basado en parámetros de voz."),
    ]
    for code, name, desc in defaults:
        exists = db.query(Disease).filter(Disease.disease_code == code).first()
        if not exists:
            db.add(Disease(disease_code=code, name=name, description=desc))
    db.commit()


def create_diagnosis_with_single_candidate(
    db: Session,
    user_id: int,
    disease_code: str,
    probability: float,
    final_description: str,
) -> Diagnosis:
    disease = db.query(Disease).filter(Disease.disease_code == disease_code).first()
    if not disease:
        raise ValueError(f"Disease with code {disease_code} not found")

    diagnosis = Diagnosis(user_id=user_id, final_description=final_description, status="pending")
    db.add(diagnosis)
    db.flush()

    detail = DiagnosisDetail(
        diagnosis_id=diagnosis.id,
        disease_id=disease.id,
        probability=validate_probability(probability),
    )
    db.add(detail)
    return diagnosis


def get_recent_diagnoses(db: Session, limit: int = 50):
    query = (
        db.query(
            Diagnosis.id,
            Diagnosis.generated_at,
            Diagnosis.status,
            Diagnosis.final_description,
            User.name.label("user_name"),
            User.email.label("user_email"),
            Disease.name.label("disease_name"),
            Disease.disease_code,
            DiagnosisDetail.probability,
        )
        .join(User, Diagnosis.user_id == User.id)
        .join(DiagnosisDetail, DiagnosisDetail.diagnosis_id == Diagnosis.id)
        .join(Disease, DiagnosisDetail.disease_id == Disease.id)
        .order_by(Diagnosis.generated_at.desc())
        .limit(limit)
    )
    return query.all()


def get_diagnoses_by_user_email(db: Session, email: str, limit: int = 50):
    query = (
        db.query(
            Diagnosis.id,
            Diagnosis.generated_at,
            Diagnosis.status,
            Diagnosis.final_description,
            User.name.label("user_name"),
            User.email.label("user_email"),
            Disease.name.label("disease_name"),
            Disease.disease_code,
            DiagnosisDetail.probability,
        )
        .join(User, Diagnosis.user_id == User.id)
        .join(DiagnosisDetail, DiagnosisDetail.diagnosis_id == Diagnosis.id)
        .join(Disease, DiagnosisDetail.disease_id == Disease.id)
        .filter(User.email == email)
        .order_by(Diagnosis.generated_at.desc())
        .limit(limit)
    )
    return query.all()


def get_diagnoses_by_user_name(db: Session, name: str, limit: int = 50):
    query = (
        db.query(
            Diagnosis.id,
            Diagnosis.generated_at,
            Diagnosis.status,
            Diagnosis.final_description,
            User.name.label("user_name"),
            User.email.label("user_email"),
            Disease.name.label("disease_name"),
            Disease.disease_code,
            DiagnosisDetail.probability,
        )
        .join(User, Diagnosis.user_id == User.id)
        .join(DiagnosisDetail, DiagnosisDetail.diagnosis_id == Diagnosis.id)
        .join(Disease, DiagnosisDetail.disease_id == Disease.id)
        .filter(User.name == name)
        .order_by(Diagnosis.generated_at.desc())
        .limit(limit)
    )
    return query.all()

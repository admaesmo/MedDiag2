# crud.py
from sqlalchemy.orm import Session
from models import User, Disease, Diagnosis, DiagnosisDetail

# 1) Usuario: crear o reutilizar
def get_or_create_user(db: Session, name: str, email: str = None,
                       age: int = None, gender: str = None,
                       phone_number: str = None) -> User:
    user = None
    if email:
        user = db.query(User).filter(User.email == email).first()

    if not user:
        user = User(
            name=name or "Paciente sin nombre",
            email=email,
            age=age,
            gender=gender,
            phone_number=phone_number
        )
        db.add(user)
        db.flush()  # para obtener user.id
    return user

# 2) Seed básico de enfermedades ligadas a tus 3 modelos
def seed_default_diseases(db: Session):
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

# 3) Crear diagnóstico + detalle (versión simple: 1 enfermedad candidata)
def create_diagnosis_with_single_candidate(
    db: Session,
    user_id: int,
    disease_code: str,
    probability: float,
    final_description: str
) -> Diagnosis:
    disease = db.query(Disease).filter(Disease.disease_code == disease_code).first()
    if not disease:
        raise ValueError(f"Disease with code {disease_code} not found")

    diagnosis = Diagnosis(
        user_id=user_id,
        final_description=final_description,
        status="pending"
    )
    db.add(diagnosis)
    db.flush()  # genera diagnosis.id

    detail = DiagnosisDetail(
        diagnosis_id=diagnosis.id,
        disease_id=disease.id,
        probability=round(float(probability), 4)
    )
    db.add(detail)

    return diagnosis

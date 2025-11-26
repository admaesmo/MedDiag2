# seed_dummy_data.py
from datetime import datetime, timedelta
import random

from database import SessionLocal, engine
from models import Base, User
from crud import seed_default_diseases, get_or_create_user, create_diagnosis_with_single_candidate

def seed():
    # Asegurarse de que las tablas existen
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Asegurar enfermedades base DIAB / HEART / PARK
        seed_default_diseases(db)

        # ---------- 1. Crear algunos usuarios dummy ----------
        usuarios_demo = [
            {
                "name": "Juan Pérez",
                "email": "juan.perez@example.com",
                "age": 32,
                "gender": "M",
                "phone_number": "3001234567",
            },
            {
                "name": "María López",
                "email": "maria.lopez@example.com",
                "age": 59,
                "gender": "F",
                "phone_number": "3009876543",
            },
            {
                "name": "Carlos Gómez",
                "email": "carlos.gomez@example.com",
                "age": 45,
                "gender": "M",
                "phone_number": "3015556677",
            },
        ]

        users = []
        for u in usuarios_demo:
            user = get_or_create_user(
                db,
                name=u["name"],
                email=u["email"],
                age=u["age"],
                gender=u["gender"],
                phone_number=u["phone_number"],
            )
            users.append(user)

        # ---------- 2. Crear diagnósticos dummy por usuario ----------
        # Probabilidades de ejemplo
        probs_diab = [0.15, 0.82, 0.35]
        probs_heart = [0.10, 0.76, 0.40]
        probs_park = [0.05, 0.60, 0.20]

        mensajes_diab = [
            "Bajo riesgo estimado de diabetes según el modelo.",
            "Riesgo elevado de diabetes, se recomienda evaluación médica.",
            "Riesgo intermedio de diabetes según variables clínicas.",
        ]
        mensajes_heart = [
            "Modelo sugiere bajo riesgo de enfermedad cardíaca.",
            "Modelo indica riesgo importante de enfermedad cardíaca.",
            "Modelo sugiere riesgo moderado de enfermedad cardíaca.",
        ]
        mensajes_park = [
            "Patrones vocales compatibles con voz sana.",
            "Modelo detecta patrones compatibles con Parkinson.",
            "Patrones vocales con ligeras alteraciones, seguimiento sugerido.",
        ]

        # Creamos 1 diagnóstico de cada tipo por usuario
        now = datetime.utcnow()
        for idx, user in enumerate(users):
            # Diabetes
            diag_diab = create_diagnosis_with_single_candidate(
                db=db,
                user_id=user.id,
                disease_code="DIAB",
                probability=probs_diab[idx],
                final_description=mensajes_diab[idx],
            )
            diag_diab.generated_at = now - timedelta(days=7 - idx)

            # Heart
            diag_heart = create_diagnosis_with_single_candidate(
                db=db,
                user_id=user.id,
                disease_code="HEART",
                probability=probs_heart[idx],
                final_description=mensajes_heart[idx],
            )
            diag_heart.generated_at = now - timedelta(days=4 - idx)

            # Parkinson
            diag_park = create_diagnosis_with_single_candidate(
                db=db,
                user_id=user.id,
                disease_code="PARK",
                probability=probs_park[idx],
                final_description=mensajes_park[idx],
            )
            diag_park.generated_at = now - timedelta(days=2 - idx)

        db.commit()
        print("Datos dummy insertados correctamente en meddiag.db")
    except Exception as e:
        db.rollback()
        print(f"Error insertando datos dummy: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()

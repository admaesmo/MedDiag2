# models.py
from sqlalchemy import (
    Column, Integer, String, Text,
    Numeric, ForeignKey, CheckConstraint, UniqueConstraint,
    DateTime
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    phone_number = Column(Text)
    age = Column(Integer, CheckConstraint("age BETWEEN 0 AND 120"))
    gender = Column(String(1), CheckConstraint("gender IN ('M','F','O')"))
    email = Column(Text, unique=True)

    diagnoses = relationship("Diagnosis", back_populates="user")

class Symptom(Base):
    __tablename__ = "symptoms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False, unique=True)
    description = Column(Text)

    diagnosis_symptoms = relationship("DiagnosisSymptom", back_populates="symptom")

class Disease(Base):
    __tablename__ = "diseases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    disease_code = Column(Text, nullable=False, unique=True)
    name = Column(Text, nullable=False)
    description = Column(Text)

    diagnosis_details = relationship("DiagnosisDetail", back_populates="disease")

class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(
        Text,
        nullable=False,
        server_default="pending"
    )
    final_description = Column(Text)

    __table_args__ = (
        CheckConstraint("status IN ('pending','confirmed','discarded')", name="ck_diagnosis_status"),
    )

    user = relationship("User", back_populates="diagnoses")
    details = relationship("DiagnosisDetail", back_populates="diagnosis", cascade="all, delete-orphan")
    symptoms = relationship("DiagnosisSymptom", back_populates="diagnosis", cascade="all, delete-orphan")

class DiagnosisDetail(Base):
    __tablename__ = "diagnosis_details"

    id = Column(Integer, primary_key=True, autoincrement=True)
    diagnosis_id = Column(Integer, ForeignKey("diagnoses.id", ondelete="CASCADE"), nullable=False)
    disease_id = Column(Integer, ForeignKey("diseases.id", ondelete="RESTRICT"), nullable=False)
    probability = Column(Numeric(5, 4), nullable=False)

    __table_args__ = (
        CheckConstraint("probability >= 0 AND probability <= 1", name="ck_probability_range"),
        UniqueConstraint("diagnosis_id", "disease_id", name="uq_diag_disease"),
    )

    diagnosis = relationship("Diagnosis", back_populates="details")
    disease = relationship("Disease", back_populates="diagnosis_details")

class DiagnosisSymptom(Base):
    __tablename__ = "diagnosis_symptoms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    diagnosis_id = Column(Integer, ForeignKey("diagnoses.id", ondelete="CASCADE"), nullable=False)
    symptom_id = Column(Integer, ForeignKey("symptoms.id", ondelete="RESTRICT"), nullable=False)

    __table_args__ = (
        UniqueConstraint("diagnosis_id", "symptom_id", name="uq_diag_symptom"),
    )

    diagnosis = relationship("Diagnosis", back_populates="symptoms")
    symptom = relationship("Symptom", back_populates="diagnosis_symptoms")

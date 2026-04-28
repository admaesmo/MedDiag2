import uuid as _uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    BigInteger,
    String,
    Text,
    Numeric,
    ForeignKey,
    CheckConstraint,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.utils.database import Base


# ---------------------------------------------------------------------------
# Identity & Access
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # --- legacy fields (kept for backward-compat) ---
    name = Column(Text, nullable=True)
    phone_number = Column(Text)
    gender = Column(String(1), CheckConstraint("gender IN ('M','F','O')"))
    email = Column(Text, unique=True)

    # --- new auth fields ---
    auth_provider = Column(String(50), nullable=True)   # "local", "supabase", "firebase"
    auth_subject = Column(String(255), nullable=True)    # UID from external provider
    display_name = Column(Text, nullable=True)
    email_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("auth_provider", "auth_subject", name="uq_auth_identity"),
    )

    diagnoses = relationship("Diagnosis", back_populates="user")
    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    audio_records = relationship("AudioRecord", back_populates="user", cascade="all, delete-orphan")


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)   # admin, doctor, patient
    name = Column(Text, nullable=False)
    description = Column(Text)

    users = relationship("UserRole", back_populates="role")


class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )

    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="users")


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------

class AudioRecord(Base):
    __tablename__ = "audio_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(_uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    source_type = Column(String(50), default="upload")  # upload, microphone, whatsapp
    original_filename = Column(Text)
    stored_filename = Column(Text, nullable=False)
    storage_provider = Column(String(50), nullable=False, default="local")  # local, s3
    storage_path = Column(Text, nullable=False)

    mime_type = Column(String(100))
    file_size_bytes = Column(BigInteger)
    duration_seconds = Column(Float, nullable=True)

    language_code = Column(String(10), nullable=True)
    status = Column(String(50), nullable=False, default="uploaded")
    # 2.0 flow statuses plus legacy processed/transcribed compatibility.

    transcript_text = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'uploaded','preprocessing','processing','quality_checked','rejected',"
            "'features_extracted','partial_features','inference_completed',"
            "'processed','transcribed','failed','archived'"
            ")",
            name="ck_audio_status",
        ),
    )

    user = relationship("User", back_populates="audio_records")
    quality_reports = relationship("AudioQualityReport", back_populates="audio_record", cascade="all, delete-orphan")
    biomarker_features = relationship("BiomarkerFeature", back_populates="audio_record", cascade="all, delete-orphan")


class AudioQualityReport(Base):
    __tablename__ = "audio_quality_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    audio_record_id = Column(Integer, ForeignKey("audio_records.id", ondelete="CASCADE"), nullable=False)

    quality_score = Column(Float, nullable=False)
    is_valid = Column(Boolean, nullable=False, default=False)
    quality_status = Column(String(50), nullable=False, default="invalid")
    noise_level = Column(Float, nullable=True)
    clipping = Column(Float, nullable=True)
    silence_ratio = Column(Float, nullable=True)
    rms = Column(Float, nullable=True)
    peak_amplitude = Column(Float, nullable=True)
    stability_score = Column(Float, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    metrics_json = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("quality_score >= 0 AND quality_score <= 1", name="ck_audio_quality_score_range"),
        CheckConstraint("quality_status IN ('valid','low_quality','invalid')", name="ck_audio_quality_status"),
    )

    audio_record = relationship("AudioRecord", back_populates="quality_reports")


class BiomarkerFeature(Base):
    __tablename__ = "biomarker_features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    audio_record_id = Column(Integer, ForeignKey("audio_records.id", ondelete="CASCADE"), nullable=False)

    extractor_version = Column(String(50), nullable=False)
    feature_schema_version = Column(String(50), nullable=False)
    features_json = Column(JSON, nullable=False)
    feature_status = Column(String(50), nullable=False, default="complete")
    ready_for_inference = Column(Boolean, nullable=False, default=False)
    missing_features_json = Column(JSON, nullable=True)
    invalid_features_json = Column(JSON, nullable=True)
    diagnosis_id = Column(Integer, ForeignKey("diagnoses.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("feature_status IN ('complete','partial','failed')", name="ck_biomarker_feature_status"),
    )

    audio_record = relationship("AudioRecord", back_populates="biomarker_features")
    diagnosis = relationship("Diagnosis")


# ---------------------------------------------------------------------------
# Clinical (unchanged)
# ---------------------------------------------------------------------------

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
    status = Column(Text, nullable=False, server_default="pending")
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

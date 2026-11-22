"""New local study domain schema, managed exclusively through Alembic."""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declarative_base, relationship


DomainBase = declarative_base()


class Subject(DomainBase):
    __tablename__ = "subjects"
    __table_args__ = (UniqueConstraint("slug", name="uq_subjects_slug"),)

    id = Column(Integer, primary_key=True)
    slug = Column(String(40), nullable=False)
    name = Column(String(80), nullable=False)
    icon = Column(String(16), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    topics = relationship("Topic", back_populates="subject", cascade="all, delete-orphan")
    blueprints = relationship("Blueprint", back_populates="subject", cascade="all, delete-orphan")
    exams = relationship("Exam", back_populates="subject")


class Topic(DomainBase):
    __tablename__ = "topics"
    __table_args__ = (UniqueConstraint("subject_id", "code", name="uq_topics_subject_code"),)

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(Integer, ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    code = Column(String(80), nullable=False)
    name = Column(String(240), nullable=False)
    grade = Column(Integer, nullable=False)
    reference = Column(Text, nullable=True)
    subject = relationship("Subject", back_populates="topics")
    parent = relationship("Topic", remote_side=[id], back_populates="children")
    children = relationship("Topic", back_populates="parent")


class Blueprint(DomainBase):
    __tablename__ = "blueprints"
    __table_args__ = (UniqueConstraint("subject_id", "code", name="uq_blueprints_subject_code"),)

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(80), nullable=False)
    name = Column(String(200), nullable=False)
    exam_category = Column(String(40), nullable=False)
    subject = relationship("Subject", back_populates="blueprints")
    versions = relationship("BlueprintVersion", back_populates="blueprint", cascade="all, delete-orphan")


class BlueprintVersion(DomainBase):
    __tablename__ = "blueprint_versions"
    __table_args__ = (UniqueConstraint("blueprint_id", "version", name="uq_blueprint_versions_version"),)

    id = Column(Integer, primary_key=True)
    blueprint_id = Column(Integer, ForeignKey("blueprints.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    status = Column(String(24), nullable=False, default="active")
    source_filename = Column(String(255), nullable=False)
    source_sha256 = Column(String(64), nullable=False)
    rules = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    blueprint = relationship("Blueprint", back_populates="versions")


class Exam(DomainBase):
    __tablename__ = "exams"
    __table_args__ = (
        Index("ix_exams_subject_category_year", "subject_id", "category", "exam_year"),
        Index("ix_exams_fingerprint", "fingerprint"),
    )

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    blueprint_version_id = Column(Integer, ForeignKey("blueprint_versions.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(300), nullable=False)
    category = Column(String(40), nullable=False)
    status = Column(String(24), nullable=False, default="draft")
    provenance_status = Column(String(24), nullable=False, default="unverified")
    max_score = Column(Float, nullable=False, default=10.0)
    scoring_config = Column(JSON, nullable=False, default=dict)
    exam_year = Column(Integer, nullable=True)
    semester = Column(String(16), nullable=True)
    exam_month = Column(Integer, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    province = Column(String(120), nullable=True)
    school_name = Column(String(240), nullable=True)
    total_questions = Column(Integer, nullable=False, default=0)
    fingerprint = Column(String(64), nullable=True)
    fingerprint_version = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    subject = relationship("Subject", back_populates="exams")
    questions = relationship("ExamQuestionLink", back_populates="exam", cascade="all, delete-orphan", order_by="ExamQuestionLink.position")
    sources = relationship("SourceRecord", back_populates="exam")
    attempts = relationship("ExamAttempt", back_populates="exam", cascade="all, delete-orphan")


class Question(DomainBase):
    __tablename__ = "questions"
    __table_args__ = (Index("ix_questions_fingerprint", "fingerprint"),)

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    question_type = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)
    answer = Column(JSON, nullable=True)
    answer_status = Column(String(24), nullable=False, default="unknown")
    explanation = Column(Text, nullable=True)
    difficulty = Column(String(24), nullable=True)
    cognitive_level = Column(String(24), nullable=True)
    assessment_breakdown = Column(JSON, nullable=True)
    fingerprint = Column(String(64), nullable=True)
    fingerprint_version = Column(Integer, nullable=True)
    content_origin = Column(String(24), nullable=False, default="user_import")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    exam_links = relationship("ExamQuestionLink", back_populates="question")
    sources = relationship("SourceRecord", back_populates="question")


class ExamQuestionLink(DomainBase):
    __tablename__ = "exam_question_links"
    __table_args__ = (
        UniqueConstraint("exam_id", "position", name="uq_exam_question_links_position"),
        UniqueConstraint("exam_id", "question_id", name="uq_exam_question_links_question"),
    )

    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False)
    position = Column(Integer, nullable=False)
    section = Column(String(80), nullable=True)
    points = Column(Float, nullable=True)
    exam = relationship("Exam", back_populates="questions")
    question = relationship("Question", back_populates="exam_links")


class SourceRecord(DomainBase):
    __tablename__ = "source_records"
    __table_args__ = (Index("ix_source_records_sha256", "sha256"),)

    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="SET NULL"), nullable=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="SET NULL"), nullable=True)
    source_kind = Column(String(24), nullable=False)
    source_url = Column(Text, nullable=True)
    original_filename = Column(String(255), nullable=True)
    sha256 = Column(String(64), nullable=True)
    content_fingerprint = Column(String(64), nullable=True)
    fingerprint_version = Column(Integer, nullable=True)
    raw_file_path = Column(Text, nullable=True)
    raw_text = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    imported_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    exam = relationship("Exam", back_populates="sources")
    question = relationship("Question", back_populates="sources")


class ImportJob(DomainBase):
    __tablename__ = "import_jobs"

    id = Column(Integer, primary_key=True)
    source_kind = Column(String(24), nullable=False)
    input_reference = Column(Text, nullable=True)
    status = Column(String(24), nullable=False, default="queued")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    staged_exams = relationship("StagedExam", back_populates="job", cascade="all, delete-orphan")


class StagedExam(DomainBase):
    __tablename__ = "staged_exams"

    id = Column(Integer, primary_key=True)
    import_job_id = Column(Integer, ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False)
    source_record_id = Column(Integer, ForeignKey("source_records.id", ondelete="RESTRICT"), nullable=True, unique=True)
    raw_payload = Column(Text, nullable=True)
    extracted_data = Column(JSON, nullable=True)
    warnings = Column(JSON, nullable=False, default=list)
    status = Column(String(24), nullable=False, default="needs_review")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    job = relationship("ImportJob", back_populates="staged_exams")
    source_record = relationship("SourceRecord")


class DuplicateCandidate(DomainBase):
    __tablename__ = "duplicate_candidates"
    __table_args__ = (UniqueConstraint("left_kind", "left_id", "right_kind", "right_id", name="uq_duplicate_candidates_pair"),)

    id = Column(Integer, primary_key=True)
    left_kind = Column(String(16), nullable=False)
    left_id = Column(Integer, nullable=False)
    right_kind = Column(String(16), nullable=False)
    right_id = Column(Integer, nullable=False)
    match_kind = Column(String(16), nullable=False)
    similarity = Column(Float, nullable=True)
    status = Column(String(24), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ExamAttempt(DomainBase):
    __tablename__ = "exam_attempts"

    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    score = Column(Float, nullable=True)
    total_correct = Column(Integer, nullable=False, default=0)
    total_questions = Column(Integer, nullable=False, default=0)
    status = Column(String(24), nullable=False, default="in_progress")
    exam = relationship("Exam", back_populates="attempts")
    answers = relationship("Answer", back_populates="attempt", cascade="all, delete-orphan")


class Answer(DomainBase):
    __tablename__ = "answers"
    __table_args__ = (UniqueConstraint("attempt_id", "question_id", name="uq_answers_attempt_question"),)

    id = Column(Integer, primary_key=True)
    attempt_id = Column(Integer, ForeignKey("exam_attempts.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False)
    response = Column(JSON, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    score_earned = Column(Float, nullable=False, default=0.0)
    attempt = relationship("ExamAttempt", back_populates="answers")


class Mistake(DomainBase):
    __tablename__ = "mistakes"
    __table_args__ = (UniqueConstraint("attempt_id", "question_id", name="uq_mistakes_attempt_question"),)

    id = Column(Integer, primary_key=True)
    attempt_id = Column(Integer, ForeignKey("exam_attempts.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class GenerationJob(DomainBase):
    __tablename__ = "generation_jobs"

    id = Column(Integer, primary_key=True)
    blueprint_version_id = Column(Integer, ForeignKey("blueprint_versions.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String(24), nullable=False, default="queued")
    request_data = Column(JSON, nullable=False)
    progress_json = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    result_exam_id = Column(Integer, ForeignKey("exams.id", ondelete="SET NULL"), nullable=True)
    cancel_requested = Column(Boolean, nullable=False, default=False)
    model_name = Column(String(120), nullable=False)
    prompt_version = Column(String(40), nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    result_exam = relationship("Exam", foreign_keys=[result_exam_id])

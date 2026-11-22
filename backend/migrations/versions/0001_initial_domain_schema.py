"""Create the fresh local study domain schema.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("icon", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("slug", name="uq_subjects_slug"),
    )
    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], name="fk_topics_subject_id_subjects", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["topics.id"], name="fk_topics_parent_id_topics", ondelete="SET NULL"),
        sa.UniqueConstraint("subject_id", "code", name="uq_topics_subject_code"),
    )
    op.create_table(
        "blueprints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("exam_category", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], name="fk_blueprints_subject_id_subjects", ondelete="CASCADE"),
        sa.UniqueConstraint("subject_id", "code", name="uq_blueprints_subject_code"),
    )
    op.create_table(
        "blueprint_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("blueprint_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["blueprint_id"], ["blueprints.id"], name="fk_blueprint_versions_blueprint_id_blueprints", ondelete="CASCADE"),
        sa.UniqueConstraint("blueprint_id", "version", name="uq_blueprint_versions_version"),
    )
    op.create_table(
        "exams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("blueprint_version_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="draft", nullable=False),
        sa.Column("provenance_status", sa.String(length=24), server_default="unverified", nullable=False),
        sa.Column("exam_year", sa.Integer(), nullable=True),
        sa.Column("semester", sa.String(length=16), nullable=True),
        sa.Column("exam_month", sa.Integer(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("province", sa.String(length=120), nullable=True),
        sa.Column("school_name", sa.String(length=240), nullable=True),
        sa.Column("total_questions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=True),
        sa.Column("fingerprint_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], name="fk_exams_subject_id_subjects", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["blueprint_version_id"], ["blueprint_versions.id"], name="fk_exams_blueprint_version_id_blueprint_versions", ondelete="SET NULL"),
    )
    op.create_index("ix_exams_subject_category_year", "exams", ["subject_id", "category", "exam_year"])
    op.create_index("ix_exams_fingerprint", "exams", ["fingerprint"])
    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("question_type", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("answer", sa.JSON(), nullable=True),
        sa.Column("answer_status", sa.String(length=24), server_default="unknown", nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.String(length=24), nullable=True),
        sa.Column("cognitive_level", sa.String(length=24), nullable=True),
        sa.Column("fingerprint", sa.String(length=64), nullable=True),
        sa.Column("fingerprint_version", sa.Integer(), nullable=True),
        sa.Column("content_origin", sa.String(length=24), server_default="user_import", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], name="fk_questions_subject_id_subjects", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], name="fk_questions_topic_id_topics", ondelete="SET NULL"),
    )
    op.create_index("ix_questions_fingerprint", "questions", ["fingerprint"])
    op.create_table(
        "exam_question_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("exam_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(length=80), nullable=True),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], name="fk_exam_question_links_exam_id_exams", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], name="fk_exam_question_links_question_id_questions", ondelete="RESTRICT"),
        sa.UniqueConstraint("exam_id", "position", name="uq_exam_question_links_position"),
    )
    op.create_table(
        "source_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("exam_id", sa.Integer(), nullable=True),
        sa.Column("question_id", sa.Integer(), nullable=True),
        sa.Column("source_kind", sa.String(length=24), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("raw_file_path", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], name="fk_source_records_exam_id_exams", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], name="fk_source_records_question_id_questions", ondelete="SET NULL"),
    )
    op.create_index("ix_source_records_sha256", "source_records", ["sha256"])
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_kind", sa.String(length=24), nullable=False),
        sa.Column("input_reference", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=24), server_default="queued", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "staged_exams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("import_job_id", sa.Integer(), nullable=False),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.Column("extracted_data", sa.JSON(), nullable=True),
        sa.Column("warnings", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("status", sa.String(length=24), server_default="needs_review", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["import_job_id"], ["import_jobs.id"], name="fk_staged_exams_import_job_id_import_jobs", ondelete="CASCADE"),
    )
    op.create_table(
        "duplicate_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("left_kind", sa.String(length=16), nullable=False),
        sa.Column("left_id", sa.Integer(), nullable=False),
        sa.Column("right_kind", sa.String(length=16), nullable=False),
        sa.Column("right_id", sa.Integer(), nullable=False),
        sa.Column("match_kind", sa.String(length=16), nullable=False),
        sa.Column("similarity", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=24), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("left_kind", "left_id", "right_kind", "right_id", name="uq_duplicate_candidates_pair"),
    )
    op.create_table(
        "exam_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("exam_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=24), server_default="in_progress", nullable=False),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], name="fk_exam_attempts_exam_id_exams", ondelete="RESTRICT"),
    )
    op.create_table(
        "answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attempt_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("response", sa.JSON(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["attempt_id"], ["exam_attempts.id"], name="fk_answers_attempt_id_exam_attempts", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], name="fk_answers_question_id_questions", ondelete="RESTRICT"),
        sa.UniqueConstraint("attempt_id", "question_id", name="uq_answers_attempt_question"),
    )
    op.create_table(
        "mistakes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attempt_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["exam_attempts.id"], name="fk_mistakes_attempt_id_exam_attempts", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], name="fk_mistakes_question_id_questions", ondelete="RESTRICT"),
        sa.UniqueConstraint("attempt_id", "question_id", name="uq_mistakes_attempt_question"),
    )
    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("blueprint_version_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="queued", nullable=False),
        sa.Column("request_data", sa.JSON(), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("prompt_version", sa.String(length=40), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["blueprint_version_id"], ["blueprint_versions.id"], name="fk_generation_jobs_blueprint_version_id_blueprint_versions", ondelete="RESTRICT"),
    )


def downgrade() -> None:
    op.drop_table("generation_jobs")
    op.drop_table("mistakes")
    op.drop_table("answers")
    op.drop_table("exam_attempts")
    op.drop_table("duplicate_candidates")
    op.drop_table("staged_exams")
    op.drop_table("import_jobs")
    op.drop_index("ix_source_records_sha256", table_name="source_records")
    op.drop_table("source_records")
    op.drop_table("exam_question_links")
    op.drop_index("ix_questions_fingerprint", table_name="questions")
    op.drop_table("questions")
    op.drop_index("ix_exams_fingerprint", table_name="exams")
    op.drop_index("ix_exams_subject_category_year", table_name="exams")
    op.drop_table("exams")
    op.drop_table("blueprint_versions")
    op.drop_table("blueprints")
    op.drop_table("topics")
    op.drop_table("subjects")

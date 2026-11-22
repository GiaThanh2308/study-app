"""Link staged imports to immutable sources and add canonical fingerprints.

Revision ID: 0004_ingestion_fingerprints
Revises: 0003_unique_exam_question_links
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_ingestion_fingerprints"
down_revision = "0003_unique_exam_question_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("source_records") as batch_op:
        batch_op.add_column(sa.Column("content_fingerprint", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("fingerprint_version", sa.Integer(), nullable=True))
    op.create_index("ix_source_records_content_fingerprint", "source_records", ["content_fingerprint"])
    with op.batch_alter_table("staged_exams") as batch_op:
        batch_op.add_column(sa.Column("source_record_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_staged_exams_source_record_id_source_records",
            "source_records",
            ["source_record_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_unique_constraint("uq_staged_exams_source_record_id", ["source_record_id"])


def downgrade() -> None:
    with op.batch_alter_table("staged_exams") as batch_op:
        batch_op.drop_constraint("uq_staged_exams_source_record_id", type_="unique")
        batch_op.drop_constraint("fk_staged_exams_source_record_id_source_records", type_="foreignkey")
        batch_op.drop_column("source_record_id")
    op.drop_index("ix_source_records_content_fingerprint", table_name="source_records")
    with op.batch_alter_table("source_records") as batch_op:
        batch_op.drop_column("fingerprint_version")
        batch_op.drop_column("content_fingerprint")

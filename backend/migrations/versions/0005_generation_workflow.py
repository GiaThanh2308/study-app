"""Persist per-prompt assessment and resumable generation jobs.

Revision ID: 0005_generation_workflow
Revises: 0004_ingestion_fingerprints
"""
from alembic import op
import sqlalchemy as sa


revision = "0005_generation_workflow"
down_revision = "0004_ingestion_fingerprints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("questions") as batch_op:
        batch_op.add_column(sa.Column("assessment_breakdown", sa.JSON(), nullable=True))

    with op.batch_alter_table("generation_jobs") as batch_op:
        batch_op.add_column(sa.Column("progress_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("output_data", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("result_exam_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("cancel_requested", sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.create_foreign_key(
            "fk_generation_jobs_result_exam_id_exams",
            "exams",
            ["result_exam_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("generation_jobs") as batch_op:
        batch_op.drop_constraint("fk_generation_jobs_result_exam_id_exams", type_="foreignkey")
        batch_op.drop_column("cancel_requested")
        batch_op.drop_column("result_exam_id")
        batch_op.drop_column("output_data")
        batch_op.drop_column("progress_json")
    with op.batch_alter_table("questions") as batch_op:
        batch_op.drop_column("assessment_breakdown")

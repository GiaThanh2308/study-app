"""Add explicit scoring data needed by catalog practice attempts.

Revision ID: 0002_practice_scoring
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_practice_scoring"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("exams") as batch_op:
        batch_op.add_column(sa.Column("max_score", sa.Float(), server_default="10.0", nullable=False))
        batch_op.add_column(sa.Column("scoring_config", sa.JSON(), server_default="{}", nullable=False))
    with op.batch_alter_table("exam_question_links") as batch_op:
        batch_op.add_column(sa.Column("points", sa.Float(), nullable=True))
    with op.batch_alter_table("exam_attempts") as batch_op:
        batch_op.add_column(sa.Column("total_correct", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("total_questions", sa.Integer(), server_default="0", nullable=False))
    with op.batch_alter_table("answers") as batch_op:
        batch_op.add_column(sa.Column("score_earned", sa.Float(), server_default="0.0", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("answers") as batch_op:
        batch_op.drop_column("score_earned")
    with op.batch_alter_table("exam_attempts") as batch_op:
        batch_op.drop_column("total_questions")
        batch_op.drop_column("total_correct")
    with op.batch_alter_table("exam_question_links") as batch_op:
        batch_op.drop_column("points")
    with op.batch_alter_table("exams") as batch_op:
        batch_op.drop_column("scoring_config")
        batch_op.drop_column("max_score")

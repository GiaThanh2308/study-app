"""Prevent listing one question more than once in the same exam.

Revision ID: 0003_unique_exam_question_links
Revises: 0002_practice_scoring
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_unique_exam_question_links"
down_revision = "0002_practice_scoring"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("exam_question_links") as batch_op:
        batch_op.create_unique_constraint(
            "uq_exam_question_links_question", ["exam_id", "question_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("exam_question_links") as batch_op:
        batch_op.drop_constraint("uq_exam_question_links_question", type_="unique")

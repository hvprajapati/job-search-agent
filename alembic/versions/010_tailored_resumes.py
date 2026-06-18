"""010_tailored_resumes table.

Revision ID: 010
Create Date: 2026-06-18
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tailored_resumes",
        sa.Column("id", PGUUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", PGUUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("base_resume_id", PGUUID(), sa.ForeignKey("resumes.id"), nullable=False),
        sa.Column("job_id", PGUUID(), sa.ForeignKey("job_postings.id"), nullable=False),
        sa.Column("job_title", sa.String(255), server_default=""),
        sa.Column("company_name", sa.String(255), server_default=""),
        sa.Column("tailored_content", JSONB(), server_default="{}"),
        sa.Column("original_content", JSONB(), server_default="{}"),
        sa.Column("strategy", sa.String(20), server_default="moderate"),
        sa.Column("diffs", JSONB(), server_default="[]"),
        sa.Column("keyword_analysis", JSONB(), nullable=True),
        sa.Column("gap_report", JSONB(), nullable=True),
        sa.Column("scores", JSONB(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("parent_version_id", PGUUID(), nullable=True),
        sa.Column("factuality_score", sa.Float(), server_default="1.0"),
        sa.Column("factuality_violations", JSONB(), server_default="[]"),
        sa.Column("generation_metadata", JSONB(), server_default="{}"),
        sa.Column("is_accepted", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_tailored_user_job", "tailored_resumes", ["user_id", "job_id"])
    op.create_index("idx_tailored_base_job", "tailored_resumes", ["base_resume_id", "job_id"])
    op.create_index("idx_tailored_user_active", "tailored_resumes", ["user_id", "is_active"])


def downgrade() -> None:
    op.drop_index("idx_tailored_user_active", table_name="tailored_resumes")
    op.drop_index("idx_tailored_base_job", table_name="tailored_resumes")
    op.drop_index("idx_tailored_user_job", table_name="tailored_resumes")
    op.drop_table("tailored_resumes")

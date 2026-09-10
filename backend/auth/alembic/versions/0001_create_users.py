"""Create users table

Revision ID: 0001
Revises:
Create Date: 2026-09-09

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

ALLOWED_USER_TYPES = [
    "fisherman",
    "coast_guard",
    "researcher",
    "maritime_operator",
    "coastal_authority",
    "other",
]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "user_type",
            sa.String(50),
            nullable=False,
            server_default="other",
        ),
        sa.Column(
            "preferred_language",
            sa.String(10),
            nullable=False,
            server_default="en",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "user_type IN ({})".format(
                ", ".join(f"'{t}'" for t in ALLOWED_USER_TYPES)
            ),
            name="ck_users_user_type",
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

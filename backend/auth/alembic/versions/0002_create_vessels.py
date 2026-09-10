"""Create vessels table

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-10

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

ALLOWED_VESSEL_TYPES = [
    "small_fishing_boat",
    "gillnetter",
    "trawler",
    "longliner",
    "purse_seiner",
    "other",
]

ALLOWED_ENGINE_TYPES = [
    "outboard",
    "inboard",
    "diesel",
    "petrol",
    "other",
]


def upgrade() -> None:
    op.create_table(
        "vessels",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "vessel_type",
            sa.String(50),
            nullable=False,
            server_default="other",
        ),
        sa.Column("length_m", sa.Float(), nullable=True),
        sa.Column("engine_type", sa.String(50), nullable=True),
        sa.Column("engine_power_hp", sa.Float(), nullable=True),
        sa.Column("cruising_speed_kmh", sa.Float(), nullable=True),
        sa.Column("fuel_capacity_l", sa.Float(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_vessels_user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "vessel_type IN ({})".format(
                ", ".join(f"'{t}'" for t in ALLOWED_VESSEL_TYPES)
            ),
            name="ck_vessels_vessel_type",
        ),
        sa.CheckConstraint(
            "engine_type IS NULL OR engine_type IN ({})".format(
                ", ".join(f"'{t}'" for t in ALLOWED_ENGINE_TYPES)
            ),
            name="ck_vessels_engine_type",
        ),
    )
    op.create_index("ix_vessels_user_id", "vessels", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_vessels_user_id", table_name="vessels")
    op.drop_table("vessels")

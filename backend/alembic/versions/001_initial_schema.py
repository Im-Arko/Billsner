"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tables created via metadata.create_all on startup; migration for production deploys
    pass


def downgrade() -> None:
    pass

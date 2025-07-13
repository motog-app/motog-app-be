"""Enable btree_gist and add geospatial index

Revision ID: a8a2016af773
Revises: 4054816307b6
Create Date: 2025-07-12 13:57:45.148698

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a8a2016af773'
down_revision: Union[str, Sequence[str], None] = '4054816307b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.create_index(
        'idx_vehicle_listings_location',
        'vehicle_listings',
        ['latitude', 'longitude'],
        unique=False,
        postgresql_using='gist'
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_vehicle_listings_location', table_name='vehicle_listings')
    op.execute("DROP EXTENSION btree_gist")

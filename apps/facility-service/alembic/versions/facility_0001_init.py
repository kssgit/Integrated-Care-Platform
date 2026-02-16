"""facility_0001_init

Create schema and tables:
- facility.facilities
- facility.facility_sync_log
"""

from alembic import op

revision = "facility_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS facility")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS facility.facilities (
          facility_id VARCHAR(64) PRIMARY KEY,
          name TEXT NOT NULL,
          address TEXT NULL,
          district VARCHAR(128) NULL,
          latitude DOUBLE PRECISION NULL,
          longitude DOUBLE PRECISION NULL,
          metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
          deleted_at TIMESTAMPTZ NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_facilities_district ON facility.facilities (district)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_facilities_deleted_at ON facility.facilities (deleted_at)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS facility.facility_sync_log (
          id BIGSERIAL PRIMARY KEY,
          provider VARCHAR(64) NOT NULL,
          sync_started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          sync_finished_at TIMESTAMPTZ NULL,
          status VARCHAR(32) NOT NULL,
          records_total INTEGER NOT NULL DEFAULT 0,
          records_success INTEGER NOT NULL DEFAULT 0,
          records_failed INTEGER NOT NULL DEFAULT 0,
          error_message TEXT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_facility_sync_log_started_at "
        "ON facility.facility_sync_log (sync_started_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS facility.facility_sync_log")
    op.execute("DROP TABLE IF EXISTS facility.facilities")

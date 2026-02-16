"""admin_0001_init

Create schema and tables:
- admin.facility_patch_audit
- admin.pipeline_run_audit
"""

from alembic import op

revision = "admin_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS "admin"')
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS admin.facility_patch_audit (
          id BIGSERIAL PRIMARY KEY,
          facility_id VARCHAR(128) NOT NULL,
          actor_user_id VARCHAR(128) NOT NULL,
          reason VARCHAR(512) NOT NULL,
          applied_fields_json TEXT NOT NULL,
          patch_json TEXT NOT NULL,
          created_at VARCHAR(64) NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_admin_facility_patch_audit_facility "
        "ON admin.facility_patch_audit (facility_id, id DESC)"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS admin.pipeline_run_audit (
          id BIGSERIAL PRIMARY KEY,
          action VARCHAR(32) NOT NULL,
          dag_id VARCHAR(255) NOT NULL,
          dag_run_id VARCHAR(255) NOT NULL,
          state VARCHAR(64) NOT NULL,
          provider VARCHAR(128) NULL,
          conf_json TEXT NOT NULL DEFAULT '{}',
          requested_by VARCHAR(128) NOT NULL,
          created_at VARCHAR(64) NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_admin_pipeline_run_audit_run "
        "ON admin.pipeline_run_audit (dag_run_id, id DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS admin.pipeline_run_audit")
    op.execute("DROP TABLE IF EXISTS admin.facility_patch_audit")

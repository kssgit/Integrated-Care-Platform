"""user_0001_init

Create schema and tables:
- user.users
- user.preferences
- integration.audit_logs
"""

from alembic import op

revision = "user_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS "user"')
    op.execute("CREATE SCHEMA IF NOT EXISTS integration")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS "user".users (
          user_id VARCHAR(64) PRIMARY KEY,
          email VARCHAR(255) NOT NULL UNIQUE,
          role VARCHAR(32) NOT NULL,
          phone_encrypted TEXT NULL,
          phone_hash VARCHAR(64) NULL,
          profile_data JSONB NOT NULL DEFAULT '{}'::jsonb,
          deleted_at TIMESTAMPTZ NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute('CREATE INDEX IF NOT EXISTS idx_user_users_phone_hash ON "user".users (phone_hash)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_user_users_deleted_at ON "user".users (deleted_at)')
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS "user".preferences (
          user_id VARCHAR(64) PRIMARY KEY,
          notification_enabled BOOLEAN NOT NULL DEFAULT TRUE,
          preferred_language VARCHAR(16) NOT NULL DEFAULT 'ko',
          extra JSONB NOT NULL DEFAULT '{}'::jsonb,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          CONSTRAINT fk_user_preferences_user
            FOREIGN KEY (user_id) REFERENCES "user".users(user_id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS integration.audit_logs (
          id BIGSERIAL PRIMARY KEY,
          actor_user_id VARCHAR(64) NULL,
          resource_type VARCHAR(64) NOT NULL,
          resource_id VARCHAR(128) NOT NULL,
          action VARCHAR(64) NOT NULL,
          ip_address VARCHAR(64) NULL,
          payload JSONB NOT NULL DEFAULT '{}'::jsonb,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_integration_audit_logs_resource "
        "ON integration.audit_logs (resource_type, resource_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_integration_audit_logs_actor "
        "ON integration.audit_logs (actor_user_id, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS integration.audit_logs")
    op.execute('DROP TABLE IF EXISTS "user".preferences')
    op.execute('DROP TABLE IF EXISTS "user".users')

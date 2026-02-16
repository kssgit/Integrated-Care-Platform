"""auth_0002_users_sso

Create auth users and sso identity tables.
"""

from alembic import op

revision = "auth_0002"
down_revision = "auth_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS auth")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth.users (
          user_id VARCHAR(255) PRIMARY KEY,
          email VARCHAR(255) NOT NULL UNIQUE,
          password_hash VARCHAR(255) NULL,
          role VARCHAR(64) NOT NULL DEFAULT 'guardian',
          auth_source VARCHAR(32) NOT NULL DEFAULT 'local',
          is_active BOOLEAN NOT NULL DEFAULT TRUE,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_auth_users_email ON auth.users (email)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth.sso_identities (
          identity_id VARCHAR(64) PRIMARY KEY,
          provider VARCHAR(32) NOT NULL,
          provider_subject VARCHAR(255) NOT NULL,
          user_id VARCHAR(255) NOT NULL REFERENCES auth.users(user_id) ON DELETE CASCADE,
          email VARCHAR(255) NULL,
          linked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          last_login_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          CONSTRAINT uq_auth_sso_provider_subject UNIQUE (provider, provider_subject)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_auth_sso_user_id ON auth.sso_identities (user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS auth.sso_identities")
    op.execute("DROP TABLE IF EXISTS auth.users")

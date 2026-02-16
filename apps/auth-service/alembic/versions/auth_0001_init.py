"""auth_0001_init

Create schema and tables:
- auth.tokens
- auth.login_attempts
"""

from alembic import op

revision = "auth_0001"
down_revision = None
branch_labels = ("auth",)
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS auth")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth.tokens (
          id BIGSERIAL PRIMARY KEY,
          user_id VARCHAR(255) NOT NULL,
          jti VARCHAR(64) NOT NULL UNIQUE,
          token_type VARCHAR(20) NOT NULL,
          issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          expires_at TIMESTAMPTZ NOT NULL,
          revoked_at TIMESTAMPTZ NULL,
          metadata JSONB NOT NULL DEFAULT '{}'::jsonb
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_auth_tokens_user_id ON auth.tokens (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_auth_tokens_expires_at ON auth.tokens (expires_at)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth.login_attempts (
          id BIGSERIAL PRIMARY KEY,
          email VARCHAR(255) NOT NULL,
          ip_address VARCHAR(64) NOT NULL,
          attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          success BOOLEAN NOT NULL DEFAULT FALSE,
          failure_reason TEXT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_auth_login_attempts_email_attempted_at "
        "ON auth.login_attempts (email, attempted_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_auth_login_attempts_ip_attempted_at "
        "ON auth.login_attempts (ip_address, attempted_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS auth.login_attempts")
    op.execute("DROP TABLE IF EXISTS auth.tokens")

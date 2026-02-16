"""user_0002_user_columns_extensible

Extend user schema for auth linkage and future profile expansion.
"""

from alembic import op

revision = "user_0002"
down_revision = "user_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('ALTER TABLE "user".users ALTER COLUMN user_id TYPE VARCHAR(255)')
    op.execute('ALTER TABLE "user".preferences ALTER COLUMN user_id TYPE VARCHAR(255)')
    op.execute("ALTER TABLE integration.audit_logs ALTER COLUMN actor_user_id TYPE VARCHAR(255)")

    op.execute('ALTER TABLE "user".users ADD COLUMN IF NOT EXISTS auth_user_id VARCHAR(255) NULL')
    op.execute('ALTER TABLE "user".users ADD COLUMN IF NOT EXISTS auth_source VARCHAR(32) NOT NULL DEFAULT \'local\'')
    op.execute('ALTER TABLE "user".users ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT \'active\'')

    op.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_user_users_auth_user_id ON "user".users (auth_user_id)')
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_users_auth_source ON \"user\".users (auth_source)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_users_status ON \"user\".users (status)")

    op.execute('UPDATE "user".users SET auth_user_id = user_id WHERE auth_user_id IS NULL')


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_user_users_status")
    op.execute("DROP INDEX IF EXISTS idx_user_users_auth_source")
    op.execute("DROP INDEX IF EXISTS idx_user_users_auth_user_id")
    op.execute('ALTER TABLE "user".users DROP COLUMN IF EXISTS status')
    op.execute('ALTER TABLE "user".users DROP COLUMN IF EXISTS auth_source')
    op.execute('ALTER TABLE "user".users DROP COLUMN IF EXISTS auth_user_id')
    op.execute("ALTER TABLE integration.audit_logs ALTER COLUMN actor_user_id TYPE VARCHAR(64)")
    op.execute('ALTER TABLE "user".preferences ALTER COLUMN user_id TYPE VARCHAR(64)')
    op.execute('ALTER TABLE "user".users ALTER COLUMN user_id TYPE VARCHAR(64)')

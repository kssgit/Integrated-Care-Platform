"""user_0003_backfill_from_auth

Backfill missing user records from auth.users into "user".users.
This migration is idempotent and safe to re-run.
"""

from alembic import op

revision = "user_0003"
down_revision = "user_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO "user".users (
          user_id,
          email,
          role,
          auth_user_id,
          auth_source,
          status,
          phone_encrypted,
          phone_hash,
          profile_data,
          deleted_at,
          created_at,
          updated_at
        )
        SELECT
          a.user_id,
          a.email,
          LEFT(a.role, 32),
          a.user_id,
          LEFT(COALESCE(NULLIF(a.auth_source, ''), 'local'), 32),
          'active',
          NULL,
          NULL,
          '{}'::jsonb,
          NULL,
          a.created_at,
          a.updated_at
        FROM auth.users a
        LEFT JOIN "user".users u
          ON u.user_id = a.user_id
          OR u.auth_user_id = a.user_id
          OR u.email = a.email
        WHERE u.user_id IS NULL
        """
    )

    op.execute(
        """
        UPDATE "user".users
        SET auth_user_id = user_id
        WHERE auth_user_id IS NULL
        """
    )


def downgrade() -> None:
    # Data reconciliation migration: no-op on downgrade.
    pass

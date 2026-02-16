"""search_0001_init

Create schema and tables:
- search.search_documents
"""

from alembic import op

revision = "search_0001"
down_revision = None
branch_labels = ("search",)
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS search")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS search.search_documents (
          document_id VARCHAR(128) PRIMARY KEY,
          source_type VARCHAR(64) NOT NULL,
          source_id VARCHAR(64) NOT NULL,
          title TEXT NOT NULL,
          content TEXT NOT NULL,
          metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_search_documents_source "
        "ON search.search_documents (source_type, source_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_search_documents_fts "
        "ON search.search_documents "
        "USING GIN (to_tsvector('simple', COALESCE(title, '') || ' ' || COALESCE(content, '')))"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS search.search_documents")

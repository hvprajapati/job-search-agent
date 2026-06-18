"""011_fix_knowledge_tsv — convert content_tsv to generated tsvector column."""
revision = "011"
down_revision = "010"

def upgrade():
    op.execute("DROP INDEX IF EXISTS idx_kchunk_tsv")
    op.execute("ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS content_tsv")
    op.execute(
        "ALTER TABLE knowledge_chunks ADD COLUMN content_tsv tsvector "
        "GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED"
    )
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_kchunk_tsv ON knowledge_chunks USING GIN (content_tsv)")

def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_kchunk_tsv")
    op.execute("ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS content_tsv")
    op.execute("ALTER TABLE knowledge_chunks ADD COLUMN content_tsv TEXT")

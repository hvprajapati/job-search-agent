"""012_384d_embeddings — update vector columns to 384d for local embeddings."""
from alembic import op

revision = "012"
down_revision = "011"


def upgrade():
    # Drop old columns and recreate with 384d (data can be regenerated)
    op.execute("ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE knowledge_chunks ADD COLUMN embedding vector(384)")
    op.execute("ALTER TABLE semantic_memories DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE semantic_memories ADD COLUMN embedding vector(384)")
    op.execute("ALTER TABLE job_postings DROP COLUMN IF EXISTS job_embedding")
    op.execute("ALTER TABLE job_postings ADD COLUMN job_embedding vector(384)")
    op.execute("ALTER TABLE profiles DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE profiles ADD COLUMN embedding vector(384)")
    op.execute("ALTER TABLE episodic_memories DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE episodic_memories ADD COLUMN embedding vector(384)")


def downgrade():
    for col_sql in [
        "ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector(3072)",
        "ALTER TABLE semantic_memories ALTER COLUMN embedding TYPE vector(3072)",
        "ALTER TABLE job_postings ALTER COLUMN job_embedding TYPE vector(3072)",
        "ALTER TABLE profiles ALTER COLUMN embedding TYPE vector(3072)",
        "ALTER TABLE episodic_memories ALTER COLUMN embedding TYPE vector(1536)",
    ]:
        op.execute(col_sql)

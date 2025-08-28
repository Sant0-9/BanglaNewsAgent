"""Initial migration with pgvector

Revision ID: a7617f2f2784
Revises: 
Create Date: 2025-08-27 12:20:25.655428

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'a7617f2f2784'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Create sources table
    op.create_table(
        'sources',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(128), nullable=False, unique=True),
        sa.Column('category', sa.String(32), nullable=False),
        sa.Column('url', sa.String(512), nullable=False),
        sa.Column('rss_url', sa.String(512), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Create articles table
    op.create_table(
        'articles',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('url', sa.String(2000), unique=True, nullable=False, index=True),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('source', sa.String(128), nullable=False),
        sa.Column('source_category', sa.String(32), nullable=False),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('inserted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Create article_vectors table
    op.create_table(
        'article_vectors',
        sa.Column('article_id', UUID(as_uuid=True), sa.ForeignKey('articles.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('embedding', sa.Text, nullable=False),  # Will use pgvector type in the final version
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Create query_logs table
    op.create_table(
        'query_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('question', sa.Text, nullable=False),
        sa.Column('answer', sa.Text, nullable=False),
        sa.Column('source_articles', sa.Text, nullable=True),
        sa.Column('response_time_ms', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Change the embedding column to use pgvector
    op.execute('ALTER TABLE article_vectors ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536)')
    
    # Create vector index using HNSW (better for higher dimensions)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_article_vectors_embedding_hnsw 
        ON article_vectors USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('query_logs')
    op.drop_table('article_vectors')
    op.drop_table('articles')
    op.drop_table('sources')
    op.execute("DROP EXTENSION IF EXISTS vector")

import os
import json
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional, Sequence, Tuple
from pathlib import Path

from sqlalchemy import create_engine, text, select, func, bindparam
from sqlalchemy.types import Integer, DateTime, String
from sqlalchemy.sql import text as sql_text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker

# Add packages to path
sys.path.append(str(Path(__file__).parent.parent.parent))
from packages.config.embedding import config
from .models import Base, Article, ArticleVector, QueryLog

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/khobor")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db_config() -> dict:
    """Extract database configuration from DATABASE_URL for direct connections."""
    import re
    
    db_url = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/khobor")
    
    # Parse URL: postgresql+psycopg://user:password@host:port/database
    match = re.match(r"postgresql\+psycopg://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", db_url)
    
    if match:
        user, password, host, port, database = match.groups()
        return {
            "user": user,
            "password": password,
            "host": host,
            "port": int(port),
            "database": database
        }
    else:
        # Fallback to defaults
        return {
            "user": "postgres",
            "password": "postgres", 
            "host": "localhost",
            "port": 5432,
            "database": "khobor"
        }


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def validate_embedding_compatibility() -> None:
    """Validate that existing vectors are compatible with current model."""
    with session_scope() as session:
        # Validate column dimension against configured model
        try:
            col_dim = session.execute(text(
                """
                SELECT (a.atttypmod - 4) AS dim
                FROM pg_attribute a
                JOIN pg_class c ON a.attrelid = c.oid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relname = 'article_vectors'
                  AND n.nspname = 'public'
                  AND a.attname = 'embedding'
                """
            )).scalar()
            if col_dim is not None and int(col_dim) != int(config.dimension):
                raise SystemExit(
                    f"[EMBEDDING] ❌ Vector column dimension={col_dim} does not match configured dimension={config.dimension}. "
                    f"Run /admin/embedding/force-reindex and re-embed with {config.model_name}."
                )
        except Exception as e:
            # If metadata is unavailable, continue to row-level checks
            if not isinstance(e, SystemExit):
                print(f"[EMBEDDING] Warning: could not verify vector column dimension: {e}")

        # Check if any vectors exist
        vector_count = session.execute(
            text("SELECT COUNT(*) FROM article_vectors")
        ).scalar() or 0
        
        if vector_count == 0:
            print(f"[EMBEDDING] No existing vectors found - fresh start with {config.model_name}")
            return
        
        # Check model compatibility
        incompatible_vectors = session.execute(
            text("""
                SELECT COUNT(*) FROM article_vectors 
                WHERE model_name != :model_name 
                   OR model_dimension != :dimension
                   OR model_name IS NULL
                   OR model_dimension IS NULL
            """), 
            {"model_name": config.model_name, "dimension": config.dimension}
        ).scalar() or 0
        
        if incompatible_vectors > 0:
            # Hard block startup to prevent mixed-model operation
            raise SystemExit(
                f"[EMBEDDING] ❌ Found {incompatible_vectors} vectors incompatible with current model "
                f"{config.model_name} (dim={config.dimension}). Please run the /admin/embedding/force-reindex "
                f"or scripts/reembed_articles.py to reset and re-embed before starting the app."
            )
        
        print(f"[EMBEDDING] ✓ All {vector_count} vectors compatible with {config.model_name}")


def init_db():
    """Create pgvector extension, tables, and IVFFLAT index."""
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        Base.metadata.create_all(bind=conn)
        
        # Validate embedding compatibility after table creation
        validate_embedding_compatibility()
        
        # Create vector index if not exists (IVFFLAT lists=100)
        index_name = f"idx_article_vectors_embedding_ivfflat_{config.dimension}"
        conn.exec_driver_sql(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = '{index_name}'
                      AND n.nspname = 'public'
                ) THEN
                    CREATE INDEX {index_name}
                    ON article_vectors USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
                END IF;
            END
            $$;
            """
        )

        # Add audit comment with model info
        try:
            conn.exec_driver_sql(
                f"""
                COMMENT ON TABLE article_vectors IS 'embedding_model={config.model_name}; dimension={config.dimension}; updated=' || to_char(now() at time zone 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"Z"');
                """
            )
        except Exception as e:
            print(f"[EMBEDDING] Warning: could not set audit comment on article_vectors: {e}")

        # Enforce constraint to prevent mixed-model vectors
        try:
            conn.exec_driver_sql(
                """
                ALTER TABLE article_vectors
                DROP CONSTRAINT IF EXISTS ck_article_vectors_model_consistency;
                """
            )
            conn.exec_driver_sql(
                f"""
                ALTER TABLE article_vectors
                ADD CONSTRAINT ck_article_vectors_model_consistency
                CHECK (model_name = '{config.model_name}' AND model_dimension = {config.dimension});
                """
            )
        except Exception as e:
            print(f"[EMBEDDING] Warning: could not enforce model consistency constraint: {e}")


def _vector_literal(vec: Sequence[float]) -> str:
    # Format as pgvector literal string: [v1, v2, ...]
    return "[" + ", ".join(f"{float(v):.8f}" for v in vec) + "]"


def upsert_article(article: dict) -> uuid.UUID:
    """Upsert article by URL. Returns article UUID.

    Expected keys: url, title, source, source_category, summary, published_at (ISO str or datetime)
    """
    with session_scope() as session:
        data = dict(article)
        # Normalize published_at
        published_at = data.get("published_at")
        if isinstance(published_at, str) and published_at:
            try:
                data["published_at"] = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            except Exception:
                data["published_at"] = None
        elif not published_at:
            data["published_at"] = None

        insert_stmt = insert(Article).values(**{
            "url": data["url"],
            "title": data.get("title", "Untitled")[:512],
            "source": data.get("source", "Unknown")[:128],
            "source_category": data.get("source_category", "general")[:32],
            "summary": data.get("summary"),
            "published_at": data.get("published_at"),
        })
        
        insert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[Article.url],
            set_={
                "title": insert_stmt.excluded.title,
                "source": insert_stmt.excluded.source,
                "source_category": insert_stmt.excluded.source_category,
                "summary": insert_stmt.excluded.summary,
                "published_at": insert_stmt.excluded.published_at,
            },
        ).returning(Article.id)

        result = session.execute(insert_stmt)
        article_id = result.scalar_one()
        return article_id


def upsert_embedding(article_id: uuid.UUID, vec: Sequence[float]) -> None:
    """Upsert embedding with model validation."""
    # Enforce configured dimension
    expected_dim = config.dimension
    if vec is None or len(vec) != expected_dim:
        raise ValueError(f"Embedding must be {expected_dim}-dim for {config.model_name}; got {0 if vec is None else len(vec)}")
    
    embedding_literal = _vector_literal(vec)
    with session_scope() as session:
        insert_stmt = insert(ArticleVector).values(
            article_id=article_id,
            embedding=embedding_literal,
            model_name=config.model_name,
            model_dimension=config.dimension,
        )
        insert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[ArticleVector.article_id],
            set_={
                "embedding": insert_stmt.excluded.embedding,
                "model_name": insert_stmt.excluded.model_name,
                "model_dimension": insert_stmt.excluded.model_dimension,
                "updated_at": text("now() at time zone 'utc'")
            }
        )
        session.execute(insert_stmt)


def fetch_recent_candidates(window_hours: int = 72, limit: int = 800) -> List[Article]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=int(window_hours))
    with session_scope() as session:
        stmt = (
            select(Article)
            .where(
                (Article.published_at == None) |  # include undated
                (Article.published_at >= cutoff)
            )
            .order_by(Article.inserted_at.desc())
            .limit(limit)
        )
        result = session.execute(stmt).scalars().all()
        # Expunge objects from session to avoid lazy loading issues
        for article in result:
            session.expunge(article)
        return result


def search_vectors(qvec: Sequence[float], window_hours: int = 72, limit: int = 300) -> List[Tuple[Article, float]]:
    """Search by cosine similarity over recent articles.

    Returns list of (Article, cosine_similarity)
    """
    q_literal = _vector_literal(qvec)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=int(window_hours))

    with session_scope() as session:
        # Use raw SQL with bound parameters (including vector literal)
        query = text(
            """
            SELECT 
                a.id, a.url, a.title, a.source, a.source_category, a.summary, a.published_at,
                1 - (av.embedding <=> :qvec::vector) AS cos_sim
            FROM article_vectors av
            JOIN articles a ON a.id = av.article_id
            WHERE (a.published_at IS NULL OR a.published_at >= :cutoff)
            ORDER BY av.embedding <=> :qvec::vector
            LIMIT :limit
            """
        ).bindparams(
            bindparam("qvec", type_=String),
            bindparam("cutoff", type_=DateTime(timezone=True)),
            bindparam("limit", type_=Integer),
        )
        rows = session.execute(
            query,
            {"cutoff": cutoff, "limit": int(limit), "qvec": q_literal},
        )
        results: List[Tuple[Article, float]] = []
        for row in rows:
            art = Article(
                id=row[0],
                url=row[1],
                title=row[2],
                source=row[3],
                source_category=row[4],
                summary=row[5],
                published_at=row[6],
            )
            results.append((art, float(row[7])))
        return results


def log_query(question: str, answer: str, source_article_ids: List[str] = None, response_time_ms: int = None) -> uuid.UUID:
    """Log user query and response to database."""
    with session_scope() as session:
        source_articles_json = json.dumps(source_article_ids) if source_article_ids else None
        
        query_log = QueryLog(
            question=question,
            answer=answer,
            source_articles=source_articles_json,
            response_time_ms=response_time_ms
        )
        session.add(query_log)
        session.flush()
        return query_log.id


def get_recent_articles(limit: int = 50) -> List[Article]:
    """Get recent articles for API endpoints."""
    with session_scope() as session:
        stmt = (
            select(Article)
            .order_by(Article.inserted_at.desc())
            .limit(limit)
        )
        result = session.execute(stmt).scalars().all()
        # Expunge objects from session to avoid lazy loading issues
        for article in result:
            session.expunge(article)
        return result


def search_articles_by_keyword(keyword: str, limit: int = 50) -> List[Article]:
    """Search articles by keyword in title or summary."""
    with session_scope() as session:
        keyword_pattern = f"%{keyword.lower()}%"
        stmt = (
            select(Article)
            .where(
                (func.lower(Article.title).contains(keyword_pattern)) |
                (func.lower(Article.summary).contains(keyword_pattern))
            )
            .order_by(Article.inserted_at.desc())
            .limit(limit)
        )
        result = session.execute(stmt).scalars().all()
        # Expunge objects from session to avoid lazy loading issues
        for article in result:
            session.expunge(article)
        return result


def reset_embedding_index() -> dict:
    """Reset the entire embedding index with current model."""
    with session_scope() as session:
        # Count existing vectors and articles
        vector_count = session.execute(
            text("SELECT COUNT(*) FROM article_vectors")
        ).scalar() or 0
        
        article_count = session.execute(
            text("SELECT COUNT(*) FROM articles")
        ).scalar() or 0
        
        print(f"[INDEX RESET] Found {vector_count} vectors and {article_count} articles")
        
        # Delete all existing vectors 
        if vector_count > 0:
            session.execute(text("DELETE FROM article_vectors"))
            print(f"[INDEX RESET] Deleted {vector_count} existing vectors")
        
        # Drop old indexes
        session.execute(text("""
            DROP INDEX IF EXISTS idx_article_vectors_embedding_ivfflat;
            DROP INDEX IF EXISTS idx_article_vectors_embedding_ivfflat_1536;
            DROP INDEX IF EXISTS idx_article_vectors_embedding_ivfflat_3072;
        """))
        print("[INDEX RESET] Dropped old vector indexes")
        
        session.commit()
        
        # Recreate the index with current model dimensions
        index_name = f"idx_article_vectors_embedding_ivfflat_{config.dimension}"
        session.execute(text(f"""
            CREATE INDEX IF NOT EXISTS {index_name}
            ON article_vectors USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        """))

        # Enforce model consistency constraint
        session.execute(text("""
            ALTER TABLE article_vectors
            DROP CONSTRAINT IF EXISTS ck_article_vectors_model_consistency;
        """))
        session.execute(text(f"""
            ALTER TABLE article_vectors
            ADD CONSTRAINT ck_article_vectors_model_consistency
            CHECK (model_name = '{config.model_name}' AND model_dimension = {config.dimension});
        """))
        
        print(f"[INDEX RESET] Created new index {index_name} for {config.model_name}")
        session.commit()
        
        # Audit comment
        try:
            session.execute(text(f"""
                COMMENT ON TABLE article_vectors IS 'embedding_model={config.model_name}; dimension={config.dimension}; reset_at=' || to_char(now() at time zone 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"Z"');
            """))
        except Exception as e:
            print(f"[INDEX RESET] Warning: could not set audit comment: {e}")
        
        return {
            "status": "completed",
            "model_name": config.model_name,
            "dimension": config.dimension,
            "articles_ready_for_reembedding": article_count,
            "old_vectors_deleted": vector_count,
            "new_vectors_created": 0,
        }

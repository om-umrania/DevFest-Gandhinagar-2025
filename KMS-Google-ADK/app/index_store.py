# app/index_store.py
import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple, Dict, Any

from sqlalchemy import text, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

# --------- ENV ---------
PROJECT_ID = os.getenv("PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
REGION = os.getenv("REGION") or os.getenv("GOOGLE_CLOUD_LOCATION") or "us-central1"

DB_NAME = os.getenv("DB_NAME", "kms_index")
DB_USER = os.getenv("DB_USER", "kms_user")
DB_PASS = os.getenv("DB_PASS", "")
DB_INSTANCE = os.getenv("DB_INSTANCE")  # e.g., "my-proj:us-central1:obsidian-pg"

# --------- Optional Cloud SQL Connector import (tolerant) ---------
try:
    from google.cloud.sql.connector import Connector
    HAVE_CLOUD_SQL = True
except Exception:
    Connector = None  # type: ignore
    HAVE_CLOUD_SQL = False

_ENGINE: Optional[Engine] = None
_CONNECTOR: Optional["Connector"] = None

def _make_engine_cloudsql() -> Engine:
    """
    Engine via Cloud SQL Python Connector (Postgres/pg8000).
    Requires DB_INSTANCE, DB_USER, DB_PASS, DB_NAME.
    """
    missing = [k for k, v in {
        "DB_INSTANCE": DB_INSTANCE,
        "DB_USER": DB_USER,
        "DB_PASS": DB_PASS,
        "DB_NAME": DB_NAME,
    }.items() if not v]
    if missing:
        raise RuntimeError(f"Cloud SQL env missing: {', '.join(missing)}")

    if not HAVE_CLOUD_SQL:
        raise RuntimeError("cloud-sql-python-connector not importable")

    global _CONNECTOR
    if _CONNECTOR is None:
        _CONNECTOR = Connector()

    def getconn():
        # connector manages IAM auth; requires ADC (gcloud auth application-default login)
        return _CONNECTOR.connect(
            DB_INSTANCE,
            "pg8000",
            user=DB_USER,
            password=DB_PASS,
            db=DB_NAME,
        )

    eng = create_engine(
        "postgresql+pg8000://",
        creator=getconn,
        poolclass=NullPool,   # simple, fine for Cloud Run & local dev
        future=True,
    )
    print(f"[index_store] Using Cloud SQL via connector -> {DB_INSTANCE} / db={DB_NAME}")
    return eng

def _make_engine_sqlite() -> Engine:
    eng = create_engine("sqlite:///./kms_index.db", pool_pre_ping=True, future=True)
    print("[index_store] Falling back to SQLite at ./kms_index.db")
    return eng

def _pick_engine() -> Engine:
    # Prefer Cloud SQL only when all env vars are set
    if HAVE_CLOUD_SQL and DB_INSTANCE:
        try:
            return _make_engine_cloudsql()
        except Exception as e:
            print("[index_store] Cloud SQL path failed:", e)
    return _make_engine_sqlite()

def _get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = _pick_engine()
    return _ENGINE

@contextmanager
def connect():
    eng = _get_engine()
    with eng.connect() as conn:
        yield conn

# --------- MIGRATIONS ---------
DDL = """
CREATE TABLE IF NOT EXISTS chunks (
  id TEXT PRIMARY KEY,
  path TEXT NOT NULL,
  heading TEXT,
  start_line INT,
  text TEXT NOT NULL,
  created_at TIMESTAMPTZ,
  modified_at TIMESTAMPTZ NOT NULL,
  hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chunk_tags (
  chunk_id TEXT REFERENCES chunks(id) ON DELETE CASCADE,
  tag TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS files (
  path TEXT PRIMARY KEY,
  etag TEXT,
  size BIGINT,
  updated TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_chunks_path ON chunks(path);
CREATE INDEX IF NOT EXISTS idx_chunks_created ON chunks(created_at);
CREATE INDEX IF NOT EXISTS idx_chunks_modified ON chunks(modified_at);
CREATE INDEX IF NOT EXISTS idx_chunk_tags_tag ON chunk_tags(tag);
CREATE INDEX IF NOT EXISTS idx_chunk_tags_chunk ON chunk_tags(chunk_id);
"""

def migrate():
    with connect() as c:
        for stmt in DDL.strip().split(";"):
            s = stmt.strip()
            if s:
                c.execute(text(s))
        c.commit()

# --------- UPSERT HELPERS ---------
def upsert_file(path: str, etag: Optional[str], size: Optional[int], updated_ts):
    sql = text("""
        INSERT INTO files(path, etag, size, updated)
        VALUES (:path, :etag, :size, :updated)
        ON CONFLICT (path) DO UPDATE
        SET etag=EXCLUDED.etag, size=EXCLUDED.size, updated=EXCLUDED.updated
    """)
    with connect() as c:
        c.execute(sql, {"path": path, "etag": etag, "size": size, "updated": updated_ts})
        c.commit()

def upsert_chunk(
    chunk_id: str,
    path: str,
    heading: Optional[str],
    start_line: int,
    text_val: str,
    created_at,
    modified_at,
    hash_val: str,
):
    sql = text("""
        INSERT INTO chunks(id, path, heading, start_line, text, created_at, modified_at, hash)
        VALUES (:id, :path, :heading, :start_line, :text, :created_at, :modified, :hash)
        ON CONFLICT (id) DO UPDATE SET
            path=EXCLUDED.path,
            heading=EXCLUDED.heading,
            start_line=EXCLUDED.start_line,
            text=EXCLUDED.text,
            created_at=EXCLUDED.created_at,
            modified_at=EXCLUDED.modified_at,
            hash=EXCLUDED.hash
    """)
    with connect() as c:
        c.execute(sql, {
            "id": chunk_id, "path": path, "heading": heading,
            "start_line": start_line, "text": text_val,
            "created_at": created_at, "modified": modified_at,
            "hash": hash_val
        })
        c.commit()

def replace_chunk_tags(chunk_id: str, tags: Iterable[str]):
    tags = [t for t in (tags or []) if t]
    with connect() as c:
        c.execute(text("DELETE FROM chunk_tags WHERE chunk_id = :cid"), {"cid": chunk_id})
        if tags:
            # portable multi-row INSERT across SQLite/Postgres
            placeholders = ", ".join([f"(:cid, :t{i})" for i, _ in enumerate(tags)])
            params = {"cid": chunk_id}
            params.update({f"t{i}": t for i, t in enumerate(tags)})
            c.execute(text("INSERT INTO chunk_tags(chunk_id, tag) VALUES " + placeholders), params)
        c.commit()

# --------- QUERY (portable across SQLite/Postgres) ---------
@dataclass
class FilterSpec:
    tags: List[str]
    require_all: bool
    since: Optional[str]   # ISO dt string
    until: Optional[str]
    path_prefix: Optional[str]

def _time_expr(date_field: str) -> str:
    if date_field == "created":
        return "created_at"
    if date_field == "modified":
        return "modified_at"
    return "COALESCE(created_at, modified_at)"

def build_candidate_sql(filters: FilterSpec, date_field: str = "auto") -> Tuple[str, Dict[str, Any]]:
    df = _time_expr(date_field)
    params: Dict[str, Any] = {"since": filters.since, "until": filters.until}
    where = [f"({df} BETWEEN :since AND :until)"]

    if filters.path_prefix:
        where.append("path LIKE :pfx")
        params["pfx"] = f"{filters.path_prefix}%"

    base = f"""
    WITH filtered AS (
      SELECT c.id, c.path, c.heading, c.text, c.start_line, c.created_at, c.modified_at
      FROM chunks c
      WHERE {" AND ".join(where)}
    )
    """

    if filters.tags:
        # Build portable IN (...) with bound placeholders (works on SQLite & Postgres)
        tag_placeholders = []
        for i, t in enumerate(filters.tags):
            key = f"tg{i}"
            params[key] = t
            tag_placeholders.append(f":{key}")
        tag_in = ", ".join(tag_placeholders)

        if filters.require_all:
            # AND semantics: chunk must have ALL requested tags
            sql = base + f"""
            , tagged AS (
              SELECT ct.chunk_id
              FROM chunk_tags ct
              WHERE ct.tag IN ({tag_in})
              GROUP BY ct.chunk_id
              HAVING COUNT(DISTINCT ct.tag) = {len(filters.tags)}
            )
            SELECT f.*
            FROM filtered f
            JOIN tagged t ON f.id = t.chunk_id
            """
        else:
            # OR semantics: chunk has ANY of the tags
            sql = base + f"""
            , tagged AS (
              SELECT DISTINCT ct.chunk_id
              FROM chunk_tags ct
              WHERE ct.tag IN ({tag_in})
            )
            SELECT f.*
            FROM filtered f
            JOIN tagged t ON f.id = t.chunk_id
            """
    else:
        sql = base + "SELECT * FROM filtered"

    return sql, params

def fetch_candidates(filters: FilterSpec, date_field: str = "auto", cap: int = 2000) -> List[Dict[str, Any]]:
    sql, params = build_candidate_sql(filters, date_field=date_field)
    sql += " LIMIT :cap"
    params["cap"] = cap
    with connect() as c:
        rows = c.execute(text(sql), params).mappings().all()
        return [dict(r) for r in rows]

def fetch_facets(since: str, until: str, path_prefix: Optional[str]) -> Dict[str, Any]:
    base_where = ["(COALESCE(created_at, modified_at) BETWEEN :since AND :until)"]
    params = {"since": since, "until": until}
    if path_prefix:
        base_where.append("path LIKE :pfx")
        params["pfx"] = f"{path_prefix}%"
    where = " AND ".join(base_where)

    sql_tags = text(f"""
        SELECT tag, COUNT(*) AS count
        FROM chunk_tags
        JOIN chunks ON chunks.id = chunk_tags.chunk_id
        WHERE {where}
        GROUP BY tag
        ORDER BY count DESC
        LIMIT 50
    """)
    sql_time = text(f"""
        SELECT strftime('%Y-%m', COALESCE(created_at, modified_at)) AS bucket, COUNT(*) AS count
        FROM chunks
        WHERE {where}
        GROUP BY bucket
        ORDER BY bucket DESC
        LIMIT 24
    """)
    # NOTE: The strftime(...) above is SQLite-specific; Postgres needs to_char(date_trunc('month', ...),'YYYY-MM').
    # We'll patch dynamically below based on dialect.
    with connect() as c:
        # Patch time histogram query depending on backend
        if c.engine.url.get_backend_name() != "sqlite":
            sql_time = text(f"""
                SELECT to_char(date_trunc('month', COALESCE(created_at, modified_at)), 'YYYY-MM') AS bucket,
                       COUNT(*) AS count
                FROM chunks
                WHERE {where}
                GROUP BY bucket
                ORDER BY bucket DESC
                LIMIT 24
            """)

        top_tags = [dict(r) for r in c.execute(sql_tags, params).mappings().all()]
        time_hist = [dict(r) for r in c.execute(sql_time, params).mappings().all()]

    # normalize counts to int for both backends
    for x in top_tags:
        x["count"] = int(x["count"])
    for x in time_hist:
        x["count"] = int(x["count"])
    return {"top_tags": top_tags, "time_histogram": time_hist}

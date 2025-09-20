# scripts/ingest.py
import os
import hashlib
from typing import List, Dict, Any, Iterable, Optional
from datetime import timezone

from app.fetch_agent import list_md_objects, fetch_md
from app.index_store import (
    migrate, upsert_file, upsert_chunk, replace_chunk_tags, connect
)
from sqlalchemy import text

# ---- simple chunker ----
def split_into_chunks(path: str, text: str) -> List[Dict[str, Any]]:
    """
    Headings-first split; if a section > ~1200 chars, split by blank lines.
    Produces items: {"heading": str|None, "start_line": int, "text": str}
    """
    lines = text.splitlines()
    chunks = []
    start = 0
    current_heading = None

    def emit(s: int, e: int, heading: Optional[str]):
        body = "\n".join(lines[s:e]).strip()
        if not body:
            return
        # further split large bodies by paragraphs
        if len(body) > 1200:
            paras = [p for p in body.split("\n\n") if p.strip()]
            offset = 0
            for p in paras:
                p_lines = p.count("\n") + 1
                chunks.append({"heading": heading, "start_line": s + offset + 1, "text": p})
                offset += p_lines
        else:
            chunks.append({"heading": heading, "start_line": s + 1, "text": body})

    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("#"):  # markdown heading
            if i > start:
                emit(start, i, current_heading)
            current_heading = ln.lstrip("# ").strip() or None
            start = i + 1
    emit(start, len(lines), current_heading)
    return chunks

def normalize_tags(meta: Dict[str, Any]) -> List[str]:
    tags = meta.get("tags") or meta.get("tag") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.replace(";", ",").split(",")]
    out = []
    for t in tags:
        t = str(t).strip().lower()
        if not t:
            continue
        t = t.lstrip("#")
        out.append(t)
    return sorted(set(out))

def chunk_id_for(path: str, start_line: int, text: str) -> str:
    h = hashlib.sha1(f"{path}:{start_line}:{text[:64]}".encode("utf-8")).hexdigest()
    return h

def file_row(path: str) -> Optional[Dict[str, Any]]:
    with connect() as c:
        row = c.execute(
            text("SELECT etag, updated FROM files WHERE path = :p"),
            {"p": path}
        ).mappings().first()
        return dict(row) if row else None

def run_ingest(bucket: str, prefix: str = "notes/") -> None:
    migrate()  # ensure tables exist
    print(f"[ingest] listing md files from gs://{bucket}/{prefix} ...")
    total, changed = 0, 0
    for blob in list_md_objects(bucket, prefix=prefix):
        total += 1
        item = fetch_md(blob)
        # incremental gate
        existing = file_row(item["path"])
        if existing and existing.get("etag") == item["etag"]:
            continue  # unchanged

        changed += 1
        upsert_file(item["path"], item["etag"], item["size"], item["modified_at"])

        chunks = split_into_chunks(item["path"], item["body"])
        tags = normalize_tags(item["frontmatter"])

        for ch in chunks:
            cid = chunk_id_for(item["path"], ch["start_line"], ch["text"])
            upsert_chunk(
                chunk_id=cid,
                path=item["path"],
                heading=ch["heading"],
                start_line=ch["start_line"],
                text_val=ch["text"],
                created_at=item["created_at"],
                modified_at=item["modified_at"],
                hash_val=item["hash"],
            )
            replace_chunk_tags(cid, tags)

        print(f"[ingest] indexed: {item['path']} ({len(chunks)} chunks)")
    print(f"[ingest] done. scanned={total} changed={changed}")

if __name__ == "__main__":
    bucket = os.environ.get("GCS_BUCKET")
    if not bucket:
        raise SystemExit("GCS_BUCKET not set in env")
    run_ingest(bucket)
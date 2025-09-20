# app/fetch_agent.py
from typing import Iterator, Dict, Any, Optional
from datetime import timezone
import hashlib

from google.cloud import storage
import frontmatter
from dateutil.parser import isoparse  # add python-dateutil to requirements

def list_md_objects(bucket_name: str, prefix: str = "notes/") -> Iterator[storage.Blob]:
    client = storage.Client()
    for blob in client.list_blobs(bucket_name, prefix=prefix):
        if blob.name.endswith(".md"):
            yield blob

def parse_frontmatter_dates(meta: Dict[str, Any]) -> Optional[Any]:
    """Try to parse 'date' from frontmatter; return aware datetime or None."""
    if not meta:
        return None
    cand = meta.get("date") or meta.get("created") or meta.get("created_at")
    if not cand:
        return None
    try:
        # supports strings like 2024-01-31 or ISO
        return isoparse(str(cand)).astimezone(timezone.utc)
    except Exception:
        return None

def fetch_md(blob: storage.Blob) -> Dict[str, Any]:
    raw = blob.download_as_text()
    fm = frontmatter.loads(raw)
    created = parse_frontmatter_dates(fm.metadata)
    modified = blob.updated.replace(tzinfo=timezone.utc)  # authoritative
    return {
        "path": f"gs://{blob.bucket.name}/{blob.name}",
        "frontmatter": fm.metadata or {},
        "body": fm.content,
        "created_at": created,
        "modified_at": modified,
        "hash": hashlib.sha1(raw.encode("utf-8")).hexdigest(),
        "etag": blob.etag,
        "size": blob.size,
    }
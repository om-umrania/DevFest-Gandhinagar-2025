# ui/server.py
import os
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Query
from pydantic import BaseModel

from app.index_store import (
    migrate, fetch_candidates, fetch_facets, FilterSpec
)
# Lightweight BM25 util; for demo scoring only (replace w/ your real reranker later)
import math
import re

app = FastAPI(title="Obsidian Lite KMS API")

# ---------- Utilities ----------
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())

def bm25_score(query: str, docs: List[str], k1=1.2, b=0.75) -> List[float]:
    # minimal BM25 on the candidate set
    q_terms = tokenize(query)
    N = len(docs) or 1
    doc_tokens = [tokenize(d) for d in docs]
    avgdl = sum(len(t) for t in doc_tokens) / N
    # df for each q term
    dfs = {t: sum(1 for toks in doc_tokens if t in toks) for t in set(q_terms)}
    scores = []
    for toks in doc_tokens:
        dl = len(toks) or 1
        tf = {t: toks.count(t) for t in set(q_terms)}
        s = 0.0
        for t in q_terms:
            df = dfs.get(t, 0) or 1
            idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
            denom = tf.get(t, 0) + k1 * (1 - b + b * (dl / avgdl))
            s += idf * ((tf.get(t, 0) * (k1 + 1)) / (denom if denom != 0 else 1))
        scores.append(s)
    return scores

def iso_or_default(s: Optional[str], default: datetime) -> str:
    if not s:
        return default.isoformat()
    # Accept YYYY, YYYY-MM, YYYY-MM-DD or relative '7d','30d','12m'
    try:
        if s.endswith("d"):
            days = int(s[:-1])
            return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        if s.endswith("m"):
            months = int(s[:-1])
            return (datetime.now(timezone.utc) - timedelta(days=30*months)).isoformat()
        # pad partials
        parts = s.split("-")
        if len(parts) == 1:
            s = f"{s}-01-01"
        elif len(parts) == 2:
            s = f"{s}-01"
        return datetime.fromisoformat(s).astimezone(timezone.utc).isoformat()
    except Exception:
        return default.isoformat()

# ---------- Schemas ----------
class SearchResult(BaseModel):
    path: str
    heading: Optional[str]
    score: float
    snippet: str
    start_line: int
    signals: Dict[str, float]

class SearchResponse(BaseModel):
    query: str
    applied_filters: Dict[str, Any]
    total_candidates: int
    results: List[SearchResult]
    fell_back: bool = False
    generated_at: str

class AnswerResponse(BaseModel):
    answer: List[str]
    citations: List[Dict[str, str]]
    related: List[str]

class FacetResponse(BaseModel):
    time_histogram: List[Dict[str, Any]]
    top_tags: List[Dict[str, Any]]

# ---------- Startup ----------
@app.on_event("startup")
def _startup():
    migrate()

# ---------- Routes ----------
@app.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1),
    k: int = 10,
    tags: Optional[str] = None,                    # CSV
    require_all_tags: bool = True,
    since: Optional[str] = None,
    until: Optional[str] = None,
    date_field: str = Query("auto", regex="^(auto|created|modified)$"),
    path_prefix: Optional[str] = None,
    explain: bool = False,
    sort: str = Query("score", regex="^(score|date_desc|date_asc)$")
):
    # resolve time window
    start_default = datetime(1970, 1, 1, tzinfo=timezone.utc)
    end_default = datetime.now(timezone.utc)
    since_iso = iso_or_default(since, start_default)
    until_iso = iso_or_default(until, end_default)

    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    filt = FilterSpec(
        tags=tag_list,
        require_all=require_all_tags,
        since=since_iso,
        until=until_iso,
        path_prefix=path_prefix
    )
    cands = fetch_candidates(filt, date_field=date_field, cap=2000)

    texts = [c["text"] for c in cands]
    bm25 = bm25_score(q, texts) if texts else []

    items = []
    for i, c in enumerate(cands):
        score = bm25[i] if bm25 else 0.0
        items.append({
            "path": c["path"],
            "heading": c.get("heading"),
            "score": float(score),
            "snippet": (c["text"][:260] + "…") if c["text"] else "",
            "start_line": c.get("start_line") or 0,
            "signals": {"bm25": float(score)}
        })

    # sort
    if sort == "date_desc":
        items.sort(key=lambda x: x["signals"].get("recency", 0.0) or 0.0, reverse=True)
    elif sort == "date_asc":
        items.sort(key=lambda x: x["signals"].get("recency", 0.0) or 0.0)
    else:
        items.sort(key=lambda x: x["score"], reverse=True)

    return {
        "query": q,
        "applied_filters": {
            "tags": tag_list, "require_all_tags": require_all_tags,
            "since": since_iso[:10], "until": until_iso[:10],
            "date_field": date_field, "path_prefix": path_prefix, "sort": sort
        },
        "total_candidates": len(cands),
        "results": items[:k],
        "fell_back": False,
        "generated_at": utc_now_iso()
    }

@app.get("/answer", response_model=AnswerResponse)
def answer(
    q: str,
    k: int = 6,
    tags: Optional[str] = None,
    require_all_tags: bool = True,
    since: Optional[str] = None,
    until: Optional[str] = None,
    date_field: str = "auto",
    path_prefix: Optional[str] = None,
):
    # Reuse search to get top-k chunks (simple baseline; replace w/ your RAG later)
    sr = search(q=q, k=k, tags=tags, require_all_tags=require_all_tags,
                since=since, until=until, date_field=date_field,
                path_prefix=path_prefix, explain=False, sort="score")
    results = sr["results"]
    # naive synthesis: just return bullet points + citations
    passages = [f"- {r['snippet']}" for r in results]
    cits = [{"ref": f"{r['path']}#{r.get('heading') or ''}"} for r in results]
    related = [r["path"] for r in results[:3]]
    return {"answer": passages, "citations": cits, "related": related}

@app.get("/facets", response_model=FacetResponse)
def facets(
    since: Optional[str] = None,
    until: Optional[str] = None,
    path_prefix: Optional[str] = None,
):
    start_default = datetime(1970, 1, 1, tzinfo=timezone.utc)
    end_default = datetime.now(timezone.utc)
    since_iso = iso_or_default(since, start_default)
    until_iso = iso_or_default(until, end_default)
    data = fetch_facets(since_iso, until_iso, path_prefix)
    return {"time_histogram": data["time_histogram"], "top_tags": data["top_tags"]}
# ui/server.py
import os
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
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
@app.get("/", response_class=HTMLResponse)
def landing_page():
    """Landing page with search interface."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>KMS Google ADK - Knowledge Management System</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            
            .header {
                background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
                color: white;
                padding: 40px;
                text-align: center;
            }
            
            .header h1 {
                font-size: 2.5rem;
                margin-bottom: 10px;
                font-weight: 700;
            }
            
            .header p {
                font-size: 1.2rem;
                opacity: 0.9;
            }
            
            .search-section {
                padding: 40px;
            }
            
            .search-form {
                display: flex;
                gap: 15px;
                margin-bottom: 30px;
            }
            
            .search-input {
                flex: 1;
                padding: 15px 20px;
                border: 2px solid #e5e7eb;
                border-radius: 12px;
                font-size: 1.1rem;
                transition: all 0.3s ease;
            }
            
            .search-input:focus {
                outline: none;
                border-color: #4f46e5;
                box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
            }
            
            .search-btn {
                padding: 15px 30px;
                background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 1.1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            
            .search-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(79, 70, 229, 0.3);
            }
            
            .filters {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 30px;
            }
            
            .filter-group {
                display: flex;
                flex-direction: column;
            }
            
            .filter-group label {
                font-weight: 600;
                margin-bottom: 5px;
                color: #374151;
            }
            
            .filter-group input, .filter-group select {
                padding: 10px;
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                font-size: 0.9rem;
            }
            
            .results-section {
                margin-top: 30px;
            }
            
            .result-item {
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 15px;
                transition: all 0.3s ease;
            }
            
            .result-item:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            }
            
            .result-title {
                font-size: 1.3rem;
                font-weight: 600;
                color: #1f2937;
                margin-bottom: 8px;
            }
            
            .result-path {
                color: #6b7280;
                font-size: 0.9rem;
                margin-bottom: 10px;
            }
            
            .result-snippet {
                color: #4b5563;
                line-height: 1.6;
                margin-bottom: 10px;
            }
            
            .result-score {
                display: inline-block;
                background: #dbeafe;
                color: #1e40af;
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 0.8rem;
                font-weight: 600;
            }
            
            .loading {
                text-align: center;
                padding: 40px;
                color: #6b7280;
            }
            
            .error {
                background: #fef2f2;
                border: 1px solid #fecaca;
                color: #dc2626;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            }
            
            .stats {
                background: #f0f9ff;
                border: 1px solid #bae6fd;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 20px;
            }
            
            .stats h3 {
                color: #0369a1;
                margin-bottom: 10px;
            }
            
            .quick-search {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin-bottom: 20px;
            }
            
            .quick-search-btn {
                background: #f3f4f6;
                border: 1px solid #d1d5db;
                color: #374151;
                padding: 8px 16px;
                border-radius: 20px;
                cursor: pointer;
                transition: all 0.3s ease;
                font-size: 0.9rem;
            }
            
            .quick-search-btn:hover {
                background: #4f46e5;
                color: white;
                border-color: #4f46e5;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔍 KMS Google ADK</h1>
                <p>Knowledge Management System - Search across 30+ technical documents</p>
            </div>
            
            <div class="search-section">
                <form class="search-form" onsubmit="searchDocuments(event)">
                    <input type="text" id="searchQuery" class="search-input" placeholder="Search for machine learning, Docker, web development, security..." required>
                    <button type="submit" class="search-btn">Search</button>
                </form>
                
                <div class="quick-search">
                    <span style="font-weight: 600; margin-right: 10px;">Quick searches:</span>
                    <button class="quick-search-btn" onclick="quickSearch('machine learning')">Machine Learning</button>
                    <button class="quick-search-btn" onclick="quickSearch('docker containers')">Docker</button>
                    <button class="quick-search-btn" onclick="quickSearch('web development')">Web Dev</button>
                    <button class="quick-search-btn" onclick="quickSearch('security best practices')">Security</button>
                    <button class="quick-search-btn" onclick="quickSearch('kubernetes orchestration')">Kubernetes</button>
                    <button class="quick-search-btn" onclick="quickSearch('python programming')">Python</button>
                </div>
                
                <div class="filters">
                    <div class="filter-group">
                        <label for="tags">Tags (comma-separated)</label>
                        <input type="text" id="tags" placeholder="e.g., ai, docker, security">
                    </div>
                    <div class="filter-group">
                        <label for="sortBy">Sort by</label>
                        <select id="sortBy">
                            <option value="score">Relevance</option>
                            <option value="date_desc">Date (Newest)</option>
                            <option value="date_asc">Date (Oldest)</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label for="maxResults">Max Results</label>
                        <select id="maxResults">
                            <option value="10">10</option>
                            <option value="20">20</option>
                            <option value="50">50</option>
                        </select>
                    </div>
                </div>
                
                <div id="results"></div>
            </div>
        </div>
        
        <script>
            function quickSearch(query) {
                document.getElementById('searchQuery').value = query;
                searchDocuments(event);
            }
            
            async function searchDocuments(event) {
                event.preventDefault();
                
                const query = document.getElementById('searchQuery').value;
                const tags = document.getElementById('tags').value;
                const sortBy = document.getElementById('sortBy').value;
                const maxResults = document.getElementById('maxResults').value;
                
                const resultsDiv = document.getElementById('results');
                resultsDiv.innerHTML = '<div class="loading">🔍 Searching...</div>';
                
                try {
                    let url = `/search?q=${encodeURIComponent(query)}&k=${maxResults}&sort=${sortBy}`;
                    if (tags) {
                        url += `&tags=${encodeURIComponent(tags)}`;
                    }
                    
                    const response = await fetch(url);
                    const data = await response.json();
                    
                    displayResults(data);
                } catch (error) {
                    resultsDiv.innerHTML = `<div class="error">❌ Error: ${error.message}</div>`;
                }
            }
            
            function displayResults(data) {
                const resultsDiv = document.getElementById('results');
                
                if (!data.results || data.results.length === 0) {
                    resultsDiv.innerHTML = '<div class="error">No results found. Try a different search term.</div>';
                    return;
                }
                
                let html = `
                    <div class="stats">
                        <h3>📊 Search Results</h3>
                        <p>Found <strong>${data.total_candidates}</strong> documents matching "${data.query}"</p>
                        <p>Showing ${data.results.length} results</p>
                    </div>
                `;
                
                data.results.forEach((result, index) => {
                    const title = result.heading || 'Untitled';
                    const path = result.path.replace('gs://kms-test-bucket-devfest/', '');
                    const snippet = result.snippet || 'No preview available';
                    const score = (result.score || 0).toFixed(3);
                    
                    html += `
                        <div class="result-item">
                            <div class="result-title">${title}</div>
                            <div class="result-path">📄 ${path}</div>
                            <div class="result-snippet">${snippet}</div>
                            <div class="result-score">Score: ${score}</div>
                        </div>
                    `;
                });
                
                resultsDiv.innerHTML = html;
            }
            
            // Load some initial results on page load
            window.addEventListener('load', function() {
                searchDocuments({preventDefault: () => {}});
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

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
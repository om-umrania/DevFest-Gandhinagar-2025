"""
Simple Prediction Layer Tool for KMS-Google-ADK MVP
Basic query classification and retrieval planning.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class RetrievalPlan:
    """Simple retrieval plan."""
    query_type: str
    strategy: str
    top_k: int
    filters: Dict[str, Any]


class SimplePredictionTool:
    """Simple tool for query analysis and retrieval planning."""
    
    def __init__(self):
        """Initialize the prediction layer tool."""
        pass
    
    def plan_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> RetrievalPlan:
        """
        Analyze a query and create a simple retrieval plan.
        
        Args:
            query: User query string
            context: Optional context information
            
        Returns:
            RetrievalPlan object
        """
        query_lower = query.lower()
        
        # Simple query classification
        if any(word in query_lower for word in ["compare", "vs", "versus", "difference"]):
            query_type = "compare"
            strategy = "hybrid"
            top_k = 10
        elif any(word in query_lower for word in ["related", "similar", "connected"]):
            query_type = "explore"
            strategy = "graph_traversal"
            top_k = 15
        elif any(word in query_lower for word in ["what is", "define", "meaning"]):
            query_type = "lookup"
            strategy = "semantic_search"
            top_k = 5
        else:
            query_type = "general"
            strategy = "semantic_search"
            top_k = 8
        
        # Extract simple filters
        filters = {}
        if "tag:" in query_lower:
            # Extract tags after "tag:"
            parts = query_lower.split("tag:")
            if len(parts) > 1:
                tags = [tag.strip() for tag in parts[1].split()[:3]]  # Max 3 tags
                filters["tags"] = tags
        
        return RetrievalPlan(
            query_type=query_type,
            strategy=strategy,
            top_k=top_k,
            filters=filters
        )
    
    def rerank_candidates(
        self, 
        candidates: List[Any], 
        query: str
    ) -> List[Any]:
        """
        Simple reranking of candidates.
        
        Args:
            candidates: List of candidate results
            query: Original query
            
        Returns:
            List of reranked candidates
        """
        query_words = set(query.lower().split())
        
        for candidate in candidates:
            # Handle both dict and SearchResult objects
            if hasattr(candidate, 'title'):
                # SearchResult object
                title = getattr(candidate, 'title', '').lower()
                content = getattr(candidate, 'content', '').lower()
                original_score = getattr(candidate, 'score', 0)
            else:
                # Dictionary object
                title = candidate.get("title", "").lower()
                content = candidate.get("content", "").lower()
                original_score = candidate.get("score", 0)
            
            # Count word matches
            title_matches = sum(1 for word in query_words if word in title)
            content_matches = sum(1 for word in query_words if word in content)
            
            # Simple rerank score
            rerank_score = (
                original_score * 0.7 +  # Original score
                title_matches * 0.2 +  # Title matches
                content_matches * 0.1   # Content matches
            )
            
            # Add rerank score to candidate
            if hasattr(candidate, 'rerank_score'):
                candidate.rerank_score = rerank_score
            else:
                candidate["rerank_score"] = rerank_score
        
        # Sort by rerank score
        return sorted(candidates, key=lambda x: getattr(x, 'rerank_score', 0) if hasattr(x, 'rerank_score') else x.get("rerank_score", 0), reverse=True)

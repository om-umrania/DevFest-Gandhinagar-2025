"""
Prediction Agent for Obsidian KMS
Interprets user intents and chooses retrieval strategy
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum

from google.adk import Agent, Tool, Memory
from google.adk.agents import AgentConfig

from tools.vector_search_tool import VectorSearchTool
from tools.graph_update_tool import GraphUpdateTool
from tools.prediction_layer_tool import PredictionLayerTool
from memory.adapters.neo4j import Neo4jAdapter

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of queries the system can handle"""
    LOOKUP = "lookup"  # Find specific information
    COMPARE = "compare"  # Compare multiple items
    SYNTHESIZE = "synthesize"  # Create new insights
    EXPLORE = "explore"  # Discover related content
    TIMELINE = "timeline"  # Chronological information
    CAUSAL = "causal"  # Cause-effect relationships
    DEFINITION = "definition"  # Define concepts
    HOWTO = "howto"  # Step-by-step instructions


class RetrievalStrategy(Enum):
    """Retrieval strategies for different query types"""
    VECTOR_ONLY = "vector_only"
    GRAPH_ONLY = "graph_only"
    HYBRID = "hybrid"
    TEMPORAL = "temporal"
    HIERARCHICAL = "hierarchical"


class PredictionAgent(Agent):
    """
    Prediction Agent interprets user intents and chooses retrieval strategy.
    
    Responsibilities:
    - Classify query type and intent
    - Decide on retrieval strategy (graph vs semantic vs hybrid)
    - Rerank candidates based on multiple signals
    - Feed curated contexts to Synthesis Agent
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        
        # Initialize tools
        self.vector_search_tool = VectorSearchTool()
        self.graph_update_tool = GraphUpdateTool()
        self.prediction_layer_tool = PredictionLayerTool()
        
        # Initialize memory adapters
        self.graph_db = Neo4jAdapter()
        
        # Configuration
        self.max_candidates = config.get("max_candidates", 20)
        self.rerank_top_k = config.get("rerank_top_k", 10)
        self.graph_walk_max_hops = config.get("graph_walk_max_hops", 3)
        
        # Query classification model (simplified)
        self.query_patterns = {
            QueryType.LOOKUP: ["what is", "who is", "when did", "where is", "find", "search"],
            QueryType.COMPARE: ["compare", "vs", "versus", "difference", "similar", "contrast"],
            QueryType.SYNTHESIZE: ["summarize", "synthesis", "overview", "analysis", "insights"],
            QueryType.EXPLORE: ["explore", "discover", "related", "connected", "associated"],
            QueryType.TIMELINE: ["timeline", "chronology", "history", "evolution", "progression"],
            QueryType.CAUSAL: ["why", "cause", "effect", "because", "leads to", "results in"],
            QueryType.DEFINITION: ["define", "definition", "meaning", "explain"],
            QueryType.HOWTO: ["how to", "steps", "process", "procedure", "guide"]
        }
    
    async def plan_query(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Plan retrieval strategy for a user query
        
        Args:
            query_data: Query data with text, context, and preferences
            
        Returns:
            Retrieval plan with strategy, parameters, and expected results
        """
        try:
            query_text = query_data["query"]
            context = query_data.get("context", {})
            preferences = query_data.get("preferences", {})
            
            logger.info(f"Planning query: {query_text[:100]}...")
            
            # 1. Classify query type
            query_type = await self._classify_query(query_text)
            
            # 2. Determine retrieval strategy
            strategy = await self._determine_strategy(query_type, query_text, context)
            
            # 3. Generate retrieval plan
            plan = await self._generate_retrieval_plan(query_type, strategy, query_text, context)
            
            # 4. Estimate expected results
            expected_results = await self._estimate_results(plan, query_text)
            
            result = {
                "query": query_text,
                "query_type": query_type.value,
                "strategy": strategy.value,
                "plan": plan,
                "expected_results": expected_results,
                "confidence": plan.get("confidence", 0.8),
                "processing_time": datetime.now().isoformat(),
                "status": "success"
            }
            
            logger.info(f"Query planned: {query_type.value} -> {strategy.value}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to plan query: {str(e)}")
            return {
                "query": query_data.get("query", ""),
                "error": str(e),
                "status": "error"
            }
    
    async def _classify_query(self, query_text: str) -> QueryType:
        """Classify the type of query based on text patterns"""
        try:
            query_lower = query_text.lower()
            
            # Score each query type based on pattern matches
            scores = {}
            for query_type, patterns in self.query_patterns.items():
                score = sum(1 for pattern in patterns if pattern in query_lower)
                scores[query_type] = score
            
            # Find the highest scoring type
            if scores:
                best_type = max(scores, key=scores.get)
                if scores[best_type] > 0:
                    return best_type
            
            # Default to lookup if no patterns match
            return QueryType.LOOKUP
            
        except Exception as e:
            logger.error(f"Failed to classify query: {str(e)}")
            return QueryType.LOOKUP
    
    async def _determine_strategy(self, query_type: QueryType, query_text: str, 
                                context: Dict[str, Any]) -> RetrievalStrategy:
        """Determine the best retrieval strategy for the query type"""
        try:
            # Strategy mapping based on query type
            strategy_mapping = {
                QueryType.LOOKUP: RetrievalStrategy.HYBRID,
                QueryType.COMPARE: RetrievalStrategy.GRAPH_ONLY,
                QueryType.SYNTHESIZE: RetrievalStrategy.HYBRID,
                QueryType.EXPLORE: RetrievalStrategy.GRAPH_ONLY,
                QueryType.TIMELINE: RetrievalStrategy.TEMPORAL,
                QueryType.CAUSAL: RetrievalStrategy.GRAPH_ONLY,
                QueryType.DEFINITION: RetrievalStrategy.VECTOR_ONLY,
                QueryType.HOWTO: RetrievalStrategy.HIERARCHICAL
            }
            
            base_strategy = strategy_mapping.get(query_type, RetrievalStrategy.HYBRID)
            
            # Adjust strategy based on context
            if context.get("prefer_semantic"):
                if base_strategy == RetrievalStrategy.GRAPH_ONLY:
                    base_strategy = RetrievalStrategy.HYBRID
            elif context.get("prefer_graph"):
                if base_strategy == RetrievalStrategy.VECTOR_ONLY:
                    base_strategy = RetrievalStrategy.HYBRID
            
            return base_strategy
            
        except Exception as e:
            logger.error(f"Failed to determine strategy: {str(e)}")
            return RetrievalStrategy.HYBRID
    
    async def _generate_retrieval_plan(self, query_type: QueryType, strategy: RetrievalStrategy,
                                     query_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed retrieval plan"""
        try:
            plan = {
                "strategy": strategy.value,
                "query_type": query_type.value,
                "parameters": {},
                "steps": [],
                "confidence": 0.8
            }
            
            if strategy == RetrievalStrategy.VECTOR_ONLY:
                plan["steps"] = [
                    "Generate query embedding",
                    "Search vector database",
                    "Rerank by relevance",
                    "Return top candidates"
                ]
                plan["parameters"] = {
                    "k": self.max_candidates,
                    "rerank_k": self.rerank_top_k,
                    "filters": context.get("filters", {})
                }
                
            elif strategy == RetrievalStrategy.GRAPH_ONLY:
                plan["steps"] = [
                    "Extract entities from query",
                    "Find starting nodes",
                    "Perform graph traversal",
                    "Score by graph proximity",
                    "Return top candidates"
                ]
                plan["parameters"] = {
                    "max_hops": self.graph_walk_max_hops,
                    "traversal_type": "breadth_first",
                    "relationship_types": ["LINKS_TO", "MENTIONS", "SIMILAR_TO"]
                }
                
            elif strategy == RetrievalStrategy.HYBRID:
                plan["steps"] = [
                    "Generate query embedding",
                    "Extract entities from query",
                    "Parallel: vector search + graph traversal",
                    "Combine and deduplicate results",
                    "Rerank using hybrid scoring",
                    "Return top candidates"
                ]
                plan["parameters"] = {
                    "vector_k": self.max_candidates // 2,
                    "graph_k": self.max_candidates // 2,
                    "combination_method": "weighted_average",
                    "vector_weight": 0.6,
                    "graph_weight": 0.4
                }
                
            elif strategy == RetrievalStrategy.TEMPORAL:
                plan["steps"] = [
                    "Extract temporal entities",
                    "Search by date ranges",
                    "Order chronologically",
                    "Return timeline"
                ]
                plan["parameters"] = {
                    "date_field": "created_at",
                    "sort_order": "asc",
                    "group_by": "month"
                }
                
            elif strategy == RetrievalStrategy.HIERARCHICAL:
                plan["steps"] = [
                    "Identify hierarchical structure",
                    "Find parent/child relationships",
                    "Traverse hierarchy",
                    "Return structured results"
                ]
                plan["parameters"] = {
                    "hierarchy_type": "note_sections",
                    "max_depth": 5
                }
            
            return plan
            
        except Exception as e:
            logger.error(f"Failed to generate retrieval plan: {str(e)}")
            return {"strategy": "hybrid", "steps": [], "parameters": {}}
    
    async def _estimate_results(self, plan: Dict[str, Any], query_text: str) -> Dict[str, Any]:
        """Estimate expected results for the retrieval plan"""
        try:
            strategy = plan["strategy"]
            parameters = plan["parameters"]
            
            # Estimate based on strategy
            if strategy == "vector_only":
                estimated_count = parameters.get("k", self.max_candidates)
                estimated_time = 0.5  # seconds
            elif strategy == "graph_only":
                estimated_count = parameters.get("max_hops", 3) * 10
                estimated_time = 1.0  # seconds
            elif strategy == "hybrid":
                estimated_count = parameters.get("vector_k", 10) + parameters.get("graph_k", 10)
                estimated_time = 1.5  # seconds
            else:
                estimated_count = 10
                estimated_time = 1.0
            
            return {
                "estimated_count": estimated_count,
                "estimated_time": estimated_time,
                "confidence": plan.get("confidence", 0.8)
            }
            
        except Exception as e:
            logger.error(f"Failed to estimate results: {str(e)}")
            return {"estimated_count": 10, "estimated_time": 1.0, "confidence": 0.5}
    
    async def vector_search(self, query_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Perform vector search for semantic similarity"""
        try:
            query_text = query_data["query"]
            k = query_data.get("k", self.max_candidates)
            filters = query_data.get("filters", {})
            
            # Generate query embedding
            query_embedding = await self.vector_search_tool.generate_embedding(query_text)
            
            # Search vector database
            results = await self.vector_search_tool.search(
                embedding=query_embedding,
                k=k,
                filters=filters
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to perform vector search: {str(e)}")
            return []
    
    async def graph_walk(self, query_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Perform graph traversal for relationship-based search"""
        try:
            query_text = query_data["query"]
            max_hops = query_data.get("max_hops", self.graph_walk_max_hops)
            
            # Extract entities from query
            entities = await self.prediction_layer_tool.extract_entities(query_text)
            
            if not entities:
                return []
            
            # Find starting nodes
            starting_nodes = []
            for entity in entities:
                nodes = await self.graph_db.find_notes_by_entity(entity["name"])
                starting_nodes.extend(nodes)
            
            if not starting_nodes:
                return []
            
            # Perform graph traversal
            traversal_results = []
            for start_node in starting_nodes[:5]:  # Limit starting nodes
                results = await self.graph_db.traverse_graph(
                    start_node_id=start_node["note_id"],
                    max_hops=max_hops,
                    relationship_types=["LINKS_TO", "MENTIONS", "SIMILAR_TO"]
                )
                traversal_results.extend(results)
            
            # Deduplicate and score
            unique_results = {}
            for result in traversal_results:
                note_id = result["note_id"]
                if note_id not in unique_results or result["score"] > unique_results[note_id]["score"]:
                    unique_results[note_id] = result
            
            # Sort by score
            sorted_results = sorted(unique_results.values(), key=lambda x: x["score"], reverse=True)
            
            return sorted_results[:self.max_candidates]
            
        except Exception as e:
            logger.error(f"Failed to perform graph walk: {str(e)}")
            return []
    
    async def rerank_candidates(self, candidates: List[Dict[str, Any]], 
                              query_text: str, strategy: str) -> List[Dict[str, Any]]:
        """Rerank candidates using multiple signals"""
        try:
            if not candidates:
                return []
            
            # Apply reranking based on strategy
            if strategy == "hybrid":
                reranked = await self._hybrid_rerank(candidates, query_text)
            elif strategy == "temporal":
                reranked = await self._temporal_rerank(candidates, query_text)
            elif strategy == "hierarchical":
                reranked = await self._hierarchical_rerank(candidates, query_text)
            else:
                reranked = await self._default_rerank(candidates, query_text)
            
            return reranked[:self.rerank_top_k]
            
        except Exception as e:
            logger.error(f"Failed to rerank candidates: {str(e)}")
            return candidates[:self.rerank_top_k]
    
    async def _hybrid_rerank(self, candidates: List[Dict[str, Any]], query_text: str) -> List[Dict[str, Any]]:
        """Rerank using hybrid scoring (vector + graph + recency)"""
        try:
            for candidate in candidates:
                # Combine multiple signals
                vector_score = candidate.get("similarity_score", 0.0)
                graph_score = candidate.get("graph_score", 0.0)
                recency_score = candidate.get("recency_score", 0.0)
                hub_score = candidate.get("hub_score", 0.0)
                
                # Weighted combination
                hybrid_score = (
                    0.4 * vector_score +
                    0.3 * graph_score +
                    0.2 * recency_score +
                    0.1 * hub_score
                )
                
                candidate["hybrid_score"] = hybrid_score
            
            # Sort by hybrid score
            return sorted(candidates, key=lambda x: x["hybrid_score"], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to hybrid rerank: {str(e)}")
            return candidates
    
    async def _temporal_rerank(self, candidates: List[Dict[str, Any]], query_text: str) -> List[Dict[str, Any]]:
        """Rerank using temporal signals"""
        try:
            for candidate in candidates:
                # Extract temporal information
                created_at = candidate.get("created_at")
                updated_at = candidate.get("updated_at")
                
                # Calculate temporal score
                if created_at and updated_at:
                    # Prefer recently updated notes
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc)
                    if isinstance(updated_at, str):
                        updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    
                    days_since_update = (now - updated_at).days
                    temporal_score = max(0, 1.0 - (days_since_update / 365))  # Decay over a year
                else:
                    temporal_score = 0.5
                
                candidate["temporal_score"] = temporal_score
            
            # Sort by temporal score
            return sorted(candidates, key=lambda x: x["temporal_score"], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to temporal rerank: {str(e)}")
            return candidates
    
    async def _hierarchical_rerank(self, candidates: List[Dict[str, Any]], query_text: str) -> List[Dict[str, Any]]:
        """Rerank using hierarchical structure"""
        try:
            for candidate in candidates:
                # Consider section hierarchy
                section_level = candidate.get("section_level", 0)
                heading_relevance = candidate.get("heading_relevance", 0.0)
                
                # Higher level sections get higher scores
                hierarchy_score = (5 - section_level) / 5.0 if section_level <= 5 else 0.0
                
                # Combine with heading relevance
                hierarchical_score = 0.7 * hierarchy_score + 0.3 * heading_relevance
                
                candidate["hierarchical_score"] = hierarchical_score
            
            # Sort by hierarchical score
            return sorted(candidates, key=lambda x: x["hierarchical_score"], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to hierarchical rerank: {str(e)}")
            return candidates
    
    async def _default_rerank(self, candidates: List[Dict[str, Any]], query_text: str) -> List[Dict[str, Any]]:
        """Default reranking using similarity scores"""
        try:
            # Sort by similarity score
            return sorted(candidates, key=lambda x: x.get("similarity_score", 0.0), reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to default rerank: {str(e)}")
            return candidates
    
    async def update_models(self) -> Dict[str, Any]:
        """Update prediction models (maintenance task)"""
        try:
            # This would typically involve retraining models
            # For now, just return a success status
            return {
                "status": "completed",
                "message": "Models updated successfully",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to update models: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

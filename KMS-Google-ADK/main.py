"""
Main entry point for KMS-Google-ADK MVP
Simple demonstration of the multi-agent system.
"""

import os
import json
from typing import List, Dict, Any

# Import our tools
from tools.local_note_tool import LocalNoteTool
from tools.simple_entity_tool import SimpleEntityTool
from tools.vector_search_tool import VectorSearchTool
from tools.graph_update_tool import GraphUpdateTool
from tools.prediction_layer_tool import PredictionLayerTool


class SimpleOrchestrator:
    """Simple orchestrator for the MVP system."""
    
    def __init__(self, base_path: str = "notes"):
        """Initialize the orchestrator with all tools."""
        self.base_path = base_path
        
        # Initialize tools
        self.note_tool = LocalNoteTool(base_path)
        self.entity_tool = SimpleEntityTool()
        self.vector_tool = VectorSearchTool()
        self.graph_tool = GraphUpdateTool()
        self.prediction_tool = PredictionLayerTool()
        
        print("✅ KMS-Google-ADK MVP initialized successfully!")
    
    def add_note(self, path: str, title: str, content: str, tags: List[str] = None) -> Dict[str, Any]:
        """
        Add a new note to the system.
        
        Args:
            path: GCS path for the note
            title: Note title
            content: Note content
            tags: Optional tags
            
        Returns:
            Result dictionary
        """
        print(f"📝 Adding note: {title}")
        
        # Create note
        frontmatter = {
            "title": title,
            "tags": tags or []
        }
        
        result = self.note_tool.create_or_update(path, frontmatter, content)
        
        if result["status"] == "error":
            return result
        
        note_id = result["note_id"]
        print(f"   ✅ Note created with ID: {note_id}")
        
        # Extract entities
        print("   🔍 Extracting entities...")
        entities = self.entity_tool.extract_entities(content)
        print(f"   ✅ Found {len(entities['entities'])} entities, {len(entities['keyphrases'])} keyphrases")
        
        # Create simple embedding (placeholder)
        embedding = self._create_simple_embedding(content)
        
        # Store in vector database
        print("   💾 Storing in vector database...")
        self.vector_tool.upsert_embedding(
            note_id=note_id,
            path=result["path"],
            title=title,
            content=content,
            embedding=embedding,
            metadata={"tags": tags or []}
        )
        
        # Update graph
        print("   🕸️  Updating knowledge graph...")
        self.graph_tool.upsert_node(
            node_id=note_id,
            node_type="note",
            title=title,
            path=result["path"],
            metadata={"tags": tags or []}
        )
        
        print(f"   ✅ Note '{title}' processed successfully!")
        return result
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for notes using the query.
        
        Args:
            query: Search query
            
        Returns:
            List of search results
        """
        print(f"🔍 Searching for: '{query}'")
        
        # Plan the query
        plan = self.prediction_tool.plan_query(query)
        print(f"   📋 Query plan: {plan.query_type} using {plan.strategy}")
        
        # Create simple query embedding
        query_embedding = self._create_simple_embedding(query)
        
        # Search vector database
        print("   🔍 Searching vector database...")
        results = self.vector_tool.search(query_embedding, k=plan.top_k, filters=plan.filters)
        
        if not results:
            # Fallback to text search
            print("   🔍 Fallback to text search...")
            results = self.vector_tool.search_by_text(query, k=plan.top_k, filters=plan.filters)
        
        # Rerank results
        print("   📊 Reranking results...")
        reranked = self.prediction_tool.rerank_candidates(results, query)
        
        print(f"   ✅ Found {len(reranked)} results")
        return reranked
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge graph."""
        return self.graph_tool.get_graph_stats()
    
    def _create_simple_embedding(self, text: str) -> List[float]:
        """
        Create a simple embedding for text.
        This is a placeholder - in a real system, you'd use a proper embedding model.
        """
        # Simple hash-based embedding (not semantic, but works for demo)
        words = text.lower().split()
        embedding = [0.0] * 10  # 10-dimensional embedding
        
        for i, word in enumerate(words[:10]):  # Use first 10 words
            # Simple hash-based value
            hash_val = hash(word) % 1000 / 1000.0
            embedding[i] = hash_val
        
        return embedding


def main():
    """Main function to demonstrate the system."""
    print("🚀 Starting KMS-Google-ADK MVP Demo")
    print("=" * 50)
    
    # Initialize orchestrator
    orchestrator = SimpleOrchestrator()
    
    # Add some sample notes
    print("\n📚 Adding sample notes...")
    
    sample_notes = [
        {
            "path": "notes/machine-learning.md",
            "title": "Machine Learning Basics",
            "content": """
# Machine Learning Basics

Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data.

## Key Concepts
- Supervised Learning: Learning with labeled data
- Unsupervised Learning: Finding patterns in unlabeled data
- Deep Learning: Neural networks with multiple layers

## Applications
- Image recognition
- Natural language processing
- Recommendation systems
            """,
            "tags": ["AI", "ML", "tutorial"]
        },
        {
            "path": "notes/python-programming.md",
            "title": "Python Programming Guide",
            "content": """
# Python Programming Guide

Python is a versatile programming language known for its simplicity and readability.

## Key Features
- Simple syntax
- Large standard library
- Strong community support
- Cross-platform compatibility

## Popular Libraries
- NumPy for numerical computing
- Pandas for data analysis
- FastAPI for web development
            """,
            "tags": ["programming", "python", "tutorial"]
        },
        {
            "path": "notes/cloud-computing.md",
            "title": "Cloud Computing Overview",
            "content": """
# Cloud Computing Overview

Cloud computing delivers computing services over the internet.

## Service Models
- IaaS: Infrastructure as a Service
- PaaS: Platform as a Service
- SaaS: Software as a Service

## Benefits
- Scalability
- Cost efficiency
- Reliability
- Security
            """,
            "tags": ["cloud", "infrastructure", "technology"]
        }
    ]
    
    # Add notes
    for note in sample_notes:
        orchestrator.add_note(**note)
        print()
    
    # Demonstrate search
    print("\n🔍 Demonstrating search capabilities...")
    
    search_queries = [
        "machine learning",
        "python programming",
        "cloud computing benefits",
        "AI and ML concepts"
    ]
    
    for query in search_queries:
        print(f"\n🔍 Query: '{query}'")
        results = orchestrator.search(query)
        
        for i, result in enumerate(results[:3], 1):  # Show top 3
            print(f"   {i}. {result.get('title', 'Unknown')} (score: {result.get('rerank_score', 0):.3f})")
            print(f"      {result.get('snippet', '')[:100]}...")
    
    # Show graph stats
    print("\n📊 Knowledge Graph Statistics:")
    stats = orchestrator.get_graph_stats()
    print(f"   Nodes: {stats.get('node_count', 0)}")
    print(f"   Edges: {stats.get('edge_count', 0)}")
    print(f"   Avg connections: {stats.get('avg_connections', 0):.2f}")
    
    print("\n✅ Demo completed successfully!")
    print("\nTo run the web interface:")
    print("   uvicorn ui.server:app --reload --host 0.0.0.0 --port 8080")


if __name__ == "__main__":
    main()

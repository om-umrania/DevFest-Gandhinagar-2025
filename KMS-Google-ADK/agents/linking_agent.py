"""
Linking Agent for KMS-Google-ADK
Handles bi-directional semantic links between documents and concepts.
"""

from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timezone
import asyncio
import logging
import sqlite3
import json
from dataclasses import dataclass
from enum import Enum

from tools.vector_search_tool import VectorSearchTool
from tools.simple_entity_extraction_tool import SimpleEntityExtractionTool as EntityExtractionTool


class LinkType(Enum):
    """Types of semantic links."""
    RELATED = "related"
    SIMILAR = "similar"
    REFERENCES = "references"
    CONTAINS = "contains"
    PART_OF = "part_of"
    OPPOSITE = "opposite"


@dataclass
class SemanticLink:
    """Represents a semantic link between two entities."""
    source_id: str
    target_id: str
    link_type: LinkType
    strength: float
    context: str
    created_at: datetime
    metadata: Dict[str, Any]


class LinkingAgent:
    """
    Agent responsible for creating and managing semantic links between documents and concepts.
    
    This agent handles:
    - Detecting semantic relationships between documents
    - Creating bi-directional links
    - Maintaining link strength and context
    - Suggesting new connections
    - Link discovery and traversal
    """
    
    def __init__(self, db_path: str = "kms_index.db"):
        """
        Initialize the linking agent.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Initialize tools
        self.vector_search_tool = VectorSearchTool(db_path)
        self.entity_extraction_tool = EntityExtractionTool(db_path)
        
        # Initialize database
        self._init_database()
        
        self.logger.info("Linking Agent initialized")
    
    def _init_database(self):
        """Initialize the linking database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create links table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS semantic_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                link_type TEXT NOT NULL,
                strength REAL NOT NULL,
                context TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_id, target_id, link_type)
            )
        """)
        
        # Create indexes for efficient querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_source ON semantic_links(source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_target ON semantic_links(target_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_type ON semantic_links(link_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_strength ON semantic_links(strength)")
        
        conn.commit()
        conn.close()
    
    async def find_semantic_links(
        self,
        document_id: str,
        threshold: float = 0.7,
        max_links: int = 10
    ) -> List[SemanticLink]:
        """
        Find semantic links for a given document.
        
        Args:
            document_id: ID of the document to find links for
            threshold: Minimum similarity threshold for links
            max_links: Maximum number of links to return
            
        Returns:
            List of semantic links
        """
        try:
            self.logger.info(f"Finding semantic links for document: {document_id}")
            
            # Get document embedding
            doc_embedding = await self.vector_search_tool.get_embedding(document_id)
            if not doc_embedding:
                self.logger.warning(f"No embedding found for document: {document_id}")
                return []
            
            # Find similar documents using vector search
            similar_docs = await self.vector_search_tool.find_similar(
                embedding=doc_embedding,
                threshold=threshold,
                limit=max_links * 2  # Get more to filter
            )
            
            links = []
            for doc in similar_docs:
                if doc.note_id == document_id:
                    continue  # Skip self
                
                # Calculate link strength based on similarity score
                strength = min(doc.score, 1.0)
                
                # Determine link type based on strength and context
                link_type = self._determine_link_type(strength, doc.metadata)
                
                # Create context from document metadata
                context = self._create_link_context(doc.metadata)
                
                link = SemanticLink(
                    source_id=document_id,
                    target_id=doc.note_id,
                    link_type=link_type,
                    strength=strength,
                    context=context,
                    created_at=datetime.now(timezone.utc),
                    metadata={
                        "similarity_score": doc.score,
                        "target_title": doc.metadata.get("title", ""),
                        "target_path": doc.metadata.get("path", "")
                    }
                )
                
                links.append(link)
            
            # Sort by strength and limit results
            links.sort(key=lambda x: x.strength, reverse=True)
            return links[:max_links]
            
        except Exception as e:
            self.logger.error(f"Failed to find semantic links: {str(e)}")
            return []
    
    def _determine_link_type(self, strength: float, metadata: Dict[str, Any]) -> LinkType:
        """
        Determine the type of semantic link based on strength and metadata.
        
        Args:
            strength: Link strength (0.0 to 1.0)
            metadata: Target document metadata
            
        Returns:
            Link type
        """
        if strength >= 0.9:
            return LinkType.SIMILAR
        elif strength >= 0.8:
            return LinkType.RELATED
        elif strength >= 0.6:
            return LinkType.REFERENCES
        else:
            return LinkType.RELATED
    
    def _create_link_context(self, metadata: Dict[str, Any]) -> str:
        """
        Create context string for a semantic link.
        
        Args:
            metadata: Document metadata
            
        Returns:
            Context string
        """
        title = metadata.get("title", "")
        heading = metadata.get("heading", "")
        
        if title and heading:
            return f"Links to '{title}' section '{heading}'"
        elif title:
            return f"Links to '{title}'"
        elif heading:
            return f"Links to section '{heading}'"
        else:
            return "Semantic link"
    
    async def create_links(
        self,
        source_id: str,
        links: List[SemanticLink]
    ) -> Dict[str, Any]:
        """
        Create semantic links in the database.
        
        Args:
            source_id: Source document ID
            links: List of links to create
            
        Returns:
            Dict with creation results
        """
        try:
            self.logger.info(f"Creating {len(links)} links for document: {source_id}")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            created_count = 0
            updated_count = 0
            
            for link in links:
                try:
                    # Check if link already exists
                    cursor.execute("""
                        SELECT id, strength FROM semantic_links
                        WHERE source_id = ? AND target_id = ? AND link_type = ?
                    """, (link.source_id, link.target_id, link.link_type.value))
                    
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Update existing link if strength is higher
                        if link.strength > existing[1]:
                            cursor.execute("""
                                UPDATE semantic_links
                                SET strength = ?, context = ?, metadata = ?, updated_at = CURRENT_TIMESTAMP
                                WHERE id = ?
                            """, (
                                link.strength,
                                link.context,
                                json.dumps(link.metadata),
                                existing[0]
                            ))
                            updated_count += 1
                    else:
                        # Create new link
                        cursor.execute("""
                            INSERT INTO semantic_links
                            (source_id, target_id, link_type, strength, context, metadata)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            link.source_id,
                            link.target_id,
                            link.link_type.value,
                            link.strength,
                            link.context,
                            json.dumps(link.metadata)
                        ))
                        created_count += 1
                
                except Exception as e:
                    self.logger.error(f"Failed to create link {link.source_id} -> {link.target_id}: {str(e)}")
                    continue
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Created {created_count} new links, updated {updated_count} existing links")
            
            return {
                "success": True,
                "created": created_count,
                "updated": updated_count,
                "total_processed": len(links)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create links: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_links(
        self,
        document_id: str,
        link_type: Optional[LinkType] = None,
        min_strength: float = 0.0
    ) -> List[SemanticLink]:
        """
        Get all links for a document.
        
        Args:
            document_id: Document ID
            link_type: Optional filter by link type
            min_strength: Minimum link strength
            
        Returns:
            List of semantic links
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = """
                SELECT source_id, target_id, link_type, strength, context, metadata, created_at
                FROM semantic_links
                WHERE (source_id = ? OR target_id = ?) AND strength >= ?
            """
            params = [document_id, document_id, min_strength]
            
            if link_type:
                query += " AND link_type = ?"
                params.append(link_type.value)
            
            query += " ORDER BY strength DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            links = []
            for row in rows:
                link = SemanticLink(
                    source_id=row[0],
                    target_id=row[1],
                    link_type=LinkType(row[2]),
                    strength=row[3],
                    context=row[4],
                    created_at=datetime.fromisoformat(row[6]),
                    metadata=json.loads(row[5]) if row[5] else {}
                )
                links.append(link)
            
            conn.close()
            return links
            
        except Exception as e:
            self.logger.error(f"Failed to get links: {str(e)}")
            return []
    
    async def get_link_graph(
        self,
        document_id: str,
        depth: int = 2,
        max_nodes: int = 50
    ) -> Dict[str, Any]:
        """
        Get a graph of connected documents.
        
        Args:
            document_id: Starting document ID
            depth: Maximum traversal depth
            max_nodes: Maximum number of nodes in graph
            
        Returns:
            Graph representation with nodes and edges
        """
        try:
            self.logger.info(f"Building link graph for document: {document_id}")
            
            visited = set()
            nodes = {}
            edges = []
            queue = [(document_id, 0)]  # (node_id, depth)
            
            while queue and len(visited) < max_nodes:
                current_id, current_depth = queue.pop(0)
                
                if current_id in visited or current_depth > depth:
                    continue
                
                visited.add(current_id)
                
                # Get document info
                doc_info = await self.vector_search_tool.get_document_info(current_id)
                if doc_info:
                    nodes[current_id] = {
                        "id": current_id,
                        "title": doc_info.get("title", ""),
                        "path": doc_info.get("path", ""),
                        "depth": current_depth
                    }
                
                # Get links for current document
                links = await self.get_links(current_id, min_strength=0.5)
                
                for link in links:
                    target_id = link.target_id if link.source_id == current_id else link.source_id
                    
                    if target_id not in visited and current_depth < depth:
                        queue.append((target_id, current_depth + 1))
                    
                    # Add edge
                    edge = {
                        "source": link.source_id,
                        "target": link.target_id,
                        "type": link.link_type.value,
                        "strength": link.strength,
                        "context": link.context
                    }
                    
                    # Avoid duplicate edges
                    if not any(e["source"] == edge["source"] and e["target"] == edge["target"] for e in edges):
                        edges.append(edge)
            
            return {
                "nodes": list(nodes.values()),
                "edges": edges,
                "total_nodes": len(nodes),
                "total_edges": len(edges)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to build link graph: {str(e)}")
            return {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0}
    
    async def suggest_links(
        self,
        document_id: str,
        based_on: str = "content"
    ) -> List[Dict[str, Any]]:
        """
        Suggest new semantic links for a document.
        
        Args:
            document_id: Document ID
            based_on: Basis for suggestions ("content", "entities", "tags")
            
        Returns:
            List of suggested links
        """
        try:
            self.logger.info(f"Suggesting links for document: {document_id}")
            
            suggestions = []
            
            if based_on == "content":
                # Find similar content
                similar_docs = await self.find_semantic_links(document_id, threshold=0.6)
                suggestions.extend([
                    {
                        "target_id": link.target_id,
                        "reason": f"Similar content (strength: {link.strength:.2f})",
                        "strength": link.strength,
                        "context": link.context
                    }
                    for link in similar_docs
                ])
            
            elif based_on == "entities":
                # Find documents with similar entities
                entities = await self.entity_extraction_tool.get_document_entities(document_id)
                for entity in entities:
                    related_docs = await self.entity_extraction_tool.find_related_documents(
                        entity["text"], limit=5
                    )
                    suggestions.extend([
                        {
                            "target_id": doc["note_id"],
                            "reason": f"Shares entity: {entity['text']}",
                            "strength": 0.7,  # Default strength for entity-based links
                            "context": f"Both documents mention '{entity['text']}'"
                        }
                        for doc in related_docs
                    ])
            
            # Remove duplicates and sort by strength
            seen = set()
            unique_suggestions = []
            for suggestion in suggestions:
                key = suggestion["target_id"]
                if key not in seen and key != document_id:
                    seen.add(key)
                    unique_suggestions.append(suggestion)
            
            unique_suggestions.sort(key=lambda x: x["strength"], reverse=True)
            
            return unique_suggestions[:10]  # Return top 10 suggestions
            
        except Exception as e:
            self.logger.error(f"Failed to suggest links: {str(e)}")
            return []
    
    async def update_links_for_document(
        self,
        document_id: str,
        force_update: bool = False
    ) -> Dict[str, Any]:
        """
        Update all links for a document.
        
        Args:
            document_id: Document ID
            force_update: Whether to force update existing links
            
        Returns:
            Dict with update results
        """
        try:
            self.logger.info(f"Updating links for document: {document_id}")
            
            # Find new semantic links
            new_links = await self.find_semantic_links(document_id)
            
            if not new_links:
                return {
                    "success": True,
                    "message": "No new links found",
                    "links_created": 0
                }
            
            # Create links
            result = await self.create_links(document_id, new_links)
            
            return {
                "success": True,
                "links_found": len(new_links),
                "links_created": result.get("created", 0),
                "links_updated": result.get("updated", 0)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to update links: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_link_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about semantic links.
        
        Returns:
            Dict with link statistics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total links
            cursor.execute("SELECT COUNT(*) FROM semantic_links")
            total_links = cursor.fetchone()[0]
            
            # Links by type
            cursor.execute("""
                SELECT link_type, COUNT(*) FROM semantic_links
                GROUP BY link_type
            """)
            links_by_type = dict(cursor.fetchall())
            
            # Average strength
            cursor.execute("SELECT AVG(strength) FROM semantic_links")
            avg_strength = cursor.fetchone()[0] or 0.0
            
            # Strongest links
            cursor.execute("""
                SELECT source_id, target_id, strength, link_type
                FROM semantic_links
                ORDER BY strength DESC
                LIMIT 5
            """)
            strongest_links = [
                {
                    "source": row[0],
                    "target": row[1],
                    "strength": row[2],
                    "type": row[3]
                }
                for row in cursor.fetchall()
            ]
            
            conn.close()
            
            return {
                "total_links": total_links,
                "links_by_type": links_by_type,
                "average_strength": round(avg_strength, 3),
                "strongest_links": strongest_links
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get link statistics: {str(e)}")
            return {
                "total_links": 0,
                "links_by_type": {},
                "average_strength": 0.0,
                "strongest_links": []
            }

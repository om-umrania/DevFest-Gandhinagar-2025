"""
Graph Update Tool for KMS-Google-ADK
Handles graph database operations for bi-directional links and relationships.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import sqlite3
import json
from datetime import datetime, timezone


@dataclass
class GraphEdge:
    """Represents a graph edge/relationship."""
    source_id: str
    target_id: str
    relationship: str
    score: float
    rationale: str
    metadata: Dict[str, Any]


class GraphUpdateTool:
    """Tool for managing graph relationships and bi-directional links."""
    
    def __init__(self, db_path: str = "kms_graph.db"):
        """Initialize with SQLite database for graph storage."""
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the graph database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create nodes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                title TEXT,
                path TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create edges table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS edges (
                edge_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relationship TEXT NOT NULL,
                score REAL NOT NULL,
                rationale TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES nodes (node_id),
                FOREIGN KEY (target_id) REFERENCES nodes (node_id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_relationship ON edges(relationship)")
        
        conn.commit()
        conn.close()
    
    def upsert_node(
        self, 
        node_id: str, 
        node_type: str, 
        title: str = None,
        path: str = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Insert or update a node in the graph."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            metadata_json = json.dumps(metadata or {})
            
            cursor.execute("""
                INSERT OR REPLACE INTO nodes 
                (node_id, node_type, title, path, metadata, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (node_id, node_type, title, path, metadata_json))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error upserting node: {e}")
            return False
    
    def upsert_edges(
        self, 
        note_id: str, 
        edges: List[Tuple[str, str, float, str]]
    ) -> bool:
        """
        Insert or update edges for a note.
        
        Args:
            note_id: Source note ID
            edges: List of (target_id, relationship, score, rationale) tuples
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for target_id, relationship, score, rationale in edges:
                edge_id = f"{note_id}->{target_id}:{relationship}"
                
                cursor.execute("""
                    INSERT OR REPLACE INTO edges 
                    (edge_id, source_id, target_id, relationship, score, rationale, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (edge_id, note_id, target_id, relationship, score, rationale))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error upserting edges: {e}")
            return False
    
    def get_edges(self, node_id: str, direction: str = "both") -> List[Dict[str, Any]]:
        """
        Get edges for a node.
        
        Args:
            node_id: Node ID
            direction: "in", "out", or "both"
            
        Returns:
            List of edge dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if direction == "in":
                query = "SELECT * FROM edges WHERE target_id = ?"
                cursor.execute(query, (node_id,))
                rows = cursor.fetchall()
            elif direction == "out":
                query = "SELECT * FROM edges WHERE source_id = ?"
                cursor.execute(query, (node_id,))
                rows = cursor.fetchall()
            else:  # both
                query = "SELECT * FROM edges WHERE source_id = ? OR target_id = ?"
                cursor.execute(query, (node_id, node_id))
                rows = cursor.fetchall()
            
            edges = []
            for row in rows:
                edges.append({
                    "edge_id": row[0],
                    "source_id": row[1],
                    "target_id": row[2],
                    "relationship": row[3],
                    "score": row[4],
                    "rationale": row[5],
                    "metadata": json.loads(row[6]) if row[6] else {},
                    "created_at": row[7],
                    "updated_at": row[8]
                })
            
            conn.close()
            return edges
            
        except Exception as e:
            print(f"Error getting edges: {e}")
            return []
    
    def get_related_notes(self, note_id: str, max_hops: int = 2) -> List[Dict[str, Any]]:
        """
        Get related notes within max_hops distance.
        
        Args:
            note_id: Starting note ID
            max_hops: Maximum number of hops to traverse
            
        Returns:
            List of related note information
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get direct connections
            cursor.execute("""
                SELECT DISTINCT 
                    CASE 
                        WHEN source_id = ? THEN target_id 
                        ELSE source_id 
                    END as related_id,
                    n.title, n.path, n.node_type
                FROM edges e
                JOIN nodes n ON (
                    CASE 
                        WHEN e.source_id = ? THEN e.target_id 
                        ELSE e.source_id 
                    END = n.node_id
                )
                WHERE source_id = ? OR target_id = ?
            """, (note_id, note_id, note_id, note_id))
            
            related = []
            for row in cursor.fetchall():
                related.append({
                    "note_id": row[0],
                    "title": row[1],
                    "path": row[2],
                    "node_type": row[3],
                    "hops": 1
                })
            
            conn.close()
            return related
            
        except Exception as e:
            print(f"Error getting related notes: {e}")
            return []
    
    def delete_edges(self, note_id: str) -> bool:
        """Delete all edges for a note."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM edges WHERE source_id = ? OR target_id = ?", 
                         (note_id, note_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error deleting edges: {e}")
            return False
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Node count
            cursor.execute("SELECT COUNT(*) FROM nodes")
            node_count = cursor.fetchone()[0]
            
            # Edge count
            cursor.execute("SELECT COUNT(*) FROM edges")
            edge_count = cursor.fetchone()[0]
            
            # Relationship types
            cursor.execute("SELECT relationship, COUNT(*) FROM edges GROUP BY relationship")
            relationships = dict(cursor.fetchall())
            
            conn.close()
            
            return {
                "node_count": node_count,
                "edge_count": edge_count,
                "relationships": relationships,
                "avg_connections": edge_count / max(node_count, 1)
            }
            
        except Exception as e:
            print(f"Error getting graph stats: {e}")
            return {}

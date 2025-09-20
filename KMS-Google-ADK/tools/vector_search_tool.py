"""
Vector Search Tool for KMS-Google-ADK
Handles semantic search using embeddings and vector similarity.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json
import sqlite3
from pathlib import Path
import hashlib
import struct


@dataclass
class SearchResult:
    """Represents a search result."""
    note_id: str
    path: str
    score: float
    snippet: str
    metadata: Dict[str, Any]


class VectorSearchTool:
    """Tool for semantic search using vector embeddings."""
    
    def __init__(self, db_path: str = "kms_index.db"):
        """Initialize with SQLite database for vector storage."""
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the vector database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create embeddings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                note_id TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                title TEXT,
                content TEXT,
                embedding BLOB,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index for faster searches
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_embeddings_path 
            ON embeddings(path)
        """)
        
        conn.commit()
        conn.close()
    
    def upsert_embedding(
        self, 
        note_id: str, 
        path: str, 
        title: str,
        content: str, 
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Insert or update an embedding in the database.
        
        Args:
            note_id: Unique identifier for the note
            path: GCS path to the note
            title: Note title
            content: Note content
            embedding: Vector embedding
            metadata: Additional metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Convert embedding to bytes (simple float array)
            embedding_bytes = struct.pack(f'{len(embedding)}f', *embedding)
            
            # Prepare metadata
            metadata_json = json.dumps(metadata or {})
            
            cursor.execute("""
                INSERT OR REPLACE INTO embeddings 
                (note_id, path, title, content, embedding, metadata, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (note_id, path, title, content, embedding_bytes, metadata_json))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error upserting embedding: {e}")
            return False
    
    def search(
        self, 
        query_embedding: List[float], 
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search for similar notes using vector similarity.
        
        Args:
            query_embedding: Query vector
            k: Number of results to return
            filters: Optional filters (path_prefix, tags, etc.)
            
        Returns:
            List of SearchResult objects
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build query with filters
            where_clause = "WHERE 1=1"
            params = []
            
            if filters:
                if "path_prefix" in filters:
                    where_clause += " AND path LIKE ?"
                    params.append(f"{filters['path_prefix']}%")
                
                if "tags" in filters and filters["tags"]:
                    # This would require a more complex query with JSON functions
                    # For now, we'll do a simple text search
                    tag_conditions = []
                    for tag in filters["tags"]:
                        tag_conditions.append("metadata LIKE ?")
                        params.append(f'%"{tag}"%')
                    if tag_conditions:
                        where_clause += f" AND ({' OR '.join(tag_conditions)})"
            
            # Get all embeddings
            cursor.execute(f"""
                SELECT note_id, path, title, content, embedding, metadata
                FROM embeddings
                {where_clause}
            """, params)
            
            results = []
            query_vec = query_embedding
            
            for row in cursor.fetchall():
                note_id, path, title, content, embedding_bytes, metadata_json = row
                
                # Load embedding
                embedding = list(struct.unpack(f'{len(query_vec)}f', embedding_bytes))
                
                # Calculate cosine similarity
                similarity = self._cosine_similarity(query_vec, embedding)
                
                # Generate snippet
                snippet = self._generate_snippet(content, title)
                
                # Parse metadata
                metadata = json.loads(metadata_json) if metadata_json else {}
                
                results.append(SearchResult(
                    note_id=note_id,
                    path=path,
                    score=float(similarity),
                    snippet=snippet,
                    metadata=metadata
                ))
            
            conn.close()
            
            # Sort by score and return top k
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:k]
            
        except Exception as e:
            print(f"Error searching embeddings: {e}")
            return []
    
    def search_by_text(
        self, 
        query_text: str, 
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search by text query (requires embedding generation).
        This is a placeholder - in practice, you'd use an embedding model.
        
        Args:
            query_text: Text query
            k: Number of results to return
            filters: Optional filters
            
        Returns:
            List of SearchResult objects
        """
        # For now, do a simple text search
        # In practice, you'd generate embeddings for the query
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Simple text search
            cursor.execute("""
                SELECT note_id, path, title, content, metadata
                FROM embeddings
                WHERE content LIKE ? OR title LIKE ?
                ORDER BY updated_at DESC
                LIMIT ?
            """, (f"%{query_text}%", f"%{query_text}%", k))
            
            results = []
            for row in cursor.fetchall():
                note_id, path, title, content, metadata_json = row
                metadata = json.loads(metadata_json) if metadata_json else {}
                
                results.append(SearchResult(
                    note_id=note_id,
                    path=path,
                    score=0.5,  # Placeholder score
                    snippet=self._generate_snippet(content, title),
                    metadata=metadata
                ))
            
            conn.close()
            return results
            
        except Exception as e:
            print(f"Error searching by text: {e}")
            return []
    
    def get_note_embedding(self, note_id: str) -> Optional[List[float]]:
        """Get embedding for a specific note."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT embedding FROM embeddings WHERE note_id = ?
            """, (note_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                embedding_bytes = row[0]
                # Calculate the number of floats in the embedding
                num_floats = len(embedding_bytes) // 4  # 4 bytes per float
                return list(struct.unpack(f'{num_floats}f', embedding_bytes))
            
            return None
            
        except Exception as e:
            print(f"Error getting note embedding: {e}")
            return None
    
    def delete_embedding(self, note_id: str) -> bool:
        """Delete embedding for a note."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM embeddings WHERE note_id = ?", (note_id,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error deleting embedding: {e}")
            return False
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # Calculate norms
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _generate_snippet(self, content: str, title: str, max_length: int = 200) -> str:
        """Generate a snippet from content."""
        if not content:
            return title or ""
        
        # Try to find a good sentence to start with
        sentences = content.split('. ')
        snippet = sentences[0] if sentences else content
        
        # Truncate if too long
        if len(snippet) > max_length:
            snippet = snippet[:max_length].rsplit(' ', 1)[0] + "..."
        
        return snippet

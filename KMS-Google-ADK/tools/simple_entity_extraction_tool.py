"""
Simple Entity Extraction Tool for KMS-Google-ADK
A lightweight version that doesn't require external NLP libraries.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import asyncio
import logging
import sqlite3
import json
import re
from dataclasses import dataclass


@dataclass
class Entity:
    """Represents an extracted entity."""
    text: str
    label: str
    start: int
    end: int
    confidence: float


class SimpleEntityExtractionTool:
    """
    Simple entity extraction tool using regex patterns.
    
    This is a lightweight alternative to spaCy-based extraction
    that works without external dependencies.
    """
    
    def __init__(self, db_path: str = "kms_index.db"):
        """
        Initialize the entity extraction tool.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Initialize database
        self._init_database()
        
        # Define entity patterns
        self.patterns = {
            "PERSON": [
                r"\b[A-Z][a-z]+ [A-Z][a-z]+\b",  # First Last
                r"\b[A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+\b",  # First M. Last
            ],
            "ORG": [
                r"\b[A-Z][a-z]+ (?:Inc|Corp|LLC|Ltd|Company|Corporation)\b",
                r"\b[A-Z][a-z]+ (?:University|College|Institute|School)\b",
                r"\b[A-Z][a-z]+ (?:Hospital|Medical|Center|Clinic)\b",
            ],
            "GPE": [  # Geopolitical entities
                r"\b[A-Z][a-z]+ (?:City|State|Country|Nation)\b",
                r"\b(?:United States|USA|UK|Canada|Germany|France|Japan|China)\b",
            ],
            "TECH": [  # Technology terms
                r"\b(?:Python|Java|JavaScript|React|Vue|Angular|Node\.js|Django|Flask)\b",
                r"\b(?:Machine Learning|AI|Artificial Intelligence|Deep Learning)\b",
                r"\b(?:Cloud Computing|AWS|Azure|Google Cloud|Docker|Kubernetes)\b",
            ],
            "DATE": [
                r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
                r"\b\d{1,2}/\d{1,2}/\d{4}\b",
                r"\b\d{4}-\d{2}-\d{2}\b",
            ],
            "MONEY": [
                r"\$\d+(?:,\d{3})*(?:\.\d{2})?\b",
                r"\b\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|USD|euros?|EUR)\b",
            ],
            "PERCENT": [
                r"\b\d+(?:\.\d+)?%\b",
            ],
            "EMAIL": [
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            ],
            "URL": [
                r"https?://[^\s]+",
                r"www\.[^\s]+",
            ],
        }
        
        self.logger.info("Simple Entity Extraction Tool initialized")
    
    def _init_database(self):
        """Initialize the entity database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create entities table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id TEXT NOT NULL,
                text TEXT NOT NULL,
                label TEXT NOT NULL,
                start_pos INTEGER NOT NULL,
                end_pos INTEGER NOT NULL,
                confidence REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(note_id, text, start_pos, end_pos)
            )
        """)
        
        # Create entity relationships table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity1_id INTEGER NOT NULL,
                entity2_id INTEGER NOT NULL,
                relationship_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity1_id) REFERENCES entities (id),
                FOREIGN KEY (entity2_id) REFERENCES entities (id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def extract_entities(
        self,
        document_path: str,
        content: str,
        min_confidence: float = 0.5
    ) -> Dict[str, Any]:
        """
        Extract entities from text content.
        
        Args:
            document_path: Path to the document
            content: Text content to extract entities from
            min_confidence: Minimum confidence threshold
            
        Returns:
            Dict with extracted entities and metadata
        """
        try:
            self.logger.info(f"Extracting entities from {document_path}")
            
            entities = []
            keyphrases = []
            
            # Extract entities using patterns
            for label, patterns in self.patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        entity = Entity(
                            text=match.group(),
                            label=label,
                            start=match.start(),
                            end=match.end(),
                            confidence=0.8  # Default confidence for regex matches
                        )
                        
                        if entity.confidence >= min_confidence:
                            entities.append(entity)
            
            # Extract keyphrases (simple n-gram approach)
            keyphrases = self._extract_keyphrases(content)
            
            # Store entities in database
            if entities:
                await self._store_entities(document_path, entities)
            
            self.logger.info(f"Extracted {len(entities)} entities and {len(keyphrases)} keyphrases")
            
            return {
                "success": True,
                "entities": [
                    {
                        "text": entity.text,
                        "label": entity.label,
                        "start": entity.start,
                        "end": entity.end,
                        "confidence": entity.confidence
                    }
                    for entity in entities
                ],
                "keyphrases": keyphrases,
                "total_entities": len(entities),
                "total_keyphrases": len(keyphrases)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to extract entities: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "entities": [],
                "keyphrases": []
            }
    
    def _extract_keyphrases(self, content: str, max_length: int = 3) -> List[str]:
        """
        Extract keyphrases using simple n-gram approach.
        
        Args:
            content: Text content
            max_length: Maximum n-gram length
            
        Returns:
            List of keyphrases
        """
        # Clean and tokenize
        words = re.findall(r'\b[a-zA-Z]+\b', content.lower())
        
        keyphrases = []
        
        # Generate n-grams
        for n in range(2, max_length + 1):
            for i in range(len(words) - n + 1):
                phrase = " ".join(words[i:i + n])
                
                # Filter out common stop words
                if not self._is_stop_phrase(phrase):
                    keyphrases.append(phrase)
        
        # Count frequency and return most common
        phrase_counts = {}
        for phrase in keyphrases:
            phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
        
        # Return top keyphrases
        sorted_phrases = sorted(phrase_counts.items(), key=lambda x: x[1], reverse=True)
        return [phrase for phrase, count in sorted_phrases[:20] if count > 1]
    
    def _is_stop_phrase(self, phrase: str) -> bool:
        """Check if a phrase should be filtered out."""
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "up", "about", "into", "through", "during",
            "before", "after", "above", "below", "between", "among", "is", "are",
            "was", "were", "be", "been", "being", "have", "has", "had", "do",
            "does", "did", "will", "would", "could", "should", "may", "might",
            "must", "can", "this", "that", "these", "those", "i", "you", "he",
            "she", "it", "we", "they", "me", "him", "her", "us", "them"
        }
        
        words = phrase.split()
        return any(word in stop_words for word in words)
    
    async def _store_entities(self, document_path: str, entities: List[Entity]):
        """Store entities in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for entity in entities:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO entities
                    (note_id, text, label, start_pos, end_pos, confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    document_path,
                    entity.text,
                    entity.label,
                    entity.start,
                    entity.end,
                    entity.confidence
                ))
            except Exception as e:
                self.logger.warning(f"Failed to store entity {entity.text}: {str(e)}")
        
        conn.commit()
        conn.close()
    
    async def get_document_entities(self, document_path: str) -> List[Dict[str, Any]]:
        """Get all entities for a document."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT text, label, start_pos, end_pos, confidence
            FROM entities
            WHERE note_id = ?
            ORDER BY start_pos
        """, (document_path,))
        
        entities = [
            {
                "text": row[0],
                "label": row[1],
                "start": row[2],
                "end": row[3],
                "confidence": row[4]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return entities
    
    async def find_related_documents(
        self,
        entity_text: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find documents containing a specific entity."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT note_id, COUNT(*) as entity_count
            FROM entities
            WHERE text LIKE ?
            GROUP BY note_id
            ORDER BY entity_count DESC
            LIMIT ?
        """, (f"%{entity_text}%", limit))
        
        results = [
            {
                "note_id": row[0],
                "entity_count": row[1]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return results
    
    async def get_entity_statistics(self) -> Dict[str, Any]:
        """Get statistics about extracted entities."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total entities
        cursor.execute("SELECT COUNT(*) FROM entities")
        total_entities = cursor.fetchone()[0]
        
        # Entities by label
        cursor.execute("""
            SELECT label, COUNT(*) FROM entities
            GROUP BY label
            ORDER BY COUNT(*) DESC
        """)
        entities_by_label = dict(cursor.fetchall())
        
        # Most common entities
        cursor.execute("""
            SELECT text, COUNT(*) as frequency
            FROM entities
            GROUP BY text
            ORDER BY frequency DESC
            LIMIT 10
        """)
        most_common = [
            {"text": row[0], "frequency": row[1]}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return {
            "total_entities": total_entities,
            "entities_by_label": entities_by_label,
            "most_common_entities": most_common
        }
    
    async def cleanup_old_entities(self, older_than_days: int = 30):
        """Clean up old entities."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM entities
            WHERE created_at < datetime('now', '-{} days')
        """.format(older_than_days))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        self.logger.info(f"Cleaned up {deleted_count} old entities")
        return deleted_count

"""
Ingestion Agent for Obsidian KMS
Handles note normalization, entity extraction, and indexing
"""

import asyncio
import hashlib
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

from google.adk import Agent, Tool, Memory
from google.adk.agents import AgentConfig

from tools.note_creation_tool import NoteCreationTool
from tools.entity_extraction_tool import EntityExtractionTool
from tools.vector_search_tool import VectorSearchTool
from memory.adapters.neo4j import Neo4jAdapter
from memory.adapters.pgvector import PgVectorAdapter

logger = logging.getLogger(__name__)


class IngestionAgent(Agent):
    """
    Ingestion Agent handles note normalization and indexing.
    
    Responsibilities:
    - Parse markdown frontmatter and content
    - Extract entities and keyphrases
    - Generate embeddings and persist to Vector DB
    - Create explicit links from note content
    - Emit events for Linking Agent
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        
        # Initialize tools
        self.note_creation_tool = NoteCreationTool()
        self.entity_extraction_tool = EntityExtractionTool()
        self.vector_search_tool = VectorSearchTool()
        
        # Initialize memory adapters
        self.graph_db = Neo4jAdapter()
        self.vector_db = PgVectorAdapter()
        
        # Configuration
        self.max_content_length = config.get("max_content_length", 100000)
        self.embedding_model = config.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
        
    async def process_note(self, note_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single note through the ingestion pipeline
        
        Args:
            note_data: Note data with path, content, and metadata
            
        Returns:
            Processing result with note ID, entities, and embeddings
        """
        try:
            note_path = note_data["path"]
            content = note_data["content"]
            
            logger.info(f"Processing note: {note_path}")
            
            # 1. Parse markdown and frontmatter
            parsed_note = await self._parse_markdown(note_path, content)
            
            # 2. Validate and normalize
            normalized_note = await self._normalize_note(parsed_note)
            
            # 3. Extract entities and keyphrases
            entities = await self._extract_entities(normalized_note)
            
            # 4. Generate embeddings
            embeddings = await self._generate_embeddings(normalized_note)
            
            # 5. Create/update note in database
            note_id = await self._persist_note(normalized_note, entities, embeddings)
            
            # 6. Extract explicit links
            explicit_links = await self._extract_explicit_links(normalized_note)
            
            result = {
                "note_id": note_id,
                "path": note_path,
                "entities": entities,
                "embeddings": embeddings,
                "explicit_links": explicit_links,
                "processing_time": datetime.now().isoformat(),
                "status": "success"
            }
            
            logger.info(f"Successfully processed note {note_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process note {note_data.get('path', 'unknown')}: {str(e)}")
            return {
                "note_id": None,
                "path": note_data.get("path", "unknown"),
                "error": str(e),
                "status": "error"
            }
    
    async def _parse_markdown(self, path: str, content: str) -> Dict[str, Any]:
        """Parse markdown content and extract frontmatter"""
        import frontmatter
        
        try:
            # Parse frontmatter and content
            parsed = frontmatter.loads(content)
            
            # Extract metadata
            frontmatter_data = parsed.metadata or {}
            body_content = parsed.content
            
            # Extract sections and headings
            sections = await self._extract_sections(body_content)
            
            return {
                "path": path,
                "frontmatter": frontmatter_data,
                "content": body_content,
                "sections": sections,
                "word_count": len(body_content.split()),
                "checksum": hashlib.sha256(content.encode()).hexdigest()
            }
            
        except Exception as e:
            logger.error(f"Failed to parse markdown for {path}: {str(e)}")
            raise
    
    async def _extract_sections(self, content: str) -> List[Dict[str, Any]]:
        """Extract sections and headings from markdown content"""
        sections = []
        lines = content.split('\n')
        current_section = None
        section_content = []
        
        for i, line in enumerate(lines):
            # Check if line is a heading
            if line.strip().startswith('#'):
                # Save previous section
                if current_section:
                    current_section['content'] = '\n'.join(section_content).strip()
                    current_section['end_line'] = i - 1
                    sections.append(current_section)
                
                # Start new section
                level = len(line) - len(line.lstrip('#'))
                heading = line.lstrip('# ').strip()
                
                current_section = {
                    'heading': heading,
                    'level': level,
                    'start_line': i + 1,
                    'content': ''
                }
                section_content = []
            else:
                section_content.append(line)
        
        # Add final section
        if current_section:
            current_section['content'] = '\n'.join(section_content).strip()
            current_section['end_line'] = len(lines)
            sections.append(current_section)
        
        return sections
    
    async def _normalize_note(self, parsed_note: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize note data"""
        # Ensure required fields
        if not parsed_note["frontmatter"].get("title"):
            parsed_note["frontmatter"]["title"] = Path(parsed_note["path"]).stem
        
        # Add timestamps
        now = datetime.now().isoformat()
        if not parsed_note["frontmatter"].get("created_at"):
            parsed_note["frontmatter"]["created_at"] = now
        parsed_note["frontmatter"]["updated_at"] = now
        
        # Validate content length
        if len(parsed_note["content"]) > self.max_content_length:
            logger.warning(f"Note {parsed_note['path']} exceeds max length, truncating")
            parsed_note["content"] = parsed_note["content"][:self.max_content_length]
        
        # Normalize tags
        tags = parsed_note["frontmatter"].get("tags", [])
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",")]
        parsed_note["frontmatter"]["tags"] = [tag.lower().strip() for tag in tags if tag.strip()]
        
        return parsed_note
    
    async def _extract_entities(self, note: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract entities and keyphrases from note content"""
        try:
            # Use entity extraction tool
            entities = await self.entity_extraction_tool.extract_entities(
                note["content"],
                note["frontmatter"].get("title", ""),
                note["sections"]
            )
            
            return entities
            
        except Exception as e:
            logger.error(f"Failed to extract entities: {str(e)}")
            return []
    
    async def _generate_embeddings(self, note: Dict[str, Any]) -> Dict[str, List[float]]:
        """Generate embeddings for note content and sections"""
        try:
            embeddings = {}
            
            # Generate embedding for full content
            content_embedding = await self.vector_search_tool.generate_embedding(
                note["content"]
            )
            embeddings["content"] = content_embedding
            
            # Generate embeddings for sections
            section_embeddings = []
            for section in note["sections"]:
                if section["content"].strip():
                    section_emb = await self.vector_search_tool.generate_embedding(
                        f"{section['heading']}\n{section['content']}"
                    )
                    section_embeddings.append({
                        "heading": section["heading"],
                        "level": section["level"],
                        "embedding": section_emb
                    })
            
            embeddings["sections"] = section_embeddings
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
            return {}
    
    async def _persist_note(self, note: Dict[str, Any], entities: List[Dict[str, Any]], 
                          embeddings: Dict[str, List[float]]) -> str:
        """Persist note to database"""
        try:
            # Create note in graph database
            note_id = await self.graph_db.create_note(
                path=note["path"],
                title=note["frontmatter"]["title"],
                content=note["content"],
                frontmatter=note["frontmatter"],
                sections=note["sections"],
                checksum=note["checksum"]
            )
            
            # Store embeddings in vector database
            if embeddings.get("content"):
                await self.vector_db.store_embedding(
                    note_id=note_id,
                    content=note["content"],
                    embedding=embeddings["content"],
                    metadata={
                        "type": "content",
                        "path": note["path"],
                        "title": note["frontmatter"]["title"]
                    }
                )
            
            # Store section embeddings
            for section_emb in embeddings.get("sections", []):
                await self.vector_db.store_embedding(
                    note_id=note_id,
                    content=section_emb["heading"] + "\n" + section_emb.get("content", ""),
                    embedding=section_emb["embedding"],
                    metadata={
                        "type": "section",
                        "heading": section_emb["heading"],
                        "level": section_emb["level"],
                        "path": note["path"]
                    }
                )
            
            # Store entities
            for entity in entities:
                await self.graph_db.create_entity(
                    name=entity["name"],
                    entity_type=entity["type"],
                    description=entity.get("description", ""),
                    aliases=entity.get("aliases", []),
                    confidence=entity.get("confidence", 0.0)
                )
                
                # Create mention relationship
                await self.graph_db.create_mention(
                    note_id=note_id,
                    entity_name=entity["name"],
                    context=entity.get("context", ""),
                    confidence=entity.get("confidence", 0.0)
                )
            
            return note_id
            
        except Exception as e:
            logger.error(f"Failed to persist note: {str(e)}")
            raise
    
    async def _extract_explicit_links(self, note: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract explicit links from note content (wikilinks, URLs)"""
        import re
        
        explicit_links = []
        content = note["content"]
        
        # Extract wikilinks [[link]]
        wikilink_pattern = r'\[\[([^\]]+)\]\]'
        wikilinks = re.findall(wikilink_pattern, content)
        
        for link in wikilinks:
            explicit_links.append({
                "type": "wikilink",
                "target": link,
                "source": note["path"],
                "confidence": 1.0
            })
        
        # Extract URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, content)
        
        for url in urls:
            explicit_links.append({
                "type": "url",
                "target": url,
                "source": note["path"],
                "confidence": 1.0
            })
        
        return explicit_links
    
    async def reindex_notes(self) -> Dict[str, Any]:
        """Reindex all notes (maintenance task)"""
        try:
            # Get all notes from graph database
            notes = await self.graph_db.get_all_notes()
            
            reindexed_count = 0
            errors = []
            
            for note in notes:
                try:
                    # Re-process note
                    result = await self.process_note({
                        "path": note["path"],
                        "content": note["content"]
                    })
                    
                    if result["status"] == "success":
                        reindexed_count += 1
                    else:
                        errors.append(f"Failed to reindex {note['path']}: {result.get('error')}")
                        
                except Exception as e:
                    errors.append(f"Error reindexing {note['path']}: {str(e)}")
            
            return {
                "status": "completed",
                "reindexed_count": reindexed_count,
                "total_notes": len(notes),
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Failed to reindex notes: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

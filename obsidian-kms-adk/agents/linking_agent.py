"""
Linking Agent for Obsidian KMS
Handles bi-directional semantic linking and graph maintenance
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from google.adk import Agent, Tool, Memory
from google.adk.agents import AgentConfig

from tools.entity_extraction_tool import EntityExtractionTool
from tools.vector_search_tool import VectorSearchTool
from tools.graph_update_tool import GraphUpdateTool
from memory.adapters.neo4j import Neo4jAdapter

logger = logging.getLogger(__name__)


class LinkingAgent(Agent):
    """
    Linking Agent maintains bi-directional semantic links.
    
    Responsibilities:
    - Propose semantic links based on entity extraction and vector similarity
    - Update graph edges with confidence scores and rationale
    - Maintain hub/authority metrics for Graph View
    - Handle link approval workflow
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        
        # Initialize tools
        self.entity_extraction_tool = EntityExtractionTool()
        self.vector_search_tool = VectorSearchTool()
        self.graph_update_tool = GraphUpdateTool()
        
        # Initialize memory adapters
        self.graph_db = Neo4jAdapter()
        
        # Configuration
        self.link_confidence_threshold = config.get("link_confidence_threshold", 0.7)
        self.max_similar_notes = config.get("max_similar_notes", 10)
        self.semantic_weight = config.get("semantic_weight", 0.6)
        self.entity_weight = config.get("entity_weight", 0.4)
    
    async def process_links(self, ingestion_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process links for a newly ingested note
        
        Args:
            ingestion_result: Result from IngestionAgent
            
        Returns:
            Link processing result with proposed links and confidence scores
        """
        try:
            note_id = ingestion_result["note_id"]
            note_path = ingestion_result["path"]
            entities = ingestion_result["entities"]
            embeddings = ingestion_result["embeddings"]
            
            logger.info(f"Processing links for note {note_id}")
            
            # 1. Find similar notes using vector search
            similar_notes = await self._find_similar_notes(note_id, embeddings)
            
            # 2. Find entity-based connections
            entity_connections = await self._find_entity_connections(note_id, entities)
            
            # 3. Combine and score potential links
            potential_links = await self._combine_and_score_links(
                similar_notes, entity_connections, note_id
            )
            
            # 4. Filter by confidence threshold
            high_confidence_links = [
                link for link in potential_links 
                if link["confidence"] >= self.link_confidence_threshold
            ]
            
            # 5. Create pending links for human approval
            pending_links = await self._create_pending_links(note_id, high_confidence_links)
            
            result = {
                "note_id": note_id,
                "similar_notes": similar_notes,
                "entity_connections": entity_connections,
                "potential_links": potential_links,
                "high_confidence_links": high_confidence_links,
                "pending_links": pending_links,
                "processing_time": datetime.now().isoformat(),
                "status": "success"
            }
            
            logger.info(f"Found {len(high_confidence_links)} high-confidence links for note {note_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process links for note {ingestion_result.get('note_id')}: {str(e)}")
            return {
                "note_id": ingestion_result.get("note_id"),
                "error": str(e),
                "status": "error"
            }
    
    async def _find_similar_notes(self, note_id: str, embeddings: Dict[str, List[float]]) -> List[Dict[str, Any]]:
        """Find similar notes using vector similarity"""
        try:
            content_embedding = embeddings.get("content")
            if not content_embedding:
                return []
            
            # Search for similar notes
            similar_notes = await self.vector_search_tool.search(
                embedding=content_embedding,
                k=self.max_similar_notes,
                exclude_note_id=note_id
            )
            
            return similar_notes
            
        except Exception as e:
            logger.error(f"Failed to find similar notes: {str(e)}")
            return []
    
    async def _find_entity_connections(self, note_id: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find connections based on shared entities"""
        try:
            connections = []
            
            for entity in entities:
                entity_name = entity["name"]
                entity_type = entity["type"]
                
                # Find other notes that mention this entity
                related_notes = await self.graph_db.find_notes_by_entity(entity_name)
                
                for related_note in related_notes:
                    if related_note["note_id"] != note_id:
                        connections.append({
                            "target_note_id": related_note["note_id"],
                            "target_note_path": related_note["path"],
                            "shared_entity": entity_name,
                            "entity_type": entity_type,
                            "confidence": entity.get("confidence", 0.5)
                        })
            
            return connections
            
        except Exception as e:
            logger.error(f"Failed to find entity connections: {str(e)}")
            return []
    
    async def _combine_and_score_links(self, similar_notes: List[Dict[str, Any]], 
                                     entity_connections: List[Dict[str, Any]], 
                                     source_note_id: str) -> List[Dict[str, Any]]:
        """Combine vector and entity similarities and score potential links"""
        try:
            # Create a map of target notes with their scores
            link_scores = {}
            
            # Add vector similarity scores
            for note in similar_notes:
                target_id = note["note_id"]
                vector_score = note["similarity_score"]
                
                if target_id not in link_scores:
                    link_scores[target_id] = {
                        "target_note_id": target_id,
                        "target_note_path": note["path"],
                        "vector_score": vector_score,
                        "entity_score": 0.0,
                        "shared_entities": [],
                        "rationale": []
                    }
                
                link_scores[target_id]["vector_score"] = vector_score
                link_scores[target_id]["rationale"].append(f"Vector similarity: {vector_score:.3f}")
            
            # Add entity connection scores
            for connection in entity_connections:
                target_id = connection["target_note_id"]
                
                if target_id not in link_scores:
                    link_scores[target_id] = {
                        "target_note_id": target_id,
                        "target_note_path": connection["target_note_path"],
                        "vector_score": 0.0,
                        "entity_score": 0.0,
                        "shared_entities": [],
                        "rationale": []
                    }
                
                # Accumulate entity scores
                entity_score = connection["confidence"]
                link_scores[target_id]["entity_score"] += entity_score
                link_scores[target_id]["shared_entities"].append({
                    "name": connection["shared_entity"],
                    "type": connection["entity_type"],
                    "confidence": entity_score
                })
                link_scores[target_id]["rationale"].append(
                    f"Shared entity '{connection['shared_entity']}': {entity_score:.3f}"
                )
            
            # Calculate combined confidence scores
            potential_links = []
            for target_id, scores in link_scores.items():
                # Normalize entity score (average of shared entities)
                if scores["shared_entities"]:
                    scores["entity_score"] = scores["entity_score"] / len(scores["shared_entities"])
                
                # Calculate combined confidence
                combined_confidence = (
                    self.semantic_weight * scores["vector_score"] +
                    self.entity_weight * scores["entity_score"]
                )
                
                potential_links.append({
                    "source_note_id": source_note_id,
                    "target_note_id": target_id,
                    "target_note_path": scores["target_note_path"],
                    "confidence": combined_confidence,
                    "vector_score": scores["vector_score"],
                    "entity_score": scores["entity_score"],
                    "shared_entities": scores["shared_entities"],
                    "rationale": "; ".join(scores["rationale"])
                })
            
            # Sort by confidence score
            potential_links.sort(key=lambda x: x["confidence"], reverse=True)
            
            return potential_links
            
        except Exception as e:
            logger.error(f"Failed to combine and score links: {str(e)}")
            return []
    
    async def _create_pending_links(self, note_id: str, high_confidence_links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create pending links for human approval"""
        try:
            pending_links = []
            
            for link in high_confidence_links:
                pending_link = await self.graph_db.create_pending_link(
                    source_note_id=note_id,
                    target_note_id=link["target_note_id"],
                    confidence=link["confidence"],
                    rationale=link["rationale"],
                    link_type="semantic"
                )
                
                pending_links.append({
                    "pending_link_id": pending_link["id"],
                    "source_note_id": note_id,
                    "target_note_id": link["target_note_id"],
                    "target_note_path": link["target_note_path"],
                    "confidence": link["confidence"],
                    "rationale": link["rationale"],
                    "status": "pending"
                })
            
            return pending_links
            
        except Exception as e:
            logger.error(f"Failed to create pending links: {str(e)}")
            return []
    
    async def update_graph(self, linking_result: Dict[str, Any]) -> Dict[str, Any]:
        """Update graph with approved links"""
        try:
            note_id = linking_result["note_id"]
            high_confidence_links = linking_result["high_confidence_links"]
            
            # Update graph with high-confidence links
            updated_links = []
            for link in high_confidence_links:
                # Create bidirectional link
                await self.graph_update_tool.upsert_edges(
                    note_id=note_id,
                    edges=[{
                        "target_id": link["target_note_id"],
                        "relationship": "LINKS_TO",
                        "confidence": link["confidence"],
                        "rationale": link["rationale"],
                        "source": "AUTO"
                    }]
                )
                
                # Create reverse link
                await self.graph_update_tool.upsert_edges(
                    note_id=link["target_note_id"],
                    edges=[{
                        "target_id": note_id,
                        "relationship": "LINKS_TO",
                        "confidence": link["confidence"],
                        "rationale": f"Reverse of: {link['rationale']}",
                        "source": "AUTO"
                    }]
                )
                
                updated_links.append(link["target_note_id"])
            
            # Update hub/authority metrics
            await self._update_hub_authority_metrics(note_id)
            
            result = {
                "note_id": note_id,
                "updated_links": updated_links,
                "link_count": len(updated_links),
                "processing_time": datetime.now().isoformat(),
                "status": "success"
            }
            
            logger.info(f"Updated graph with {len(updated_links)} links for note {note_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to update graph: {str(e)}")
            return {
                "note_id": linking_result.get("note_id"),
                "error": str(e),
                "status": "error"
            }
    
    async def _update_hub_authority_metrics(self, note_id: str):
        """Update hub and authority metrics for graph view"""
        try:
            # Calculate hub score (outgoing links)
            outgoing_links = await self.graph_db.get_outgoing_links(note_id)
            hub_score = len(outgoing_links)
            
            # Calculate authority score (incoming links)
            incoming_links = await self.graph_db.get_incoming_links(note_id)
            authority_score = len(incoming_links)
            
            # Update note with metrics
            await self.graph_db.update_note_metrics(
                note_id=note_id,
                hub_score=hub_score,
                authority_score=authority_score
            )
            
        except Exception as e:
            logger.error(f"Failed to update hub/authority metrics: {str(e)}")
    
    async def approve_link(self, pending_link_id: str, approved: bool) -> Dict[str, Any]:
        """Approve or reject a pending link"""
        try:
            if approved:
                # Get pending link details
                pending_link = await self.graph_db.get_pending_link(pending_link_id)
                
                # Create the link
                await self.graph_update_tool.upsert_edges(
                    note_id=pending_link["source_note_id"],
                    edges=[{
                        "target_id": pending_link["target_note_id"],
                        "relationship": "LINKS_TO",
                        "confidence": pending_link["confidence"],
                        "rationale": pending_link["rationale"],
                        "source": "MANUAL"
                    }]
                )
                
                # Mark as approved
                await self.graph_db.update_pending_link_status(pending_link_id, "approved")
                
                return {
                    "pending_link_id": pending_link_id,
                    "status": "approved",
                    "message": "Link created successfully"
                }
            else:
                # Mark as rejected
                await self.graph_db.update_pending_link_status(pending_link_id, "rejected")
                
                return {
                    "pending_link_id": pending_link_id,
                    "status": "rejected",
                    "message": "Link rejected"
                }
                
        except Exception as e:
            logger.error(f"Failed to approve/reject link {pending_link_id}: {str(e)}")
            return {
                "pending_link_id": pending_link_id,
                "status": "error",
                "error": str(e)
            }
    
    async def refresh_links(self) -> Dict[str, Any]:
        """Refresh all links (maintenance task)"""
        try:
            # Get all notes
            notes = await self.graph_db.get_all_notes()
            
            refreshed_count = 0
            errors = []
            
            for note in notes:
                try:
                    # Re-process links for this note
                    result = await self.process_links({
                        "note_id": note["note_id"],
                        "path": note["path"],
                        "entities": [],  # Will be re-extracted
                        "embeddings": {}  # Will be re-generated
                    })
                    
                    if result["status"] == "success":
                        refreshed_count += 1
                    else:
                        errors.append(f"Failed to refresh links for {note['path']}: {result.get('error')}")
                        
                except Exception as e:
                    errors.append(f"Error refreshing links for {note['path']}: {str(e)}")
            
            return {
                "status": "completed",
                "refreshed_count": refreshed_count,
                "total_notes": len(notes),
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Failed to refresh links: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

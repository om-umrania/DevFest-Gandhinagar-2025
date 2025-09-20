"""
Root Orchestrator Agent for KMS-Google-ADK
Coordinates all other agents and manages the overall knowledge management workflow.
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
import asyncio
import logging
from dataclasses import dataclass
from enum import Enum

from agents.ingestion_agent import IngestionAgent
from tools.vector_search_tool import VectorSearchTool
from tools.note_creation_tool import NoteCreationTool
from tools.simple_entity_extraction_tool import SimpleEntityExtractionTool as EntityExtractionTool
from tools.graph_update_tool import GraphUpdateTool


class AgentStatus(Enum):
    """Status of an agent."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentTask:
    """Represents a task for an agent."""
    task_id: str
    agent_type: str
    task_data: Dict[str, Any]
    status: AgentStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class RootOrchestratorAgent:
    """
    Root orchestrator that coordinates all agents in the KMS system.
    
    This agent manages:
    - Document ingestion workflow
    - Search and retrieval operations
    - Knowledge graph updates
    - Entity extraction and linking
    - Note creation and updates
    """
    
    def __init__(
        self,
        bucket_name: str,
        db_path: str = "kms_index.db",
        gcs_client=None
    ):
        """
        Initialize the root orchestrator.
        
        Args:
            bucket_name: Google Cloud Storage bucket name
            db_path: Path to SQLite database
            gcs_client: Optional GCS client instance
        """
        self.bucket_name = bucket_name
        self.db_path = db_path
        self.gcs_client = gcs_client
        
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize agents
        self.ingestion_agent = IngestionAgent(bucket_name, db_path, gcs_client)
        
        # Initialize tools
        self.vector_search_tool = VectorSearchTool(db_path)
        self.note_creation_tool = NoteCreationTool(bucket_name, gcs_client)
        self.entity_extraction_tool = EntityExtractionTool(db_path)
        self.graph_update_tool = GraphUpdateTool(db_path)
        
        # Task management
        self.active_tasks: Dict[str, AgentTask] = {}
        self.task_history: List[AgentTask] = []
        
        self.logger.info("Root Orchestrator Agent initialized")
    
    async def process_document_ingestion(
        self,
        document_path: str,
        force_update: bool = False
    ) -> Dict[str, Any]:
        """
        Process a single document through the complete ingestion pipeline.
        
        Args:
            document_path: Path to the document in GCS
            force_update: Whether to force update even if unchanged
            
        Returns:
            Dict with processing results and status
        """
        task_id = f"ingest_{document_path}_{datetime.now().isoformat()}"
        
        try:
            self.logger.info(f"Starting document ingestion for {document_path}")
            
            # Create task
            task = AgentTask(
                task_id=task_id,
                agent_type="ingestion",
                task_data={"document_path": document_path, "force_update": force_update},
                status=AgentStatus.RUNNING,
                created_at=datetime.now(timezone.utc)
            )
            self.active_tasks[task_id] = task
            
            # Step 1: Ingest document
            ingestion_result = await self.ingestion_agent.process_document(
                document_path, force_update
            )
            
            if not ingestion_result.get("success", False):
                raise Exception(f"Ingestion failed: {ingestion_result.get('error')}")
            
            # Step 2: Extract entities
            entity_result = await self.entity_extraction_tool.extract_entities(
                document_path, ingestion_result.get("content", "")
            )
            
            # Step 3: Update knowledge graph
            graph_result = await self.graph_update_tool.update_graph(
                document_path, entity_result.get("entities", [])
            )
            
            # Update task status
            task.status = AgentStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            task.result = {
                "ingestion": ingestion_result,
                "entities": entity_result,
                "graph": graph_result
            }
            
            self.task_history.append(task)
            del self.active_tasks[task_id]
            
            self.logger.info(f"Document ingestion completed for {document_path}")
            
            return {
                "success": True,
                "task_id": task_id,
                "results": task.result
            }
            
        except Exception as e:
            self.logger.error(f"Document ingestion failed for {document_path}: {str(e)}")
            
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                task.status = AgentStatus.ERROR
                task.completed_at = datetime.now(timezone.utc)
                task.error = str(e)
                self.task_history.append(task)
                del self.active_tasks[task_id]
            
            return {
                "success": False,
                "task_id": task_id,
                "error": str(e)
            }
    
    async def process_batch_ingestion(
        self,
        document_paths: List[str],
        force_update: bool = False,
        max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """
        Process multiple documents through the ingestion pipeline.
        
        Args:
            document_paths: List of document paths in GCS
            force_update: Whether to force update even if unchanged
            max_concurrent: Maximum number of concurrent processing tasks
            
        Returns:
            Dict with batch processing results
        """
        self.logger.info(f"Starting batch ingestion for {len(document_paths)} documents")
        
        # Create semaphore to limit concurrent tasks
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(path):
            async with semaphore:
                return await self.process_document_ingestion(path, force_update)
        
        # Process all documents concurrently
        tasks = [process_with_semaphore(path) for path in document_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful = 0
        failed = 0
        errors = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed += 1
                errors.append(f"Document {document_paths[i]}: {str(result)}")
            elif result.get("success", False):
                successful += 1
            else:
                failed += 1
                errors.append(f"Document {document_paths[i]}: {result.get('error', 'Unknown error')}")
        
        self.logger.info(f"Batch ingestion completed: {successful} successful, {failed} failed")
        
        return {
            "success": failed == 0,
            "total": len(document_paths),
            "successful": successful,
            "failed": failed,
            "errors": errors,
            "results": results
        }
    
    async def search_knowledge(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search the knowledge base using vector similarity.
        
        Args:
            query: Search query
            filters: Optional filters (tags, date range, etc.)
            limit: Maximum number of results
            
        Returns:
            Dict with search results
        """
        try:
            self.logger.info(f"Searching knowledge base for: {query}")
            
            # Use vector search tool
            results = await self.vector_search_tool.search(
                query=query,
                filters=filters or {},
                limit=limit
            )
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "total": len(results)
            }
            
        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_note(
        self,
        path: str,
        frontmatter_data: Dict[str, Any],
        content: str,
        force_update: bool = False
    ) -> Dict[str, Any]:
        """
        Create or update a note in the knowledge base.
        
        Args:
            path: GCS path for the note
            frontmatter_data: Note metadata
            content: Note content
            force_update: Whether to force update
            
        Returns:
            Dict with creation results
        """
        try:
            self.logger.info(f"Creating/updating note: {path}")
            
            # Create note using tool
            result = await self.note_creation_tool.create_or_update(
                path=path,
                frontmatter_data=frontmatter_data,
                body=content,
                force_update=force_update
            )
            
            # If successful, process through ingestion pipeline
            if result.get("success", False):
                await self.process_document_ingestion(path, force_update)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Note creation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """
        Get the current status of all agents and active tasks.
        
        Returns:
            Dict with agent status information
        """
        return {
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.task_history),
            "agents": {
                "ingestion": "ready",
                "vector_search": "ready",
                "note_creation": "ready",
                "entity_extraction": "ready",
                "graph_update": "ready"
            },
            "active_task_details": [
                {
                    "task_id": task.task_id,
                    "agent_type": task.agent_type,
                    "status": task.status.value,
                    "created_at": task.created_at.isoformat()
                }
                for task in self.active_tasks.values()
            ]
        }
    
    async def get_task_history(
        self,
        limit: int = 50,
        agent_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get task history with optional filtering.
        
        Args:
            limit: Maximum number of tasks to return
            agent_type: Optional filter by agent type
            
        Returns:
            List of task details
        """
        tasks = self.task_history[-limit:] if limit > 0 else self.task_history
        
        if agent_type:
            tasks = [t for t in tasks if t.agent_type == agent_type]
        
        return [
            {
                "task_id": task.task_id,
                "agent_type": task.agent_type,
                "status": task.status.value,
                "created_at": task.created_at.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "error": task.error
            }
            for task in tasks
        ]
    
    async def cleanup_completed_tasks(self, older_than_hours: int = 24):
        """
        Clean up completed tasks older than specified hours.
        
        Args:
            older_than_hours: Remove tasks older than this many hours
        """
        cutoff_time = datetime.now(timezone.utc).timestamp() - (older_than_hours * 3600)
        
        # Keep only recent tasks
        self.task_history = [
            task for task in self.task_history
            if task.completed_at and task.completed_at.timestamp() > cutoff_time
        ]
        
        self.logger.info(f"Cleaned up tasks older than {older_than_hours} hours")

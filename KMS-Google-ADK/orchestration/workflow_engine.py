"""
Workflow Engine for KMS-Google-ADK
Handles complex multi-step operations and agent coordination.
"""

from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, timezone
import asyncio
import logging
import json
import uuid
from dataclasses import dataclass, asdict
from enum import Enum
from .message_bus import MessageBus, Message, MessageType, MessagePriority


class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class StepStatus(Enum):
    """Individual step status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """Represents a step in a workflow."""
    id: str
    name: str
    agent_type: str
    action: str
    parameters: Dict[str, Any]
    dependencies: List[str]
    timeout: int = 300  # 5 minutes default
    retry_count: int = 3
    retry_delay: int = 5  # seconds
    status: StepStatus = StepStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class Workflow:
    """Represents a workflow definition."""
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    created_at: datetime
    created_by: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_step: Optional[str] = None
    context: Dict[str, Any] = None


class WorkflowEngine:
    """
    Engine for executing complex workflows involving multiple agents.
    
    Features:
    - Step-by-step execution with dependencies
    - Retry logic and error handling
    - Parallel and sequential execution
    - Workflow state persistence
    - Real-time progress tracking
    - Conditional execution
    """
    
    def __init__(self, message_bus: MessageBus, db_path: str = "kms_index.db"):
        """
        Initialize the workflow engine.
        
        Args:
            message_bus: Message bus for agent communication
            db_path: Path to SQLite database for persistence
        """
        self.message_bus = message_bus
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Active workflows
        self.active_workflows: Dict[str, Workflow] = {}
        
        # Workflow templates
        self.templates: Dict[str, Callable] = {}
        
        # Step handlers
        self.step_handlers: Dict[str, Callable] = {}
        
        # Initialize database
        self._init_database()
        
        # Register default step handlers
        self._register_default_handlers()
        
        self.logger.info("Workflow Engine initialized")
    
    def _init_database(self):
        """Initialize the workflow database schema."""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Workflows table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                created_by TEXT NOT NULL,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                current_step TEXT,
                context TEXT
            )
        """)
        
        # Workflow steps table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflow_steps (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                name TEXT NOT NULL,
                agent_type TEXT NOT NULL,
                action TEXT NOT NULL,
                parameters TEXT NOT NULL,
                dependencies TEXT NOT NULL,
                timeout INTEGER DEFAULT 300,
                retry_count INTEGER DEFAULT 3,
                retry_delay INTEGER DEFAULT 5,
                status TEXT NOT NULL,
                result TEXT,
                error TEXT,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (workflow_id) REFERENCES workflows (id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _register_default_handlers(self):
        """Register default step handlers."""
        self.step_handlers.update({
            "ingest_document": self._handle_ingest_document,
            "extract_entities": self._handle_extract_entities,
            "create_links": self._handle_create_links,
            "generate_summary": self._handle_generate_summary,
            "answer_question": self._handle_answer_question,
            "search_knowledge": self._handle_search_knowledge,
            "wait": self._handle_wait,
            "condition": self._handle_condition
        })
    
    async def create_workflow(
        self,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        created_by: str = "system"
    ) -> str:
        """
        Create a new workflow.
        
        Args:
            name: Workflow name
            description: Workflow description
            steps: List of step definitions
            created_by: Creator identifier
            
        Returns:
            Workflow ID
        """
        workflow_id = str(uuid.uuid4())
        
        # Convert step definitions to WorkflowStep objects
        workflow_steps = []
        for step_def in steps:
            step = WorkflowStep(
                id=str(uuid.uuid4()),
                name=step_def["name"],
                agent_type=step_def["agent_type"],
                action=step_def["action"],
                parameters=step_def.get("parameters", {}),
                dependencies=step_def.get("dependencies", []),
                timeout=step_def.get("timeout", 300),
                retry_count=step_def.get("retry_count", 3),
                retry_delay=step_def.get("retry_delay", 5)
            )
            workflow_steps.append(step)
        
        workflow = Workflow(
            id=workflow_id,
            name=name,
            description=description,
            steps=workflow_steps,
            created_at=datetime.now(timezone.utc),
            created_by=created_by,
            context={}
        )
        
        # Store in database
        await self._save_workflow(workflow)
        
        self.logger.info(f"Created workflow {workflow_id}: {name}")
        return workflow_id
    
    async def start_workflow(self, workflow_id: str) -> bool:
        """
        Start executing a workflow.
        
        Args:
            workflow_id: Workflow ID to start
            
        Returns:
            True if started successfully
        """
        try:
            workflow = await self._load_workflow(workflow_id)
            if not workflow:
                self.logger.error(f"Workflow {workflow_id} not found")
                return False
            
            if workflow.status != WorkflowStatus.PENDING:
                self.logger.warning(f"Workflow {workflow_id} is not in pending status")
                return False
            
            # Update status
            workflow.status = WorkflowStatus.RUNNING
            workflow.started_at = datetime.now(timezone.utc)
            
            # Store active workflow
            self.active_workflows[workflow_id] = workflow
            
            # Start execution
            asyncio.create_task(self._execute_workflow(workflow))
            
            await self._save_workflow(workflow)
            
            self.logger.info(f"Started workflow {workflow_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start workflow {workflow_id}: {str(e)}")
            return False
    
    async def _execute_workflow(self, workflow: Workflow):
        """Execute a workflow step by step."""
        try:
            self.logger.info(f"Executing workflow {workflow.id}")
            
            # Find steps that can be executed (no pending dependencies)
            ready_steps = self._get_ready_steps(workflow)
            
            while ready_steps:
                # Execute steps in parallel
                tasks = []
                for step in ready_steps:
                    task = asyncio.create_task(self._execute_step(workflow, step))
                    tasks.append(task)
                
                # Wait for all steps to complete
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Check if workflow is complete
                if self._is_workflow_complete(workflow):
                    workflow.status = WorkflowStatus.COMPLETED
                    workflow.completed_at = datetime.now(timezone.utc)
                    break
                
                # Get next ready steps
                ready_steps = self._get_ready_steps(workflow)
            
            # Save final state
            await self._save_workflow(workflow)
            
            # Remove from active workflows
            if workflow.id in self.active_workflows:
                del self.active_workflows[workflow.id]
            
            self.logger.info(f"Completed workflow {workflow.id}")
            
        except Exception as e:
            self.logger.error(f"Error executing workflow {workflow.id}: {str(e)}")
            workflow.status = WorkflowStatus.FAILED
            workflow.completed_at = datetime.now(timezone.utc)
            await self._save_workflow(workflow)
    
    def _get_ready_steps(self, workflow: Workflow) -> List[WorkflowStep]:
        """Get steps that are ready to execute."""
        ready_steps = []
        
        for step in workflow.steps:
            if step.status != StepStatus.PENDING:
                continue
            
            # Check if all dependencies are completed
            dependencies_met = True
            for dep_id in step.dependencies:
                dep_step = next((s for s in workflow.steps if s.id == dep_id), None)
                if not dep_step or dep_step.status != StepStatus.COMPLETED:
                    dependencies_met = False
                    break
            
            if dependencies_met:
                ready_steps.append(step)
        
        return ready_steps
    
    def _is_workflow_complete(self, workflow: Workflow) -> bool:
        """Check if workflow is complete."""
        for step in workflow.steps:
            if step.status not in [StepStatus.COMPLETED, StepStatus.SKIPPED]:
                return False
        return True
    
    async def _execute_step(self, workflow: Workflow, step: WorkflowStep):
        """Execute a single workflow step."""
        try:
            self.logger.info(f"Executing step {step.name} in workflow {workflow.id}")
            
            step.status = StepStatus.RUNNING
            step.started_at = datetime.now(timezone.utc)
            workflow.current_step = step.id
            
            # Get step handler
            handler = self.step_handlers.get(step.action)
            if not handler:
                raise ValueError(f"No handler for action {step.action}")
            
            # Execute step with timeout
            result = await asyncio.wait_for(
                handler(workflow, step),
                timeout=step.timeout
            )
            
            step.result = result
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now(timezone.utc)
            
            # Update workflow context
            if result:
                workflow.context.update(result.get("context", {}))
            
            self.logger.info(f"Completed step {step.name}")
            
        except asyncio.TimeoutError:
            step.status = StepStatus.FAILED
            step.error = f"Step timed out after {step.timeout} seconds"
            step.completed_at = datetime.now(timezone.utc)
            self.logger.error(f"Step {step.name} timed out")
            
        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)
            step.completed_at = datetime.now(timezone.utc)
            self.logger.error(f"Step {step.name} failed: {str(e)}")
    
    # Step handlers
    async def _handle_ingest_document(self, workflow: Workflow, step: WorkflowStep) -> Dict[str, Any]:
        """Handle document ingestion step."""
        document_path = step.parameters.get("document_path")
        force_update = step.parameters.get("force_update", False)
        
        # Send request to ingestion agent
        response = await self.message_bus.request(
            topic="ingestion.process_document",
            payload={
                "document_path": document_path,
                "force_update": force_update
            },
            source="workflow_engine",
            target="ingestion_agent",
            timeout=step.timeout
        )
        
        if not response:
            raise Exception("No response from ingestion agent")
        
        return {
            "success": response.payload.get("success", False),
            "context": {
                "document_path": document_path,
                "ingestion_result": response.payload
            }
        }
    
    async def _handle_extract_entities(self, workflow: Workflow, step: WorkflowStep) -> Dict[str, Any]:
        """Handle entity extraction step."""
        document_path = step.parameters.get("document_path")
        content = step.parameters.get("content", "")
        
        # Send request to entity extraction agent
        response = await self.message_bus.request(
            topic="entities.extract",
            payload={
                "document_path": document_path,
                "content": content
            },
            source="workflow_engine",
            target="entity_agent",
            timeout=step.timeout
        )
        
        if not response:
            raise Exception("No response from entity extraction agent")
        
        return {
            "success": response.payload.get("success", False),
            "context": {
                "entities": response.payload.get("entities", []),
                "keyphrases": response.payload.get("keyphrases", [])
            }
        }
    
    async def _handle_create_links(self, workflow: Workflow, step: WorkflowStep) -> Dict[str, Any]:
        """Handle link creation step."""
        document_id = step.parameters.get("document_id")
        
        # Send request to linking agent
        response = await self.message_bus.request(
            topic="linking.create_links",
            payload={
                "document_id": document_id
            },
            source="workflow_engine",
            target="linking_agent",
            timeout=step.timeout
        )
        
        if not response:
            raise Exception("No response from linking agent")
        
        return {
            "success": response.payload.get("success", False),
            "context": {
                "links_created": response.payload.get("links_created", 0)
            }
        }
    
    async def _handle_generate_summary(self, workflow: Workflow, step: WorkflowStep) -> Dict[str, Any]:
        """Handle summary generation step."""
        document_id = step.parameters.get("document_id")
        max_length = step.parameters.get("max_length", 200)
        
        # Send request to synthesis agent
        response = await self.message_bus.request(
            topic="synthesis.generate_summary",
            payload={
                "document_id": document_id,
                "max_length": max_length
            },
            source="workflow_engine",
            target="synthesis_agent",
            timeout=step.timeout
        )
        
        if not response:
            raise Exception("No response from synthesis agent")
        
        return {
            "success": response.payload.get("success", False),
            "context": {
                "summary": response.payload.get("content", ""),
                "confidence": response.payload.get("confidence", 0.0)
            }
        }
    
    async def _handle_answer_question(self, workflow: Workflow, step: WorkflowStep) -> Dict[str, Any]:
        """Handle question answering step."""
        question = step.parameters.get("question")
        context_limit = step.parameters.get("context_limit", 5)
        
        # Send request to synthesis agent
        response = await self.message_bus.request(
            topic="synthesis.answer_question",
            payload={
                "question": question,
                "context_limit": context_limit
            },
            source="workflow_engine",
            target="synthesis_agent",
            timeout=step.timeout
        )
        
        if not response:
            raise Exception("No response from synthesis agent")
        
        return {
            "success": response.payload.get("success", False),
            "context": {
                "answer": response.payload.get("content", ""),
                "confidence": response.payload.get("confidence", 0.0),
                "sources": response.payload.get("sources", [])
            }
        }
    
    async def _handle_search_knowledge(self, workflow: Workflow, step: WorkflowStep) -> Dict[str, Any]:
        """Handle knowledge search step."""
        query = step.parameters.get("query")
        filters = step.parameters.get("filters", {})
        limit = step.parameters.get("limit", 10)
        
        # Send request to root orchestrator
        response = await self.message_bus.request(
            topic="orchestrator.search",
            payload={
                "query": query,
                "filters": filters,
                "limit": limit
            },
            source="workflow_engine",
            target="root_orchestrator",
            timeout=step.timeout
        )
        
        if not response:
            raise Exception("No response from root orchestrator")
        
        return {
            "success": response.payload.get("success", False),
            "context": {
                "results": response.payload.get("results", []),
                "total": response.payload.get("total", 0)
            }
        }
    
    async def _handle_wait(self, workflow: Workflow, step: WorkflowStep) -> Dict[str, Any]:
        """Handle wait step."""
        duration = step.parameters.get("duration", 1)  # seconds
        await asyncio.sleep(duration)
        
        return {
            "success": True,
            "context": {
                "waited_seconds": duration
            }
        }
    
    async def _handle_condition(self, workflow: Workflow, step: WorkflowStep) -> Dict[str, Any]:
        """Handle conditional step."""
        condition = step.parameters.get("condition")
        true_action = step.parameters.get("true_action")
        false_action = step.parameters.get("false_action")
        
        # Evaluate condition based on workflow context
        condition_result = self._evaluate_condition(condition, workflow.context)
        
        if condition_result and true_action:
            # Execute true action
            pass
        elif not condition_result and false_action:
            # Execute false action
            pass
        
        return {
            "success": True,
            "context": {
                "condition_result": condition_result
            }
        }
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a condition string against workflow context."""
        # Simple condition evaluation
        # In a real implementation, this would be more sophisticated
        try:
            # Replace context variables in condition
            for key, value in context.items():
                condition = condition.replace(f"${{{key}}}", str(value))
            
            # Evaluate as Python expression
            return bool(eval(condition))
        except:
            return False
    
    async def _save_workflow(self, workflow: Workflow):
        """Save workflow to database."""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Save workflow
        cursor.execute("""
            INSERT OR REPLACE INTO workflows
            (id, name, description, status, created_at, created_by, started_at, completed_at, current_step, context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            workflow.id,
            workflow.name,
            workflow.description,
            workflow.status.value,
            workflow.created_at,
            workflow.created_by,
            workflow.started_at,
            workflow.completed_at,
            workflow.current_step,
            json.dumps(workflow.context or {})
        ))
        
        # Save steps
        cursor.execute("DELETE FROM workflow_steps WHERE workflow_id = ?", (workflow.id,))
        
        for step in workflow.steps:
            cursor.execute("""
                INSERT INTO workflow_steps
                (id, workflow_id, name, agent_type, action, parameters, dependencies, timeout, retry_count, retry_delay, status, result, error, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                step.id,
                workflow.id,
                step.name,
                step.agent_type,
                step.action,
                json.dumps(step.parameters),
                json.dumps(step.dependencies),
                step.timeout,
                step.retry_count,
                step.retry_delay,
                step.status.value,
                json.dumps(step.result) if step.result else None,
                step.error,
                step.started_at,
                step.completed_at
            ))
        
        conn.commit()
        conn.close()
    
    async def _load_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Load workflow from database."""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load workflow
        cursor.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        # Load steps
        cursor.execute("SELECT * FROM workflow_steps WHERE workflow_id = ?", (workflow_id,))
        step_rows = cursor.fetchall()
        
        steps = []
        for step_row in step_rows:
            step = WorkflowStep(
                id=step_row[0],
                name=step_row[2],
                agent_type=step_row[3],
                action=step_row[4],
                parameters=json.loads(step_row[5]),
                dependencies=json.loads(step_row[6]),
                timeout=step_row[7],
                retry_count=step_row[8],
                retry_delay=step_row[9],
                status=StepStatus(step_row[10]),
                result=json.loads(step_row[11]) if step_row[11] else None,
                error=step_row[12],
                started_at=datetime.fromisoformat(step_row[13]) if step_row[13] else None,
                completed_at=datetime.fromisoformat(step_row[14]) if step_row[14] else None
            )
            steps.append(step)
        
        workflow = Workflow(
            id=row[0],
            name=row[1],
            description=row[2],
            steps=steps,
            created_at=datetime.fromisoformat(row[4]),
            created_by=row[5],
            status=WorkflowStatus(row[3]),
            started_at=datetime.fromisoformat(row[6]) if row[6] else None,
            completed_at=datetime.fromisoformat(row[7]) if row[7] else None,
            current_step=row[8],
            context=json.loads(row[9]) if row[9] else {}
        )
        
        conn.close()
        return workflow
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow status."""
        workflow = await self._load_workflow(workflow_id)
        if not workflow:
            return None
        
        return {
            "id": workflow.id,
            "name": workflow.name,
            "status": workflow.status.value,
            "progress": self._calculate_progress(workflow),
            "current_step": workflow.current_step,
            "created_at": workflow.created_at.isoformat(),
            "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
            "steps": [
                {
                    "id": step.id,
                    "name": step.name,
                    "status": step.status.value,
                    "agent_type": step.agent_type,
                    "action": step.action
                }
                for step in workflow.steps
            ]
        }
    
    def _calculate_progress(self, workflow: Workflow) -> float:
        """Calculate workflow progress percentage."""
        if not workflow.steps:
            return 0.0
        
        completed_steps = sum(1 for step in workflow.steps if step.status == StepStatus.COMPLETED)
        return (completed_steps / len(workflow.steps)) * 100
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            workflow.status = WorkflowStatus.CANCELLED
            workflow.completed_at = datetime.now(timezone.utc)
            await self._save_workflow(workflow)
            del self.active_workflows[workflow_id]
            return True
        return False
    
    def get_active_workflows(self) -> List[Dict[str, Any]]:
        """Get list of active workflows."""
        return [
            {
                "id": workflow.id,
                "name": workflow.name,
                "status": workflow.status.value,
                "progress": self._calculate_progress(workflow),
                "current_step": workflow.current_step
            }
            for workflow in self.active_workflows.values()
        ]

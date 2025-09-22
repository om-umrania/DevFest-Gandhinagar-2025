"""
Root Orchestrator Agent for Obsidian KMS
Coordinates specialized agents and manages task routing
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum

from google.adk import Agent, Tool, Memory
from google.adk.agents import AgentConfig
from google.adk.tools import ToolConfig

from .ingestion_agent import IngestionAgent
from .linking_agent import LinkingAgent
from .prediction_agent import PredictionAgent
from .synthesis_agent import SynthesisAgent

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of tasks the orchestrator can handle"""
    ADD_NOTE = "add_note"
    UPDATE_NOTE = "update_note"
    DELETE_NOTE = "delete_note"
    QUERY = "query"
    SYNTHESIS = "synthesis"
    MAINTENANCE = "maintenance"
    LINK_SUGGESTION = "link_suggestion"


class OrchestrationPattern(Enum):
    """Patterns for orchestrating agent workflows"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    LOOP = "loop"
    HYBRID = "hybrid"


class RootOrchestrator(Agent):
    """
    Root Orchestrator coordinates specialized agents and manages task routing.
    
    Responsibilities:
    - Plan and route tasks to appropriate sub-agents
    - Select orchestration patterns (Sequential/Parallel/Loop)
    - Maintain session context and tool access
    - Consolidate results from multiple agents
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        
        # Initialize specialized agents
        self.ingestion_agent = IngestionAgent(config)
        self.linking_agent = LinkingAgent(config)
        self.prediction_agent = PredictionAgent(config)
        self.synthesis_agent = SynthesisAgent(config)
        
        # Session management
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.task_queue: List[Dict[str, Any]] = []
        
        # Performance tracking
        self.metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "avg_response_time": 0.0,
            "agent_utilization": {}
        }
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for processing tasks
        
        Args:
            task: Task specification with type, payload, and metadata
            
        Returns:
            Task result with status, data, and metadata
        """
        start_time = datetime.now()
        task_id = task.get("id", f"task_{datetime.now().timestamp()}")
        
        try:
            logger.info(f"Processing task {task_id}: {task.get('type')}")
            
            # Determine orchestration pattern
            pattern = self._determine_pattern(task)
            
            # Route to appropriate agents
            result = await self._route_task(task, pattern)
            
            # Update metrics
            self._update_metrics(task_id, start_time, success=True)
            
            return {
                "task_id": task_id,
                "status": "success",
                "result": result,
                "pattern_used": pattern.value,
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {str(e)}")
            self._update_metrics(task_id, start_time, success=False)
            
            return {
                "task_id": task_id,
                "status": "error",
                "error": str(e),
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
    
    def _determine_pattern(self, task: Dict[str, Any]) -> OrchestrationPattern:
        """Determine the best orchestration pattern for the task"""
        task_type = task.get("type")
        
        if task_type in [TaskType.ADD_NOTE, TaskType.UPDATE_NOTE]:
            # Sequential: ingest -> link -> update graph
            return OrchestrationPattern.SEQUENTIAL
        elif task_type == TaskType.QUERY:
            # Hybrid: parallel search + graph walk, then synthesis
            return OrchestrationPattern.HYBRID
        elif task_type == TaskType.SYNTHESIS:
            # Loop: iterative refinement with human feedback
            return OrchestrationPattern.LOOP
        elif task_type == TaskType.MAINTENANCE:
            # Parallel: multiple maintenance tasks can run concurrently
            return OrchestrationPattern.PARALLEL
        else:
            return OrchestrationPattern.SEQUENTIAL
    
    async def _route_task(self, task: Dict[str, Any], pattern: OrchestrationPattern) -> Dict[str, Any]:
        """Route task to appropriate agents based on pattern"""
        task_type = task.get("type")
        payload = task.get("payload", {})
        
        if pattern == OrchestrationPattern.SEQUENTIAL:
            return await self._sequential_execution(task_type, payload)
        elif pattern == OrchestrationPattern.PARALLEL:
            return await self._parallel_execution(task_type, payload)
        elif pattern == OrchestrationPattern.LOOP:
            return await self._loop_execution(task_type, payload)
        elif pattern == OrchestrationPattern.HYBRID:
            return await self._hybrid_execution(task_type, payload)
        else:
            raise ValueError(f"Unknown orchestration pattern: {pattern}")
    
    async def _sequential_execution(self, task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tasks sequentially"""
        results = []
        
        if task_type in [TaskType.ADD_NOTE, TaskType.UPDATE_NOTE]:
            # 1. Ingestion
            ingestion_result = await self.ingestion_agent.process_note(payload)
            results.append(("ingestion", ingestion_result))
            
            # 2. Linking
            linking_result = await self.linking_agent.process_links(ingestion_result)
            results.append(("linking", linking_result))
            
            # 3. Update graph
            graph_result = await self.linking_agent.update_graph(linking_result)
            results.append(("graph_update", graph_result))
            
        return {"execution_type": "sequential", "results": results}
    
    async def _parallel_execution(self, task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tasks in parallel"""
        tasks = []
        
        if task_type == TaskType.MAINTENANCE:
            # Run multiple maintenance tasks concurrently
            tasks = [
                self.ingestion_agent.reindex_notes(),
                self.linking_agent.refresh_links(),
                self.prediction_agent.update_models(),
            ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            "execution_type": "parallel",
            "results": [
                {"task": f"maintenance_{i}", "result": result}
                for i, result in enumerate(results)
            ]
        }
    
    async def _loop_execution(self, task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tasks with iterative refinement"""
        max_iterations = payload.get("max_iterations", 3)
        confidence_threshold = payload.get("confidence_threshold", 0.8)
        
        iteration = 0
        results = []
        
        while iteration < max_iterations:
            # Get prediction and synthesis
            prediction = await self.prediction_agent.plan_query(payload)
            synthesis = await self.synthesis_agent.compose_answer(payload, prediction)
            
            results.append({
                "iteration": iteration,
                "prediction": prediction,
                "synthesis": synthesis
            })
            
            # Check if we need another iteration
            if synthesis.get("confidence", 0) >= confidence_threshold:
                break
                
            iteration += 1
        
        return {
            "execution_type": "loop",
            "iterations": iteration + 1,
            "results": results
        }
    
    async def _hybrid_execution(self, task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tasks with hybrid approach (parallel + sequential)"""
        if task_type == TaskType.QUERY:
            # Parallel: vector search + graph walk
            vector_task = self.prediction_agent.vector_search(payload)
            graph_task = self.prediction_agent.graph_walk(payload)
            
            vector_result, graph_result = await asyncio.gather(vector_task, graph_task)
            
            # Sequential: synthesis
            synthesis_result = await self.synthesis_agent.compose_answer(
                payload, 
                {"vector": vector_result, "graph": graph_result}
            )
            
            return {
                "execution_type": "hybrid",
                "vector_search": vector_result,
                "graph_walk": graph_result,
                "synthesis": synthesis_result
            }
        
        return {"execution_type": "hybrid", "results": []}
    
    def _update_metrics(self, task_id: str, start_time: datetime, success: bool):
        """Update performance metrics"""
        processing_time = (datetime.now() - start_time).total_seconds()
        
        if success:
            self.metrics["tasks_completed"] += 1
        else:
            self.metrics["tasks_failed"] += 1
        
        # Update average response time
        total_tasks = self.metrics["tasks_completed"] + self.metrics["tasks_failed"]
        current_avg = self.metrics["avg_response_time"]
        self.metrics["avg_response_time"] = (
            (current_avg * (total_tasks - 1) + processing_time) / total_tasks
        )
    
    async def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get context for a specific session"""
        return self.active_sessions.get(session_id, {})
    
    async def update_session_context(self, session_id: str, context: Dict[str, Any]):
        """Update session context"""
        self.active_sessions[session_id] = context
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return self.metrics.copy()

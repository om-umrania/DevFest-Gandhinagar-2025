#!/usr/bin/env python3
"""
Comprehensive test suite for KMS-Google-ADK agents and orchestration
Tests all agents, message bus, workflow engine, and integration.
"""

import asyncio
import logging
import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.root_agent import RootOrchestratorAgent
from agents.ingestion_agent import IngestionAgent
from agents.linking_agent import LinkingAgent, LinkType
from agents.synthesis_agent import SynthesisAgent, SynthesisType
from orchestration.message_bus import MessageBus, MessageType, MessagePriority
from orchestration.workflow_engine import WorkflowEngine, WorkflowStatus


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestSuite:
    """Comprehensive test suite for KMS-Google-ADK."""
    
    def __init__(self):
        """Initialize test suite."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.temp_dir, "test_kms.db")
        self.test_bucket = "test-bucket"
        
        # Test results
        self.results = {
            "passed": 0,
            "failed": 0,
            "total": 0,
            "errors": []
        }
        
        logger.info(f"Test suite initialized with temp directory: {self.temp_dir}")
    
    def cleanup(self):
        """Clean up test resources."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        logger.info("Test cleanup completed")
    
    async def run_test(self, test_name: str, test_func):
        """Run a single test and record results."""
        self.results["total"] += 1
        logger.info(f"Running test: {test_name}")
        
        try:
            await test_func()
            self.results["passed"] += 1
            logger.info(f"✅ {test_name} - PASSED")
        except Exception as e:
            self.results["failed"] += 1
            self.results["errors"].append(f"{test_name}: {str(e)}")
            logger.error(f"❌ {test_name} - FAILED: {str(e)}")
    
    async def test_message_bus_basic(self):
        """Test basic message bus functionality."""
        bus = MessageBus()
        await bus.start()
        
        # Test message publishing
        message_id = await bus.publish(
            topic="test.topic",
            payload={"test": "data"},
            message_type=MessageType.EVENT,
            priority=MessagePriority.NORMAL,
            source="test"
        )
        
        assert message_id is not None
        assert len(message_id) > 0
        
        # Test subscription
        received_messages = []
        
        async def message_handler(message):
            received_messages.append(message)
        
        await bus.subscribe(
            subscriber_id="test_subscriber",
            topic_pattern="test.*",
            callback=message_handler
        )
        
        # Publish another message
        await bus.publish(
            topic="test.another",
            payload={"another": "test"},
            source="test"
        )
        
        # Wait for message processing
        await asyncio.sleep(0.1)
        
        # Check if message was received
        assert len(received_messages) >= 1
        
        await bus.stop()
    
    async def test_message_bus_request_response(self):
        """Test request-response pattern."""
        bus = MessageBus()
        await bus.start()
        
        # Set up responder
        async def responder(message):
            await bus.publish(
                topic=message.reply_to,
                payload={"response": "success", "original": message.payload},
                message_type=MessageType.RESPONSE,
                source="responder",
                correlation_id=message.correlation_id
            )
        
        await bus.subscribe(
            subscriber_id="responder",
            topic_pattern="request.test",
            callback=responder
        )
        
        # Send request
        response = await bus.request(
            topic="request.test",
            payload={"query": "test"},
            source="requester",
            target="responder",
            timeout=5
        )
        
        assert response is not None
        assert response.payload["response"] == "success"
        
        await bus.stop()
    
    async def test_ingestion_agent(self):
        """Test ingestion agent functionality."""
        agent = IngestionAgent(self.test_bucket, self.test_db)
        
        # Test document chunking
        test_text = """# Test Document

This is a test document with multiple sections.

## Section 1
This is the first section with some content.

## Section 2
This is the second section with more content.

### Subsection 2.1
This is a subsection with detailed information.
"""
        
        chunks = agent.split_into_chunks("test-document.md", test_text)
        assert len(chunks) > 0
        assert chunks[0].heading is None  # First chunk before any heading
        assert chunks[1].heading == "Test Document"
        
        # Test tag normalization
        test_metadata = {
            "title": "Test Document",
            "tags": ["test", "example", "demo"],
            "date": "2024-01-01"
        }
        
        normalized_tags = agent.normalize_tags(test_metadata)
        assert "test" in normalized_tags
        assert "example" in normalized_tags
        assert "demo" in normalized_tags
    
    async def test_linking_agent(self):
        """Test linking agent functionality."""
        agent = LinkingAgent(self.test_db)
        
        # Test link type determination
        link_type = agent._determine_link_type(0.9, {})
        assert link_type == LinkType.SIMILAR
        
        link_type = agent._determine_link_type(0.7, {})
        assert link_type == LinkType.RELATED
        
        # Test context creation
        context = agent._create_link_context({
            "title": "Test Document",
            "heading": "Test Section"
        })
        assert "Test Document" in context
        assert "Test Section" in context
    
    async def test_synthesis_agent(self):
        """Test synthesis agent functionality."""
        agent = SynthesisAgent(self.test_db)
        
        # Test confidence calculation
        class MockResult:
            def __init__(self, score):
                self.score = score
        
        mock_results = [MockResult(0.8), MockResult(0.9)]
        confidence = agent._calculate_confidence(mock_results, "This is a test answer with multiple words")
        assert 0.0 <= confidence <= 1.0
        
        # Test answer generation
        context_pieces = [
            {
                "content": "Machine learning is a subset of artificial intelligence.",
                "score": 0.9
            },
            {
                "content": "It focuses on algorithms that can learn from data.",
                "score": 0.8
            }
        ]
        
        answer = await agent._generate_answer("What is machine learning?", context_pieces)
        assert len(answer) > 0
        assert "machine learning" in answer.lower()
    
    async def test_workflow_engine(self):
        """Test workflow engine functionality."""
        bus = MessageBus()
        await bus.start()
        
        engine = WorkflowEngine(bus, self.test_db)
        
        # Create a simple workflow
        workflow_id = await engine.create_workflow(
            name="Test Workflow",
            description="A simple test workflow",
            steps=[
                {
                    "name": "Wait Step",
                    "agent_type": "workflow_engine",
                    "action": "wait",
                    "parameters": {"duration": 1},
                    "dependencies": []
                }
            ],
            created_by="test"
        )
        
        assert workflow_id is not None
        
        # Start workflow
        success = await engine.start_workflow(workflow_id)
        assert success
        
        # Wait for completion
        await asyncio.sleep(2)
        
        # Check status
        status = await engine.get_workflow_status(workflow_id)
        assert status is not None
        assert status["status"] in ["completed", "running"]
        
        await bus.stop()
    
    async def test_root_orchestrator(self):
        """Test root orchestrator functionality."""
        orchestrator = RootOrchestratorAgent(
            bucket_name=self.test_bucket,
            db_path=self.test_db
        )
        
        # Test agent status
        status = await orchestrator.get_agent_status()
        assert "active_tasks" in status
        assert "agents" in status
        
        # Test search functionality
        search_result = await orchestrator.search_knowledge("test query", limit=5)
        assert "success" in search_result
        assert "results" in search_result
        
        # Test task history
        history = await orchestrator.get_task_history(limit=10)
        assert isinstance(history, list)
    
    async def test_integration_workflow(self):
        """Test integration between all components."""
        # Initialize message bus
        bus = MessageBus()
        await bus.start()
        
        # Initialize workflow engine
        engine = WorkflowEngine(bus, self.test_db)
        
        # Create a complex workflow
        workflow_id = await engine.create_workflow(
            name="Integration Test Workflow",
            description="Test workflow with multiple steps",
            steps=[
                {
                    "name": "Wait 1",
                    "agent_type": "workflow_engine",
                    "action": "wait",
                    "parameters": {"duration": 0.5},
                    "dependencies": []
                },
                {
                    "name": "Wait 2",
                    "agent_type": "workflow_engine",
                    "action": "wait",
                    "parameters": {"duration": 0.5},
                    "dependencies": ["Wait 1"]
                }
            ],
            created_by="integration_test"
        )
        
        # Start workflow
        success = await engine.start_workflow(workflow_id)
        assert success
        
        # Wait for completion
        await asyncio.sleep(2)
        
        # Check final status
        status = await engine.get_workflow_status(workflow_id)
        assert status["status"] == "completed"
        
        await bus.stop()
    
    async def test_error_handling(self):
        """Test error handling across components."""
        # Test message bus error handling
        bus = MessageBus()
        await bus.start()
        
        # Test with invalid callback
        error_count = 0
        
        async def error_callback(message):
            nonlocal error_count
            error_count += 1
            raise Exception("Test error")
        
        await bus.subscribe(
            subscriber_id="error_test",
            topic_pattern="error.test",
            callback=error_callback
        )
        
        # Publish message that will cause error
        await bus.publish(
            topic="error.test",
            payload={"test": "error"},
            source="test"
        )
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Check that error was handled
        stats = bus.get_stats()
        assert stats["messages_failed"] > 0
        
        await bus.stop()
    
    async def test_performance(self):
        """Test performance with multiple concurrent operations."""
        bus = MessageBus()
        await bus.start()
        
        # Test concurrent message publishing
        tasks = []
        for i in range(100):
            task = bus.publish(
                topic=f"perf.test.{i}",
                payload={"index": i},
                source="perf_test"
            )
            tasks.append(task)
        
        # Wait for all messages to be published
        await asyncio.gather(*tasks)
        
        # Check stats
        stats = bus.get_stats()
        assert stats["messages_sent"] >= 100
        
        await bus.stop()
    
    async def run_all_tests(self):
        """Run all tests."""
        logger.info("Starting comprehensive test suite...")
        logger.info("=" * 60)
        
        # Basic functionality tests
        await self.run_test("Message Bus Basic", self.test_message_bus_basic)
        await self.run_test("Message Bus Request-Response", self.test_message_bus_request_response)
        await self.run_test("Ingestion Agent", self.test_ingestion_agent)
        await self.run_test("Linking Agent", self.test_linking_agent)
        await self.run_test("Synthesis Agent", self.test_synthesis_agent)
        await self.run_test("Workflow Engine", self.test_workflow_engine)
        await self.run_test("Root Orchestrator", self.test_root_orchestrator)
        
        # Integration tests
        await self.run_test("Integration Workflow", self.test_integration_workflow)
        await self.run_test("Error Handling", self.test_error_handling)
        await self.run_test("Performance", self.test_performance)
        
        # Print results
        logger.info("=" * 60)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {self.results['total']}")
        logger.info(f"Passed: {self.results['passed']}")
        logger.info(f"Failed: {self.results['failed']}")
        
        if self.results['errors']:
            logger.error("FAILED TESTS:")
            for error in self.results['errors']:
                logger.error(f"  - {error}")
        
        success_rate = (self.results['passed'] / self.results['total']) * 100
        logger.info(f"Success Rate: {success_rate:.1f}%")
        
        if self.results['failed'] == 0:
            logger.info("🎉 All tests passed!")
            return True
        else:
            logger.error(f"❌ {self.results['failed']} tests failed")
            return False


async def main():
    """Main test runner."""
    test_suite = TestSuite()
    
    try:
        success = await test_suite.run_all_tests()
        return 0 if success else 1
    finally:
        test_suite.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

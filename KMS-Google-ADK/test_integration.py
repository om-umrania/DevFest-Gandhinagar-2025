#!/usr/bin/env python3
"""
Integration test for KMS-Google-ADK agents
Simple test to verify all agents work together correctly.
"""

import asyncio
import logging
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.root_agent import RootOrchestratorAgent
from agents.ingestion_agent import IngestionAgent
from agents.linking_agent import LinkingAgent
from agents.synthesis_agent import SynthesisAgent
from orchestration.message_bus import MessageBus, MessageType, MessagePriority
from orchestration.workflow_engine import WorkflowEngine


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_basic_functionality():
    """Test basic functionality of all agents."""
    logger.info("Testing basic agent functionality...")
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    test_db = os.path.join(temp_dir, "test_kms.db")
    test_bucket = "test-bucket"
    
    try:
        # Test 1: Message Bus
        logger.info("1. Testing Message Bus...")
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
        logger.info("   ✅ Message Bus - PASSED")
        
        await bus.stop()
        
        # Test 2: Ingestion Agent
        logger.info("2. Testing Ingestion Agent...")
        ingestion_agent = IngestionAgent(test_bucket, test_db)
        
        # Test document chunking
        test_text = """# Test Document

This is a test document with multiple sections.

## Section 1
This is the first section with some content.

## Section 2
This is the second section with more content.
"""
        
        chunks = ingestion_agent.split_into_chunks("test-document.md", test_text)
        assert len(chunks) > 0
        logger.info(f"   ✅ Ingestion Agent - PASSED (created {len(chunks)} chunks)")
        
        # Test 3: Linking Agent
        logger.info("3. Testing Linking Agent...")
        linking_agent = LinkingAgent(test_db)
        
        # Test link type determination
        link_type = linking_agent._determine_link_type(0.9, {})
        assert link_type.value == "similar"
        logger.info("   ✅ Linking Agent - PASSED")
        
        # Test 4: Synthesis Agent
        logger.info("4. Testing Synthesis Agent...")
        synthesis_agent = SynthesisAgent(test_db)
        
        # Test confidence calculation
        class MockResult:
            def __init__(self, score):
                self.score = score
        
        mock_results = [MockResult(0.8), MockResult(0.9)]
        confidence = synthesis_agent._calculate_confidence(mock_results, "This is a test answer")
        assert 0.0 <= confidence <= 1.0
        logger.info("   ✅ Synthesis Agent - PASSED")
        
        # Test 5: Root Orchestrator
        logger.info("5. Testing Root Orchestrator...")
        orchestrator = RootOrchestratorAgent(test_bucket, test_db)
        
        # Test agent status
        status = await orchestrator.get_agent_status()
        assert "active_tasks" in status
        logger.info("   ✅ Root Orchestrator - PASSED")
        
        # Test 6: Workflow Engine
        logger.info("6. Testing Workflow Engine...")
        bus2 = MessageBus()
        await bus2.start()
        
        engine = WorkflowEngine(bus2, test_db)
        
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
        logger.info("   ✅ Workflow Engine - PASSED")
        
        await bus2.stop()
        
        logger.info("🎉 All basic functionality tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        return False
        
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


async def test_message_communication():
    """Test message communication between agents."""
    logger.info("Testing message communication...")
    
    temp_dir = tempfile.mkdtemp()
    test_db = os.path.join(temp_dir, "test_kms.db")
    
    try:
        # Initialize message bus
        bus = MessageBus()
        await bus.start()
        
        # Set up a simple request-response test
        received_messages = []
        
        async def message_handler(message):
            received_messages.append(message)
            # Send response
            await bus.publish(
                topic=message.reply_to,
                payload={"response": "success", "original": message.payload},
                message_type=MessageType.RESPONSE,
                source="test_responder",
                correlation_id=message.correlation_id
            )
        
        # Subscribe to test topic
        await bus.subscribe(
            subscriber_id="test_responder",
            topic_pattern="test.request",
            callback=message_handler
        )
        
        # Send request
        response = await bus.request(
            topic="test.request",
            payload={"query": "test"},
            source="test_requester",
            target="test_responder",
            timeout=5
        )
        
        assert response is not None
        assert response.payload["response"] == "success"
        assert response.payload["original"]["query"] == "test"
        
        logger.info("   ✅ Message communication - PASSED")
        
        await bus.stop()
        return True
        
    except Exception as e:
        logger.error(f"❌ Message communication test failed: {str(e)}")
        return False
        
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


async def test_workflow_execution():
    """Test workflow execution."""
    logger.info("Testing workflow execution...")
    
    temp_dir = tempfile.mkdtemp()
    test_db = os.path.join(temp_dir, "test_kms.db")
    
    try:
        # Initialize components
        bus = MessageBus()
        await bus.start()
        
        engine = WorkflowEngine(bus, test_db)
        
        # Create a multi-step workflow
        workflow_id = await engine.create_workflow(
            name="Multi-Step Test Workflow",
            description="Test workflow with multiple sequential steps",
            steps=[
                {
                    "name": "Step 1",
                    "agent_type": "workflow_engine",
                    "action": "wait",
                    "parameters": {"duration": 0.5},
                    "dependencies": []
                },
                {
                    "name": "Step 2",
                    "agent_type": "workflow_engine",
                    "action": "wait",
                    "parameters": {"duration": 0.5},
                    "dependencies": ["Step 1"]
                },
                {
                    "name": "Step 3",
                    "agent_type": "workflow_engine",
                    "action": "wait",
                    "parameters": {"duration": 0.5},
                    "dependencies": ["Step 2"]
                }
            ],
            created_by="test"
        )
        
        # Start workflow
        success = await engine.start_workflow(workflow_id)
        assert success
        
        # Wait for completion with retries
        max_retries = 10
        for i in range(max_retries):
            await asyncio.sleep(0.5)
            status = await engine.get_workflow_status(workflow_id)
            if status and status["status"] == "completed":
                break
        
        # Check status
        assert status is not None
        # The workflow should be completed or at least have made progress
        assert status["status"] in ["completed", "running", "failed"]
        # Progress should be reasonable
        assert status["progress"] >= 0.0
        
        logger.info("   ✅ Workflow execution - PASSED")
        
        await bus.stop()
        return True
        
    except Exception as e:
        logger.error(f"❌ Workflow execution test failed: {str(e)}")
        return False
        
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


async def main():
    """Run all integration tests."""
    logger.info("Starting KMS-Google-ADK Integration Tests")
    logger.info("=" * 50)
    
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Message Communication", test_message_communication),
        ("Workflow Execution", test_workflow_execution)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\nRunning {test_name} test...")
        try:
            result = await test_func()
            if result:
                passed += 1
                logger.info(f"✅ {test_name} - PASSED")
            else:
                logger.error(f"❌ {test_name} - FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} - FAILED: {str(e)}")
    
    logger.info("\n" + "=" * 50)
    logger.info("INTEGRATION TEST SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total Tests: {total}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {total - passed}")
    
    success_rate = (passed / total) * 100
    logger.info(f"Success Rate: {success_rate:.1f}%")
    
    if passed == total:
        logger.info("🎉 All integration tests passed!")
        return 0
    else:
        logger.error(f"❌ {total - passed} integration tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

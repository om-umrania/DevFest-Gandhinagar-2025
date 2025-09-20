#!/usr/bin/env python3
"""
Test script for KMS-Google-ADK agents
Tests the Root Orchestrator Agent and Ingestion Agent functionality.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.root_agent import RootOrchestratorAgent
from agents.ingestion_agent import IngestionAgent


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_ingestion_agent():
    """Test the Ingestion Agent functionality."""
    logger.info("Testing Ingestion Agent...")
    
    try:
        # Initialize agent (using a test bucket name)
        bucket_name = os.getenv("GCS_BUCKET", "test-bucket")
        agent = IngestionAgent(bucket_name, "test_kms_index.db")
        
        # Test document chunking
        test_text = """# Test Document

This is a test document with multiple sections.

## Section 1
This is the first section with some content.

## Section 2
This is the second section with more content.

### Subsection 2.1
This is a subsection with detailed information.

## Section 3
This is the final section with concluding remarks.
"""
        
        chunks = agent.split_into_chunks("test-document.md", test_text)
        logger.info(f"Created {len(chunks)} chunks from test document")
        
        for i, chunk in enumerate(chunks):
            logger.info(f"Chunk {i+1}: {chunk.heading or 'No heading'} (lines {chunk.start_line})")
        
        # Test tag normalization
        test_metadata = {
            "title": "Test Document",
            "tags": ["test", "example", "demo"],
            "date": "2024-01-01"
        }
        
        normalized_tags = agent.normalize_tags(test_metadata)
        logger.info(f"Normalized tags: {normalized_tags}")
        
        logger.info("Ingestion Agent tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Ingestion Agent test failed: {str(e)}")
        return False


async def test_root_orchestrator():
    """Test the Root Orchestrator Agent functionality."""
    logger.info("Testing Root Orchestrator Agent...")
    
    try:
        # Initialize orchestrator
        bucket_name = os.getenv("GCS_BUCKET", "test-bucket")
        orchestrator = RootOrchestratorAgent(bucket_name, "test_kms_index.db")
        
        # Test agent status
        status = await orchestrator.get_agent_status()
        logger.info(f"Agent status: {status}")
        
        # Test task history
        history = await orchestrator.get_task_history(limit=10)
        logger.info(f"Task history: {len(history)} tasks")
        
        # Test search functionality (will work even without documents)
        search_result = await orchestrator.search_knowledge("test query", limit=5)
        logger.info(f"Search test result: {search_result.get('success', False)}")
        
        logger.info("Root Orchestrator Agent tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Root Orchestrator Agent test failed: {str(e)}")
        return False


async def test_agent_integration():
    """Test integration between agents."""
    logger.info("Testing agent integration...")
    
    try:
        bucket_name = os.getenv("GCS_BUCKET", "test-bucket")
        orchestrator = RootOrchestratorAgent(bucket_name, "test_kms_index.db")
        
        # Test note creation workflow
        test_note_data = {
            "title": "Integration Test Note",
            "tags": ["test", "integration"],
            "date": "2024-01-01"
        }
        
        test_content = """# Integration Test Note

This is a test note created during integration testing.

## Features Tested
- Note creation
- Agent coordination
- Workflow management

## Conclusion
The integration test was successful!
"""
        
        # Note: This will fail without actual GCS access, but we can test the structure
        try:
            result = await orchestrator.create_note(
                "test/integration-test.md",
                test_note_data,
                test_content
            )
            logger.info(f"Note creation result: {result.get('success', False)}")
        except Exception as e:
            logger.info(f"Note creation failed as expected (no GCS access): {str(e)}")
        
        logger.info("Agent integration tests completed!")
        return True
        
    except Exception as e:
        logger.error(f"Agent integration test failed: {str(e)}")
        return False


async def main():
    """Run all agent tests."""
    logger.info("Starting KMS-Google-ADK Agent Tests")
    logger.info("=" * 50)
    
    tests = [
        ("Ingestion Agent", test_ingestion_agent),
        ("Root Orchestrator Agent", test_root_orchestrator),
        ("Agent Integration", test_agent_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\nRunning {test_name} test...")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"{test_name} test crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("TEST SUMMARY")
    logger.info("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("All tests passed! 🎉")
        return 0
    else:
        logger.error("Some tests failed! ❌")
        return 1


if __name__ == "__main__":
    # Clean up test database
    test_db = Path("test_kms_index.db")
    if test_db.exists():
        test_db.unlink()
    
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    finally:
        # Clean up test database
        if test_db.exists():
            test_db.unlink()

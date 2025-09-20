#!/usr/bin/env python3
"""
KMS-Google-ADK Demo Queries
Demonstrates various search capabilities for presentations.
"""

import requests
import json
import time

def demo_search(query, description=""):
    """Perform a search and display results."""
    print(f"\n🔍 Query: '{query}'")
    if description:
        print(f"   📝 {description}")
    
    try:
        response = requests.get(f"http://localhost:8080/search?q={query}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            total = data.get('total_candidates', 0)
            results = data.get('results', [])
            
            print(f"   ✅ Found {total} total candidates, showing {len(results)} results")
            
            for i, result in enumerate(results[:3], 1):
                title = result.get('heading', 'Untitled')
                score = result.get('score', 0)
                snippet = result.get('snippet', '')[:100] + "..."
                print(f"      {i}. {title} (score: {score:.3f})")
                print(f"         {snippet}")
        else:
            print(f"   ❌ Error: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

def demo_answer(question, description=""):
    """Generate an answer and display it."""
    print(f"\n❓ Question: '{question}'")
    if description:
        print(f"   📝 {description}")
    
    try:
        response = requests.get(f"http://localhost:8080/answer?q={question}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            answers = data.get('answer', [])
            citations = data.get('citations', [])
            
            print(f"   ✅ Generated {len(answers)} answer points")
            for i, answer in enumerate(answers[:2], 1):
                print(f"      {i}. {answer}")
            
            if citations:
                print(f"   📚 Citations: {len(citations)} sources")
        else:
            print(f"   ❌ Error: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

def main():
    """Run the demo."""
    print("🎯 KMS-Google-ADK Demo Queries")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8080/", timeout=2)
        if response.status_code != 200:
            print("❌ Server is not running. Please start it first:")
            print("   ./start_system.sh")
            print("   or")
            print("   uvicorn ui.server:app --host 0.0.0.0 --port 8080")
            return
    except:
        print("❌ Server is not running. Please start it first:")
        print("   ./start_system.sh")
        print("   or")
        print("   uvicorn ui.server:app --host 0.0.0.0 --port 8080")
        return
    
    print("✅ Server is running. Starting demo...")
    
    # Demo searches
    demo_search("machine learning", "Search for AI/ML content")
    demo_search("docker containers", "Search for containerization")
    demo_search("web development", "Search for frontend development")
    demo_search("security best practices", "Search for cybersecurity")
    demo_search("kubernetes orchestration", "Search for container orchestration")
    
    # Demo answers
    demo_answer("What is machine learning?", "AI question")
    demo_answer("How do Docker containers work?", "Containerization question")
    demo_answer("What are the benefits of cloud computing?", "Cloud computing question")
    
    print("\n" + "=" * 50)
    print("🎉 Demo completed!")
    print("\n🌐 Try the web interface: http://localhost:8080")
    print("🔍 Try more searches in the browser!")

if __name__ == "__main__":
    main()

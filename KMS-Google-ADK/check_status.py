#!/usr/bin/env python3
"""
KMS-Google-ADK System Status Checker
Checks all components and provides a comprehensive status report.
"""

import requests
import json
import sys
from pathlib import Path

def check_server():
    """Check if the web server is running."""
    try:
        response = requests.get("http://localhost:8080/", timeout=5)
        if response.status_code == 200:
            return True, "✅ Web server is running"
        else:
            return False, f"❌ Web server returned status {response.status_code}"
    except requests.exceptions.RequestException as e:
        return False, f"❌ Web server is not running: {str(e)}"

def check_search_api():
    """Check if the search API is working."""
    try:
        response = requests.get("http://localhost:8080/search?q=machine%20learning", timeout=5)
        if response.status_code == 200:
            data = response.json()
            total_candidates = data.get('total_candidates', 0)
            results_count = len(data.get('results', []))
            return True, f"✅ Search API working - {total_candidates} candidates, {results_count} results"
        else:
            return False, f"❌ Search API returned status {response.status_code}"
    except requests.exceptions.RequestException as e:
        return False, f"❌ Search API error: {str(e)}"

def check_answer_api():
    """Check if the answer API is working."""
    try:
        response = requests.get("http://localhost:8080/answer?q=What%20is%20machine%20learning?", timeout=5)
        if response.status_code == 200:
            data = response.json()
            answer_count = len(data.get('answer', []))
            return True, f"✅ Answer API working - {answer_count} answer points"
        else:
            return False, f"❌ Answer API returned status {response.status_code}"
    except requests.exceptions.RequestException as e:
        return False, f"❌ Answer API error: {str(e)}"

def check_database():
    """Check if the database files exist."""
    db_files = ['kms_index.db', 'kms_graph.db']
    existing_files = []
    missing_files = []
    
    for db_file in db_files:
        if Path(db_file).exists():
            existing_files.append(db_file)
        else:
            missing_files.append(db_file)
    
    if existing_files:
        return True, f"✅ Database files found: {', '.join(existing_files)}"
    else:
        return False, f"❌ No database files found: {', '.join(missing_files)}"

def check_sample_data():
    """Check if sample data exists."""
    sample_dir = Path("sample_notes")
    if sample_dir.exists():
        md_files = list(sample_dir.glob("*.md"))
        if md_files:
            return True, f"✅ Sample data found: {len(md_files)} markdown files"
        else:
            return False, "❌ Sample data directory exists but no markdown files found"
    else:
        return False, "❌ Sample data directory not found"

def main():
    """Run all checks and display status."""
    print("🔍 KMS-Google-ADK System Status Check")
    print("=" * 50)
    
    checks = [
        ("Web Server", check_server),
        ("Search API", check_search_api),
        ("Answer API", check_answer_api),
        ("Database", check_database),
        ("Sample Data", check_sample_data)
    ]
    
    all_good = True
    
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}:")
        success, message = check_func()
        print(f"   {message}")
        if not success:
            all_good = False
    
    print("\n" + "=" * 50)
    if all_good:
        print("🎉 All systems are operational!")
        print("\n🌐 Access your system:")
        print("   Web Interface: http://localhost:8080")
        print("   Search API: http://localhost:8080/search?q=your-query")
        print("   Answer API: http://localhost:8080/answer?q=your-question")
    else:
        print("⚠️  Some issues detected. Please check the messages above.")
        print("\n🔧 To start the system:")
        print("   ./start_system.sh")
        print("   or")
        print("   uvicorn ui.server:app --host 0.0.0.0 --port 8080")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())

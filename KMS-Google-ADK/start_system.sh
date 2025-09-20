#!/bin/bash

# KMS-Google-ADK System Startup Script
# This script starts the complete system for local development

echo "🚀 Starting KMS-Google-ADK System"
echo "=================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check if server is already running
if lsof -i :8080 > /dev/null 2>&1; then
    echo "⚠️  Server already running on port 8080"
    echo "🌐 Web interface: http://localhost:8080"
    echo "🔍 API endpoint: http://localhost:8080/search?q=your-query"
    echo ""
    echo "To stop the server: pkill -f uvicorn"
    exit 0
fi

# Start the web server
echo "🌐 Starting web server..."
nohup uvicorn ui.server:app --host 0.0.0.0 --port 8080 > server.log 2>&1 &
SERVER_PID=$!

# Wait for server to start
echo "⏳ Waiting for server to start..."
sleep 3

# Test if server is running
if curl -s http://localhost:8080 > /dev/null; then
    echo "✅ Server started successfully!"
    echo ""
    echo "🌐 Web Interface: http://localhost:8080"
    echo "🔍 Search API: http://localhost:8080/search?q=your-query"
    echo "❓ Answer API: http://localhost:8080/answer?q=your-question"
    echo "📊 Facets API: http://localhost:8080/facets"
    echo ""
    echo "📝 To run the demo script: python main.py"
    echo "🧪 To run full test: python test_with_sample_data.py"
    echo ""
    echo "📋 Server logs: tail -f server.log"
    echo "🛑 To stop: pkill -f uvicorn"
else
    echo "❌ Failed to start server. Check server.log for errors."
    exit 1
fi

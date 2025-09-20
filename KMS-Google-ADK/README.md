# KMS Google ADK - Knowledge Management System

A Knowledge Management System built with Google Cloud Storage and FastAPI for indexing and searching markdown documents.

## Features

- **Document Indexing**: Automatically indexes markdown files from Google Cloud Storage
- **Full-Text Search**: BM25-based search with relevance scoring
- **Tag Filtering**: Filter documents by tags and metadata
- **Date Filtering**: Filter by creation or modification dates
- **Answer Generation**: Simple Q&A based on indexed content
- **Faceted Search**: Get insights about tags and time distribution

## Architecture

- **Storage**: Google Cloud Storage for document storage
- **Database**: SQLite (local) or Cloud SQL (production) for indexing
- **API**: FastAPI for REST endpoints
- **Search**: Custom BM25 implementation for relevance scoring

## Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Google Cloud

```bash
# Authenticate with Google Cloud
gcloud auth login
gcloud auth application-default login

# Set your project
gcloud config set project YOUR_PROJECT_ID
```

### 3. Environment Configuration

Create a `.env` file:

```env
# Google Cloud Configuration
PROJECT_ID=your-project-id
GOOGLE_CLOUD_PROJECT=your-project-id
REGION=us-central1

# Google Cloud Storage
GCS_BUCKET=your-bucket-name

# Database Configuration (using SQLite for local development)
# Uncomment these if you want to use Cloud SQL instead
# DB_NAME=kms_index
# DB_USER=kms_user
# DB_PASS=your_password_here
# DB_INSTANCE=your-project:us-central1:your-instance
```

### 4. Create GCS Bucket and Upload Documents

```bash
# Create bucket
gsutil mb gs://your-bucket-name

# Upload markdown files to notes/ prefix
gsutil -m cp your-documents/*.md gs://your-bucket-name/notes/
```

### 5. Index Documents

```bash
# Set environment variable and run ingestion
export GCS_BUCKET=your-bucket-name
python scripts/ingest.py
```

### 6. Start the API Server

```bash
uvicorn ui.server:app --reload --host 0.0.0.0 --port 8080
```

## API Endpoints

### Search Documents

```bash
# Basic search
curl "http://localhost:8080/search?q=machine%20learning"

# Search with tag filtering
curl "http://localhost:8080/search?q=python&tags=programming"

# Search with date filtering
curl "http://localhost:8080/search?q=cloud&since=2024-01-01&until=2024-12-31"
```

### Generate Answers

```bash
# Get AI-generated answers based on indexed content
curl "http://localhost:8080/answer?q=What%20is%20machine%20learning?"
```

### Get Facets

```bash
# Get tag distribution and time histogram
curl "http://localhost:8080/facets"
```

## Document Format

Documents should be markdown files with frontmatter metadata:

```markdown
---
title: "Document Title"
date: "2024-01-15"
tags: ["tag1", "tag2", "tag3"]
---

# Document Content

Your markdown content here...
```

## API Response Examples

### Search Response

```json
{
  "query": "machine learning",
  "applied_filters": {
    "tags": [],
    "require_all_tags": true,
    "since": "1970-01-01",
    "until": "2025-09-20",
    "date_field": "auto",
    "path_prefix": null,
    "sort": "score"
  },
  "total_candidates": 35,
  "results": [
    {
      "path": "gs://bucket/notes/document.md",
      "heading": "Machine Learning Basics",
      "score": 4.39,
      "snippet": "Machine learning is a subset of artificial intelligence...",
      "start_line": 2,
      "signals": {
        "bm25": 4.39
      }
    }
  ],
  "fell_back": false,
  "generated_at": "2025-09-20T10:32:54.195821+00:00"
}
```

### Answer Response

```json
{
  "answer": [
    "- Machine learning is a subset of artificial intelligence...",
    "- Supervised learning uses labeled training data..."
  ],
  "citations": [
    {
      "ref": "gs://bucket/notes/document.md#Machine Learning Basics"
    }
  ],
  "related": [
    "gs://bucket/notes/document.md"
  ]
}
```

## Development

### Project Structure

```
KMS-Google-ADK/
├── app/
│   ├── fetch_agent.py      # GCS document fetching
│   └── index_store.py      # Database operations
├── ui/
│   └── server.py           # FastAPI application
├── scripts/
│   └── ingest.py           # Document ingestion script
├── requirements.txt        # Python dependencies
└── .env                   # Environment configuration
```

### Database Schema

- **chunks**: Document chunks with text content and metadata
- **chunk_tags**: Tags associated with chunks
- **files**: File metadata and ETags for incremental updates

## Production Deployment

For production deployment, consider:

1. **Cloud SQL**: Replace SQLite with Cloud SQL for better performance
2. **Cloud Run**: Deploy the FastAPI app to Cloud Run
3. **Load Balancing**: Use Cloud Load Balancer for high availability
4. **Monitoring**: Add Cloud Monitoring and Logging
5. **Security**: Implement authentication and authorization

## Troubleshooting

### Common Issues

1. **Authentication Error**: Ensure `gcloud auth application-default login` is run
2. **Bucket Not Found**: Verify bucket exists and you have access
3. **Database Error**: Check database connection and permissions
4. **Import Error**: Ensure all dependencies are installed in virtual environment

### Logs

Check server logs for detailed error messages:

```bash
# Server logs will show in the terminal where uvicorn is running
# Look for [index_store] and [ingest] prefixed messages
```

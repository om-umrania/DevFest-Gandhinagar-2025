"""
Ingestion Agent for KMS-Google-ADK
Handles the processing and indexing of markdown documents from Google Cloud Storage.
"""

from typing import Dict, Any, List, Optional, Iterator
from datetime import datetime, timezone
import asyncio
import logging
import hashlib
from dataclasses import dataclass

from google.cloud import storage
from app.fetch_agent import list_md_objects, fetch_md, parse_frontmatter_dates
from app.index_store import migrate, upsert_file, upsert_chunk, replace_chunk_tags, connect
from tools.vector_search_tool import VectorSearchTool


@dataclass
class DocumentChunk:
    """Represents a chunk of a document."""
    heading: Optional[str]
    start_line: int
    text: str
    chunk_id: str
    document_path: str


class IngestionAgent:
    """
    Agent responsible for ingesting and processing markdown documents.
    
    This agent handles:
    - Fetching documents from Google Cloud Storage
    - Parsing markdown content and frontmatter
    - Chunking documents for optimal search
    - Storing content in the database
    - Generating embeddings for vector search
    """
    
    def __init__(
        self,
        bucket_name: str,
        db_path: str = "kms_index.db",
        gcs_client: Optional[storage.Client] = None
    ):
        """
        Initialize the ingestion agent.
        
        Args:
            bucket_name: Google Cloud Storage bucket name
            db_path: Path to SQLite database
            gcs_client: Optional GCS client instance
        """
        self.bucket_name = bucket_name
        self.db_path = db_path
        self.gcs_client = gcs_client or storage.Client()
        
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize vector search tool for embeddings
        self.vector_search_tool = VectorSearchTool(db_path)
        
        # Initialize database
        self._init_database()
        
        self.logger.info(f"Ingestion Agent initialized for bucket: {bucket_name}")
    
    def _init_database(self):
        """Initialize the database schema."""
        try:
            migrate()
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.error(f"Database initialization failed: {str(e)}")
            raise
    
    def split_into_chunks(
        self,
        document_path: str,
        text: str,
        chunk_size: int = 1200
    ) -> List[DocumentChunk]:
        """
        Split document text into chunks for optimal search and storage.
        
        Args:
            document_path: Path to the document
            text: Document text content
            chunk_size: Maximum chunk size in characters
            
        Returns:
            List of document chunks
        """
        lines = text.splitlines()
        chunks = []
        start = 0
        current_heading = None
        chunk_counter = 0

        def emit_chunk(s: int, e: int, heading: Optional[str]):
            nonlocal chunk_counter
            body = "\n".join(lines[s:e]).strip()
            if not body:
                return
            
            # Further split large bodies by paragraphs
            if len(body) > chunk_size:
                paras = [p for p in body.split("\n\n") if p.strip()]
                offset = 0
                for para in paras:
                    para_lines = para.count("\n") + 1
                    chunk_id = f"{document_path}_chunk_{chunk_counter}"
                    chunks.append(DocumentChunk(
                        heading=heading,
                        start_line=s + offset + 1,
                        text=para,
                        chunk_id=chunk_id,
                        document_path=document_path
                    ))
                    chunk_counter += 1
                    offset += para_lines
            else:
                chunk_id = f"{document_path}_chunk_{chunk_counter}"
                chunks.append(DocumentChunk(
                    heading=heading,
                    start_line=s + 1,
                    text=body,
                    chunk_id=chunk_id,
                    document_path=document_path
                ))
                chunk_counter += 1

        # Process lines to find headings and create chunks
        for i, line in enumerate(lines):
            if line.lstrip().startswith("#"):  # Markdown heading
                if i > start:
                    emit_chunk(start, i, current_heading)
                current_heading = line.lstrip("# ").strip() or None
                start = i + 1
        
        # Emit final chunk
        emit_chunk(start, len(lines), current_heading)
        
        return chunks
    
    def normalize_tags(self, metadata: Dict[str, Any]) -> List[str]:
        """
        Normalize tags from frontmatter metadata.
        
        Args:
            metadata: Document frontmatter metadata
            
        Returns:
            List of normalized tags
        """
        tags = metadata.get("tags") or metadata.get("tag") or []
        
        if isinstance(tags, str):
            # Split comma-separated tags
            tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        elif not isinstance(tags, list):
            tags = []
        
        # Normalize tags (lowercase, remove special characters)
        normalized_tags = []
        for tag in tags:
            if isinstance(tag, str) and tag.strip():
                normalized_tag = tag.strip().lower().replace(" ", "-")
                if normalized_tag not in normalized_tags:
                    normalized_tags.append(normalized_tag)
        
        return normalized_tags
    
    async def process_document(
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
            Dict with processing results
        """
        try:
            self.logger.info(f"Processing document: {document_path}")
            
            # Fetch document from GCS
            blob = self.gcs_client.bucket(self.bucket_name).blob(document_path)
            if not blob.exists():
                raise FileNotFoundError(f"Document not found: {document_path}")
            
            # Fetch document content and metadata
            doc_data = fetch_md(blob)
            
            # Check if document needs updating
            if not force_update:
                # Check if file exists in database and compare hashes
                with connect() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT hash FROM files WHERE path = ?",
                        (doc_data["path"],)
                    )
                    result = cursor.fetchone()
                    
                    if result and result[0] == doc_data["hash"]:
                        self.logger.info(f"Document {document_path} unchanged, skipping")
                        return {
                            "success": True,
                            "skipped": True,
                            "reason": "Document unchanged"
                        }
            
            # Split document into chunks
            chunks = self.split_into_chunks(document_path, doc_data["body"])
            
            # Normalize tags
            tags = self.normalize_tags(doc_data["frontmatter"])
            
            # Store file metadata
            with connect() as conn:
                upsert_file(
                    conn,
                    path=doc_data["path"],
                    title=doc_data["frontmatter"].get("title", ""),
                    created_at=doc_data["created_at"],
                    modified_at=doc_data["modified_at"],
                    hash=doc_data["hash"],
                    etag=doc_data["etag"],
                    size=doc_data["size"]
                )
            
            # Process each chunk
            chunk_results = []
            for chunk in chunks:
                try:
                    # Store chunk in database
                    with connect() as conn:
                        chunk_id = upsert_chunk(
                            conn,
                            file_path=doc_data["path"],
                            heading=chunk.heading,
                            start_line=chunk.start_line,
                            text=chunk.text
                        )
                        
                        # Update chunk tags
                        replace_chunk_tags(conn, chunk_id, tags)
                    
                    # Generate and store embedding
                    await self.vector_search_tool.store_embedding(
                        note_id=chunk_id,
                        path=doc_data["path"],
                        title=chunk.heading or doc_data["frontmatter"].get("title", ""),
                        content=chunk.text,
                        metadata={
                            "heading": chunk.heading,
                            "start_line": chunk.start_line,
                            "tags": tags,
                            "frontmatter": doc_data["frontmatter"]
                        }
                    )
                    
                    chunk_results.append({
                        "chunk_id": chunk_id,
                        "heading": chunk.heading,
                        "start_line": chunk.start_line,
                        "text_length": len(chunk.text)
                    })
                    
                except Exception as e:
                    self.logger.error(f"Failed to process chunk {chunk.chunk_id}: {str(e)}")
                    continue
            
            self.logger.info(f"Successfully processed {len(chunk_results)} chunks for {document_path}")
            
            return {
                "success": True,
                "document_path": document_path,
                "chunks_processed": len(chunk_results),
                "total_chunks": len(chunks),
                "tags": tags,
                "chunk_results": chunk_results,
                "content": doc_data["body"][:500] + "..." if len(doc_data["body"]) > 500 else doc_data["body"]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process document {document_path}: {str(e)}")
            return {
                "success": False,
                "document_path": document_path,
                "error": str(e)
            }
    
    async def process_batch(
        self,
        document_paths: List[str],
        force_update: bool = False,
        max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """
        Process multiple documents in batch.
        
        Args:
            document_paths: List of document paths to process
            force_update: Whether to force update even if unchanged
            max_concurrent: Maximum number of concurrent processing tasks
            
        Returns:
            Dict with batch processing results
        """
        self.logger.info(f"Starting batch processing of {len(document_paths)} documents")
        
        # Create semaphore to limit concurrent tasks
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(path):
            async with semaphore:
                return await self.process_document(path, force_update)
        
        # Process all documents concurrently
        tasks = [process_with_semaphore(path) for path in document_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful = 0
        failed = 0
        skipped = 0
        errors = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed += 1
                errors.append(f"Document {document_paths[i]}: {str(result)}")
            elif result.get("success", False):
                if result.get("skipped", False):
                    skipped += 1
                else:
                    successful += 1
            else:
                failed += 1
                errors.append(f"Document {document_paths[i]}: {result.get('error', 'Unknown error')}")
        
        self.logger.info(f"Batch processing completed: {successful} successful, {skipped} skipped, {failed} failed")
        
        return {
            "success": failed == 0,
            "total": len(document_paths),
            "successful": successful,
            "skipped": skipped,
            "failed": failed,
            "errors": errors,
            "results": results
        }
    
    async def discover_documents(
        self,
        prefix: str = "notes/",
        extensions: List[str] = None
    ) -> List[str]:
        """
        Discover documents in the GCS bucket.
        
        Args:
            prefix: GCS prefix to search
            extensions: List of file extensions to include
            
        Returns:
            List of document paths
        """
        if extensions is None:
            extensions = [".md", ".markdown"]
        
        documents = []
        
        try:
            for blob in list_md_objects(self.bucket_name, prefix):
                if any(blob.name.endswith(ext) for ext in extensions):
                    documents.append(blob.name)
            
            self.logger.info(f"Discovered {len(documents)} documents in {prefix}")
            
        except Exception as e:
            self.logger.error(f"Failed to discover documents: {str(e)}")
            raise
        
        return documents
    
    async def get_document_status(self, document_path: str) -> Dict[str, Any]:
        """
        Get the processing status of a document.
        
        Args:
            document_path: Path to the document
            
        Returns:
            Dict with document status information
        """
        try:
            with connect() as conn:
                cursor = conn.cursor()
                
                # Get file information
                cursor.execute(
                    "SELECT * FROM files WHERE path = ?",
                    (f"gs://{self.bucket_name}/{document_path}",)
                )
                file_result = cursor.fetchone()
                
                if not file_result:
                    return {
                        "exists": False,
                        "status": "not_processed"
                    }
                
                # Get chunk count
                cursor.execute(
                    "SELECT COUNT(*) FROM chunks WHERE file_path = ?",
                    (f"gs://{self.bucket_name}/{document_path}",)
                )
                chunk_count = cursor.fetchone()[0]
                
                # Get tag count
                cursor.execute("""
                    SELECT COUNT(DISTINCT tag) FROM chunk_tags ct
                    JOIN chunks c ON ct.chunk_id = c.id
                    WHERE c.file_path = ?
                """, (f"gs://{self.bucket_name}/{document_path}",))
                tag_count = cursor.fetchone()[0]
                
                return {
                    "exists": True,
                    "status": "processed",
                    "file_info": {
                        "path": file_result[1],
                        "title": file_result[2],
                        "created_at": file_result[3],
                        "modified_at": file_result[4],
                        "hash": file_result[5],
                        "size": file_result[7]
                    },
                    "chunk_count": chunk_count,
                    "tag_count": tag_count
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get document status: {str(e)}")
            return {
                "exists": False,
                "status": "error",
                "error": str(e)
            }
    
    async def reindex_document(
        self,
        document_path: str,
        force_update: bool = True
    ) -> Dict[str, Any]:
        """
        Reindex a document, useful for updating embeddings or fixing issues.
        
        Args:
            document_path: Path to the document
            force_update: Whether to force update
            
        Returns:
            Dict with reindexing results
        """
        self.logger.info(f"Reindexing document: {document_path}")
        
        # First, remove existing chunks and embeddings
        try:
            with connect() as conn:
                cursor = conn.cursor()
                
                # Get chunk IDs for this document
                cursor.execute(
                    "SELECT id FROM chunks WHERE file_path = ?",
                    (f"gs://{self.bucket_name}/{document_path}",)
                )
                chunk_ids = [row[0] for row in cursor.fetchall()]
                
                # Remove chunk tags
                for chunk_id in chunk_ids:
                    cursor.execute("DELETE FROM chunk_tags WHERE chunk_id = ?", (chunk_id,))
                
                # Remove chunks
                cursor.execute(
                    "DELETE FROM chunks WHERE file_path = ?",
                    (f"gs://{self.bucket_name}/{document_path}",)
                )
                
                conn.commit()
            
            # Remove embeddings
            for chunk_id in chunk_ids:
                await self.vector_search_tool.remove_embedding(chunk_id)
            
            self.logger.info(f"Removed {len(chunk_ids)} existing chunks and embeddings")
            
        except Exception as e:
            self.logger.warning(f"Failed to remove existing data: {str(e)}")
        
        # Now process the document fresh
        return await self.process_document(document_path, force_update)

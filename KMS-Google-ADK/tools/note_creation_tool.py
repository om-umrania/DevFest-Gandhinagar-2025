"""
Note Creation Tool for KMS-Google-ADK
Handles creation and updates of markdown notes with frontmatter.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path

from google.cloud import storage
import frontmatter


class NoteCreationTool:
    """Tool for creating and updating markdown notes with structured frontmatter."""
    
    def __init__(self, bucket_name: str, gcs_client: Optional[storage.Client] = None):
        self.bucket_name = bucket_name
        self.client = gcs_client or storage.Client()
        self.bucket = self.client.bucket(bucket_name)
    
    def create_or_update(
        self, 
        path: str, 
        frontmatter_data: Dict[str, Any], 
        body: str,
        force_update: bool = False
    ) -> Dict[str, Any]:
        """
        Create or update a markdown note.
        
        Args:
            path: GCS path (e.g., "notes/my-note.md")
            frontmatter_data: Metadata for the note
            body: Markdown content
            force_update: Whether to force update even if unchanged
            
        Returns:
            Dict with note_id, path, hash, and status
        """
        try:
            # Generate note ID from path
            note_id = self._generate_note_id(path)
            
            # Check if note exists
            blob = self.bucket.blob(path)
            existing_hash = None
            if blob.exists():
                existing_content = blob.download_as_text()
                existing_hash = hashlib.sha1(existing_content.encode("utf-8")).hexdigest()
            
            # Prepare frontmatter with timestamps
            now = datetime.now(timezone.utc)
            if "created_at" not in frontmatter_data:
                frontmatter_data["created_at"] = now.isoformat()
            frontmatter_data["updated_at"] = now.isoformat()
            
            # Create markdown content
            post = frontmatter.Post(body, **frontmatter_data)
            content = frontmatter.dumps(post)
            
            # Calculate new hash
            new_hash = hashlib.sha1(content.encode("utf-8")).hexdigest()
            
            # Skip update if content unchanged and not forced
            if existing_hash == new_hash and not force_update:
                return {
                    "note_id": note_id,
                    "path": f"gs://{self.bucket_name}/{path}",
                    "hash": new_hash,
                    "status": "unchanged",
                    "size": len(content)
                }
            
            # Upload to GCS
            blob.upload_from_string(content, content_type="text/markdown")
            
            return {
                "note_id": note_id,
                "path": f"gs://{self.bucket_name}/{path}",
                "hash": new_hash,
                "status": "updated" if existing_hash else "created",
                "size": len(content),
                "created_at": frontmatter_data.get("created_at"),
                "updated_at": frontmatter_data.get("updated_at")
            }
            
        except Exception as e:
            return {
                "note_id": None,
                "path": f"gs://{self.bucket_name}/{path}",
                "hash": None,
                "status": "error",
                "error": str(e)
            }
    
    def read_note(self, path: str) -> Optional[Dict[str, Any]]:
        """Read a note from GCS."""
        try:
            blob = self.bucket.blob(path)
            if not blob.exists():
                return None
            
            content = blob.download_as_text()
            post = frontmatter.loads(content)
            
            return {
                "note_id": self._generate_note_id(path),
                "path": f"gs://{self.bucket_name}/{path}",
                "frontmatter": post.metadata,
                "body": post.content,
                "hash": hashlib.sha1(content.encode("utf-8")).hexdigest(),
                "size": len(content),
                "etag": blob.etag,
                "updated": blob.updated
            }
        except Exception as e:
            return None
    
    def list_notes(self, prefix: str = "notes/") -> List[Dict[str, Any]]:
        """List all notes in the bucket with given prefix."""
        notes = []
        for blob in self.client.list_blobs(self.bucket_name, prefix=prefix):
            if blob.name.endswith(".md"):
                note_data = self.read_note(blob.name)
                if note_data:
                    notes.append(note_data)
        return notes
    
    def delete_note(self, path: str) -> bool:
        """Delete a note from GCS."""
        try:
            blob = self.bucket.blob(path)
            blob.delete()
            return True
        except Exception:
            return False
    
    def _generate_note_id(self, path: str) -> str:
        """Generate a unique note ID from the path."""
        return hashlib.sha1(path.encode("utf-8")).hexdigest()[:16]

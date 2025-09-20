"""
Local Note Creation Tool for KMS-Google-ADK MVP
Handles creation and updates of markdown notes with frontmatter using local files.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import frontmatter


class LocalNoteTool:
    """Tool for creating and updating markdown notes with structured frontmatter locally."""
    
    def __init__(self, base_path: str = "notes"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
    
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
            path: Local path (e.g., "machine-learning.md")
            frontmatter_data: Metadata for the note
            body: Markdown content
            force_update: Whether to force update even if unchanged
            
        Returns:
            Dict with note_id, path, hash, and status
        """
        try:
            # Generate note ID from path
            note_id = self._generate_note_id(path)
            
            # Full file path
            file_path = self.base_path / path
            
            # Check if note exists
            existing_hash = None
            if file_path.exists():
                existing_content = file_path.read_text(encoding='utf-8')
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
                    "path": str(file_path),
                    "hash": new_hash,
                    "status": "unchanged",
                    "size": len(content)
                }
            
            # Write to file
            file_path.write_text(content, encoding='utf-8')
            
            return {
                "note_id": note_id,
                "path": str(file_path),
                "hash": new_hash,
                "status": "updated" if existing_hash else "created",
                "size": len(content),
                "created_at": frontmatter_data.get("created_at"),
                "updated_at": frontmatter_data.get("updated_at")
            }
            
        except Exception as e:
            return {
                "note_id": None,
                "path": str(self.base_path / path),
                "hash": None,
                "status": "error",
                "error": str(e)
            }
    
    def read_note(self, path: str) -> Optional[Dict[str, Any]]:
        """Read a note from local file."""
        try:
            file_path = self.base_path / path
            if not file_path.exists():
                return None
            
            content = file_path.read_text(encoding='utf-8')
            post = frontmatter.loads(content)
            
            return {
                "note_id": self._generate_note_id(path),
                "path": str(file_path),
                "frontmatter": post.metadata,
                "body": post.content,
                "hash": hashlib.sha1(content.encode("utf-8")).hexdigest(),
                "size": len(content),
                "updated": datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
            }
        except Exception as e:
            return None
    
    def list_notes(self) -> List[Dict[str, Any]]:
        """List all notes in the base directory."""
        notes = []
        for file_path in self.base_path.glob("*.md"):
            note_data = self.read_note(file_path.name)
            if note_data:
                notes.append(note_data)
        return notes
    
    def delete_note(self, path: str) -> bool:
        """Delete a note from local file."""
        try:
            file_path = self.base_path / path
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception:
            return False
    
    def _generate_note_id(self, path: str) -> str:
        """Generate a unique note ID from the path."""
        return hashlib.sha1(path.encode("utf-8")).hexdigest()[:16]

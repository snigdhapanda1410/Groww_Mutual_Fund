"""Session and thread state management with persistent JSON storage."""

from datetime import datetime
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
import uuid

from src.config import config
from src.state.models import Message, Thread, ThreadSummary
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Manages independent conversation threads, message histories, and disk persistence."""

    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = Path(persist_dir or config.session_persist_path)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.threads: Dict[str, Thread] = {}
        self.active_thread_id: Optional[str] = None

        # Load persisted sessions if any exist
        self.load_all_from_disk()

        # Guarantee at least one active thread exists
        if not self.threads:
            initial = self.create_thread(title="New Conversation")
            self.active_thread_id = initial.thread_id

    def create_thread(self, title: str = "New Conversation") -> Thread:
        """Create a new independent conversation thread and set as active."""
        tid = str(uuid.uuid4())[:8]
        now = datetime.utcnow()
        new_thread = Thread(
            thread_id=tid,
            title=title,
            created_at=now,
            updated_at=now,
            messages=[],
        )
        self.threads[tid] = new_thread
        self.active_thread_id = tid
        self.save_to_disk(tid)
        logger.info(f"Created new conversation thread '{tid}' (title='{title}')")
        return new_thread

    def switch_thread(self, thread_id: str) -> Optional[Thread]:
        """Switch active thread focus."""
        if thread_id in self.threads:
            self.active_thread_id = thread_id
            logger.info(f"Switched active thread to '{thread_id}'")
            return self.threads[thread_id]
        logger.warning(f"Thread '{thread_id}' not found; switch failed.")
        return None

    def get_active_thread(self) -> Optional[Thread]:
        """Return the currently active thread object."""
        if self.active_thread_id and self.active_thread_id in self.threads:
            return self.threads[self.active_thread_id]
        if self.threads:
            # Fallback to the first available thread
            first_id = next(iter(self.threads))
            self.active_thread_id = first_id
            return self.threads[first_id]
        return None

    def get_active_history(self) -> List[Message]:
        """Return chronological message history for the active thread."""
        active = self.get_active_thread()
        return active.messages if active else []

    def add_message(
        self,
        role: str,
        content: str,
        citation_url: Optional[str] = None,
        last_updated: Optional[str] = None,
        is_refusal: bool = False,
        thread_id: Optional[str] = None,
    ) -> Message:
        """Append a message to the specified (or active) thread and persist."""
        target_id = thread_id or self.active_thread_id
        if not target_id or target_id not in self.threads:
            created = self.create_thread()
            target_id = created.thread_id

        msg = Message(
            message_id=str(uuid.uuid4())[:8],
            role=role,  # type: ignore[arg-type]
            content=content,
            citation_url=str(citation_url) if citation_url else None,
            last_updated=last_updated,
            timestamp=datetime.utcnow(),
            is_refusal=is_refusal,
        )

        target_thread = self.threads[target_id]
        target_thread.messages.append(msg)
        target_thread.updated_at = datetime.utcnow()

        # Automatically update thread title from first user query if still default
        if role == "user" and target_thread.title == "New Conversation":
            short_title = content.strip().split("\n")[0][:36]
            if len(content.strip()) > 36:
                short_title += "..."
            target_thread.title = short_title

        self.save_to_disk(target_id)
        return msg

    def delete_thread(self, thread_id: str) -> bool:
        """Delete a thread from memory and persistent disk."""
        if thread_id in self.threads:
            del self.threads[thread_id]
            file_path = self.persist_dir / f"{thread_id}.json"
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.error(f"Failed to delete session file '{file_path}': {e}")

            logger.info(f"Deleted thread '{thread_id}'")
            if self.active_thread_id == thread_id:
                self.active_thread_id = next(iter(self.threads)) if self.threads else None
                if not self.active_thread_id:
                    self.create_thread()
            return True
        return False

    def list_threads(self) -> List[ThreadSummary]:
        """Return list of thread summaries ordered by last activity descending."""
        summaries: List[ThreadSummary] = []
        for tid, t in self.threads.items():
            summaries.append(
                ThreadSummary(
                    thread_id=tid,
                    title=t.title,
                    message_count=len(t.messages),
                    last_active=t.updated_at,
                )
            )
        summaries.sort(key=lambda s: s.last_active, reverse=True)
        return summaries

    def save_to_disk(self, thread_id: str) -> None:
        """Serialize thread to JSON file on disk."""
        if thread_id not in self.threads:
            return
        target_thread = self.threads[thread_id]
        file_path = self.persist_dir / f"{thread_id}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(target_thread.model_dump_json(indent=2))
        except Exception as e:
            logger.error(f"Error saving thread '{thread_id}' to '{file_path}': {e}")

    def load_from_disk(self, thread_id: str) -> Optional[Thread]:
        """Load single thread from JSON file."""
        file_path = self.persist_dir / f"{thread_id}.json"
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            thread = Thread.model_validate(data)
            self.threads[thread.thread_id] = thread
            return thread
        except Exception as e:
            logger.error(f"Error loading thread '{thread_id}' from '{file_path}': {e}")
            return None

    def load_all_from_disk(self) -> None:
        """Scan persistence directory and load all valid thread JSON files."""
        for p in self.persist_dir.glob("*.json"):
            tid = p.stem
            self.load_from_disk(tid)

#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from platformdirs import PlatformDirs

from pydantic_ai import ModelMessage
from pydantic_core import to_jsonable_python
from pydantic import TypeAdapter


class SessionManager:
    """Manages conversation session persistence across platform-specific directories."""

    SESSION_FILENAME = "session.json"

    def __init__(self, session_dir: Optional[Path] = None):
        """Initialize session manager.

        Args:
            session_dir: Optional custom session directory. If not provided,
                         uses platform-appropriate default location.
        """
        if session_dir:
            self._session_dir = Path(session_dir)
        else:
            dirs = PlatformDirs("persona", appauthor=False)
            self._session_dir = Path(dirs.user_config_dir) / "sessions"
        self._ensure_session_dir()

    def _ensure_session_dir(self) -> None:
        """Ensure session directory exists."""
        self._session_dir.mkdir(parents=True, exist_ok=True)

    def generate_session_name(self) -> str:
        """Generate a timestamp-based session name.

        Returns:
            Session name in format: session_YYYYMMDD_HHMMSS
        """
        return datetime.now().strftime("session_%Y%m%d_%H%M%S")

    def get_session_path(self, name: str) -> Path:
        """Get the full path for a session file.

        Args:
            name: Session name (without extension)

        Returns:
            Full path to the session JSON file
        """
        return self._session_dir / f"{name}.json"

    def save_session(
        self,
        messages: list[ModelMessage],
        name: Optional[str] = None
    ) -> str:
        """Save conversation messages to a session file.

        Args:
            messages: List of model messages to save
            name: Optional session name. If not provided, generates one.

        Returns:
            The session name used (generated or provided)
        """
        if name is None:
            name = self.generate_session_name()

        session_path = self.get_session_path(name)
        messages_data = to_jsonable_python(messages)

        with open(session_path, 'w', encoding='utf-8') as f:
            json.dump(messages_data, f, indent=2, ensure_ascii=False)

        return name

    def load_session(self, name: str) -> Optional[list[ModelMessage]]:
        """Load conversation messages from a session file.

        Args:
            name: Session name to load

        Returns:
            List of ModelMessage objects, or None if session doesn't exist
        """
        session_path = self.get_session_path(name)

        if not session_path.exists():
            return None

        with open(session_path, 'r', encoding='utf-8') as f:
            messages_data = json.load(f)

        ModelMessagesTypeAdapter = TypeAdapter(list[ModelMessage])
        return ModelMessagesTypeAdapter.validate_python(messages_data)

    def list_sessions(self) -> list[str]:
        """List all saved session names.

        Returns:
            List of session names (without file extension), sorted by modification time
        """
        if not self._session_dir.exists():
            return []

        sessions = []
        for file_path in self._session_dir.glob("*.json"):
            sessions.append((file_path.stem, file_path.stat().st_mtime))

        sessions.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in sessions]

    def delete_session(self, name: str) -> bool:
        """Delete a session file.

        Args:
            name: Session name to delete

        Returns:
            True if session was deleted, False if it didn't exist
        """
        session_path = self.get_session_path(name)

        if session_path.exists():
            session_path.unlink()
            return True
        return False

    def session_exists(self, name: str) -> bool:
        """Check if a session exists.

        Args:
            name: Session name to check

        Returns:
            True if session exists, False otherwise
        """
        return self.get_session_path(name).exists()

    @property
    def session_dir(self) -> Path:
        """Get the session directory path."""
        return self._session_dir

    def save_auto(self, messages: list[ModelMessage]) -> str:
        """Auto-save session with name 'latest'.

        Args:
            messages: List of model messages to save

        Returns:
            The session name used ('latest')
        """
        return self.save_session(messages, name="latest")

    def load_latest(self) -> Optional[list[ModelMessage]]:
        """Load the 'latest' auto-saved session.

        Returns:
            List of ModelMessage objects, or None if no latest session exists
        """
        return self.load_session("latest")

    def get_command_history_path(self, name: str) -> Path:
        """Get path to session's command history file.

        Args:
            name: Session name

        Returns:
            Path to the command history file
        """
        return self._session_dir / f"{name}_commands.txt"

    def load_command_history(self, name: str) -> list[str]:
        """Load command history for a session.

        Args:
            name: Session name

        Returns:
            List of commands from session's history file
        """
        history_file = self.get_command_history_path(name)
        
        if not history_file.exists():
            return []
        
        with open(history_file, 'r') as f:
            return [line.strip() for line in f if line.strip()]

    def merge_command_history(self, name: str, new_commands: list[str]):
        """Merge new commands into session's command history.

        Args:
            name: Session name
            new_commands: List of new commands to merge
        """
        history_file = self.get_command_history_path(name)
        existing = set()
        
        if history_file.exists():
            with open(history_file, 'r') as f:
                existing = set(line.strip() for line in f if line.strip())
        
        with open(history_file, 'a') as f:
            for cmd in new_commands:
                if cmd and cmd not in existing:
                    f.write(cmd + '\n')
                    existing.add(cmd)

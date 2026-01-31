#!/usr/bin/env python3
import os
import tempfile

from persona.sandbox import container


class ContainerManager:
    """Manages Docker container lifecycle with automatic cleanup."""

    def __init__(self, name: str, image: str, mnt_dir: str, 
                 skills_dir: str, env_vars: dict, no_mnt: bool = False):
        self.name = name
        self.image = image
        self.mnt_dir = mnt_dir
        self.skills_dir = skills_dir
        self.env_vars = env_vars
        self.no_mnt = no_mnt
        self._env_file = None

    def _create_env_file(self) -> str | None:
        """Create temporary env file from env_vars dictionary."""
        if not self.env_vars:
            return None
        
        env_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.env',
            delete=False,
            prefix='.sandbox_env_'
        )
        for key, value in self.env_vars.items():
            env_file.write(f"{key}={value}\n")
        env_file_path = env_file.name
        env_file.close()
        os.chmod(env_file_path, 0o600)
        return env_file_path

    def _cleanup_env_file(self):
        """Remove temporary env file if it exists."""
        if self._env_file and os.path.exists(self._env_file):
            os.unlink(self._env_file)
            self._env_file = None

    def start(self) -> bool:
        """Start the container with configured parameters."""
        self._env_file = self._create_env_file()
        result = container.start_container(
            self.name,
            self.image,
            self.mnt_dir,
            self.skills_dir,
            self._env_file,
            self.no_mnt
        )
        if not result:
            self._cleanup_env_file()
        return result

    def stop(self) -> bool:
        """Stop the container and clean up resources."""
        self._cleanup_env_file()
        return container.stop_container(self.name)

    def __enter__(self):
        """Context manager entry - start container."""
        if not self.start():
            raise RuntimeError(f"Failed to start container {self.name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stop container."""
        self.stop()
        return False

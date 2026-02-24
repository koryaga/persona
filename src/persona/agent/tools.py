#!/usr/bin/env python3
import os
import subprocess
import tempfile
from pathlib import Path

import aiofiles

from persona.config import env


def create_tools(container_name: str, skills_dir):
    """Create agent tools with proper closure over container_name and skills_dir."""

    async def run_cmd(cmd: str) -> str:
        """Execute a bash command in the Ubuntu sandbox container.

        Args:
            cmd: The bash command to execute (e.g., "ls -la")
        """

        try:
            result = subprocess.run(
                ["docker", "exec", container_name, "bash", "-c", cmd],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR: {result.stderr}"
            
            return output
        except subprocess.TimeoutExpired:
            return "Command timed out"
        except subprocess.SubprocessError as e:
            return f"Error executing command: {str(e)}"
        except KeyboardInterrupt:
            return "Command interrupted by user"
        except Exception as e:
            return f"Unexpected error: {str(e)}"
    
    async def save_text_file(path: str, file_body: str) -> str:
        """Write text content to a file, script at an arbitrary path in the sandbox container.

        Args:
            path: Absolute path where to write the file (e.g., "/tmp/output.txt")
            file_body: Complete content to write to the file
        """
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='', delete=False) as tmp:
                tmp.write(file_body)
                tmp_path = tmp.name
            
            result = subprocess.run(
                ["docker", "cp", tmp_path, f"{container_name}:{path}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            os.unlink(tmp_path)
            
            if result.returncode == 0:
                return f"Successfully wrote {len(file_body)} bytes to {path}"
            else:
                return f"Error writing file: {result.stderr}"
        except Exception as e:
            return f"Error writing file: {str(e)}"
    
    async def load_skill(skill: str) -> str:
        """Load a skill definition into the agent's context.

        Args:
            skill: Name of the skill directory to load (e.g. "web-search", "skill-creator")
        """
        async with aiofiles.open(skills_dir / skill / "SKILL.md", "r") as f:
            content = await f.read()
            return (
                f"Reading: {skill}\n"
                f"Base directory: /skills\n"
                f"{content}\n"
                f"Skill read: {skill}"
            )
    
    return run_cmd, save_text_file, load_skill

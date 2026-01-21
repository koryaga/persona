#!/usr/bin/env python3
import argparse
import asyncio
import atexit
import datetime
import glob
import importlib.resources as resources
import os
import re
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import aiofiles
import logfire
from dotenv import load_dotenv
from pydantic_ai import Agent, ModelSettings
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from persona import __version__


def is_debug() -> bool:
    return os.getenv('DEBUG', '').lower() in ('true', '1', 'yes')


def _signal_handler(signum, frame):
    """Handle termination signals to ensure clean container shutdown."""
    if 'container_name' in globals() and container_name:
        stop_container(container_name)
    sys.exit(0)


def configure_logfire() -> None:
    """Configure logfire for debug mode instrumentation."""
    if is_debug():
        logfire.configure(send_to_logfire=False)
        logfire.instrument_pydantic_ai()
        logfire.instrument_httpx(capture_all=True)


def get_skills_dir() -> Path:
    """Find skills directory - bundled in package or from project root."""
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', '')  # type: ignore
        return Path(meipass) / 'skills'
    
    try:
        pkg_skills = resources.files('persona')
        if pkg_skills.is_dir():
            skills_path = pkg_skills / 'skills'
            if skills_path.is_dir():
                return Path(str(skills_path))
    except (TypeError, ModuleNotFoundError, AttributeError, FileNotFoundError):
        pass
    
    return Path(__file__).parent.parent.parent / 'skills'


def get_instructions_path() -> Path:
    """Find instructions.md - bundled in package or from project root."""
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', '')  # type: ignore
        return Path(meipass) / 'instructions.md'
    
    try:
        pkg_instructions = resources.files('persona')
        if pkg_instructions.is_file():
            instructions_path = pkg_instructions / 'instructions.md'
            if instructions_path.is_file():
                return Path(str(instructions_path))
    except (TypeError, ModuleNotFoundError, AttributeError, FileNotFoundError):
        pass
    
    return Path(__file__).parent.parent.parent / 'instructions.md'


def load_config() -> None:
    """Load configuration from environment with priority order."""
    load_dotenv(override=False)

    user_config = Path(os.path.expanduser('~/.persona/.env'))
    if user_config.exists():
        load_dotenv(user_config, override=True)

    if Path('.env').exists():
        load_dotenv('.env', override=True)


def get_sandbox_env_vars() -> dict[str, str]:
    """Read allowed environment variables from .env.sandbox file."""
    sandbox_env = Path(__file__).parent.parent.parent / '.env.sandbox'
    if not sandbox_env.exists():
        return {}

    env_vars = {}
    for line in sandbox_env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            if key:
                env_vars[key] = value
    return env_vars


def find_and_parse_skills(skills_dir: Path):
    """Find all SKILL.md files and parse them into XML."""
    
    def parse_skill(file_path: Path, skills_dir: Path):
        with open(file_path, 'r') as file:
            content = file.read()
        
        match = re.search(r'^---$(.*?)^---$', content, re.DOTALL | re.MULTILINE)
        if match:
            metadata_block = match.group(1).strip().split('\n')
            metadata = dict(line.split(': ', 1) for line in metadata_block)
            
            relative_path = file_path.relative_to(skills_dir)
            container_path = f"/skills/{relative_path}"
            
            xml_output = (
                '<skill>\n'
                f'<name>{metadata["name"]}</name>\n'
                f'<description>{metadata["description"]}</description>\n'
                f'<location>{container_path}</location>\n'
                '</skill>'
            )
            return xml_output
        else:
            raise ValueError("Metadata section not found.")
    
    skills_xml = []
    skill_files = list(skills_dir.rglob("SKILL.md"))
    
    for skill_file in skill_files:
        try:
            xml_content = parse_skill(skill_file, skills_dir)
            skills_xml.append(xml_content)
        except Exception as e:
            print(f"Error parsing {skill_file}: {e}")
    
    return '\n'.join(skills_xml)


def start_container(container_name: str, image_name: str, mnt_dir: str, skills_dir: str, env_file: str | None = None, no_mnt: bool = False) -> bool:
    """Start a Docker container with the specified parameters."""
    try:
        mnt_dir = os.path.abspath(os.path.expanduser(mnt_dir))
        skills_dir = os.path.abspath(os.path.expanduser(skills_dir))

        cmd = ["docker", "run", "-d", "--rm"]

        if env_file and os.path.isfile(env_file):
            cmd.extend(["--env-file", env_file])

        if not no_mnt and os.path.isdir(mnt_dir):
            cmd.extend(["-v", f"{mnt_dir}:/mnt"])
        if os.path.isdir(skills_dir):
            cmd.extend(["-v", f"{skills_dir}:/skills"])
        
        cmd.extend([
            "--name", container_name,
            image_name,
            "sleep", "infinity"
        ])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            if is_debug():
                print(f"Container {container_name} started successfully with ID: {result.stdout.strip()}")
            return True
        else:
            if is_debug():
                print(f"Failed to start container {container_name}: {result.stderr}")
            return False
    
    except subprocess.TimeoutExpired:
        if is_debug():
            print("Command timed out")
        return False
    except Exception as e:
        if is_debug():
            print(f"Error starting container: {str(e)}")
        return False


def stop_container(container_name: str) -> bool:
    """Stop a Docker container with the specified name."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-q", "-f", f"name={container_name}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            stop_result = subprocess.run(
                ["docker", "stop", container_name],
                capture_output=True,
                text=True,
                timeout=20
            )
            
            if stop_result.returncode == 0:
                if is_debug():
                    print(f"Container {container_name} stopped successfully")
                return True
            else:
                if is_debug():
                    print(f"Failed to stop container {container_name}: {stop_result.stderr}")
                return False
        else:
            if is_debug():
                print(f"Container {container_name} not found or not running")
            return True
    
    except Exception as e:
        if is_debug():
            print(f"Error stopping container: {str(e)}")
        return False


def create_agent(skills_dir: Path, model_settings: Optional[dict] = None):
    """Create and configure the agent."""
    instructions_path = get_instructions_path()
    with open(instructions_path, 'r') as f:
        system_prompt = f.read()
    
    openai_model = os.getenv('OPENAI_MODEL', 'cogito:14b')
    openai_api_key = os.getenv('OPENAI_API_KEY', 'ollama')
    openai_api_base = os.getenv('OPENAI_API_BASE', 'http://localhost:11434/v1')
    
    if model_settings:
        model = OpenAIChatModel(
            openai_model,
            provider=OpenAIProvider(
                base_url=openai_api_base,
                api_key=openai_api_key,
            ),
            settings=ModelSettings(**model_settings),
        )
    else:
        model = OpenAIChatModel(
            openai_model,
            provider=OpenAIProvider(
                base_url=openai_api_base,
                api_key=openai_api_key,
            ),
            settings=ModelSettings(temperature=0, top_p=0),
        )
    
    def get_instructions() -> str:
        return (
            f"{system_prompt}"
            f"Current date and time: {datetime.datetime.now().isoformat()}"
            """ When users ask you to perform tasks, check if any of the available skills below can help complete the task more effectively.

            <skills_instructions>
            How to use skills:
            - Invoke skills using this tool with the skill name only: `load_skill` <skill_name>
            - When you invoke a skill, you will see `Reading: <skill_name>`
            - The skill's prompt will expand and provide detailed instructions
            - Base directory provided in output for resolving bundled resources

            Usage notes:
            - Only use skills listed in <available_skills> below
            - Do not invoke a skill that is already loaded in your context
            </skills_instructions>"""
            "<available_skills>"
            f"{find_and_parse_skills(skills_dir)}"
            "</available_skills>"
        )
    
    agent = Agent(
        model,
        retries=5,
        instructions=get_instructions,
    )
    
    return agent


def create_tools(container_name: str, skills_dir: Path):
    """Create agent tools with proper closure over container_name and skills_dir."""

    async def run_cmd(cmd: str) -> str:
        """Execute a bash command in the Ubuntu sandbox container.

        Args:
            cmd: The bash command to execute (e.g., "ls -la")
        """
        print(f"\033[38;5;208m[CMD] {cmd}\033[0m")
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
        except Exception as e:
            return f"Unexpected error: {str(e)}"
    
    async def save_text_file(path: str, file_body: str) -> str:
        """Write text content to a file at an arbitrary path in the sandbox container.

        Args:
            path: Absolute path where to write the file (e.g., "/tmp/output.txt")
            file_body: Complete content to write to the file
        """
        print(f"\033[94m[FILE] {path}\033[0m")
        
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
        print(f"\033[93m[SKILL] {skill}\033[0m")
        
        async with aiofiles.open(skills_dir / skill / "SKILL.md", "r") as f:
            content = await f.read()
            return (
                f"Reading: {skill}\n"
                f"Base directory: /skills\n"
                f"{content}\n"
                f"Skill read: {skill}"
            )
    
    return run_cmd, save_text_file, load_skill


async def _main():
    """Main entry point for the persona CLI."""
    load_config()
    configure_logfire()
    
    parser = argparse.ArgumentParser(
        prog="persona",
        description="A universal AI agent CLI with Anthropic-style skills"
    )
    parser.add_argument("--version", action="version", version=f"persona {__version__}")
    parser.add_argument(
        "--mnt-dir",
        dest="mnt_dir",
        help="Local directory to mount into container at /mnt",
        default="."
    )
    parser.add_argument(
        "--no-mnt",
        dest="no_mnt",
        action="store_true",
        help="Don't mount any host directory at /mnt",
        default=False
    )
    parser.add_argument(
        "--skills-dir",
        dest="skills_dir",
        help="Local skills directory to mount into container",
        default=None
    )
    parser.add_argument(
        "--container-image",
        dest="container_image",
        help="Docker image to use for sandbox",
        default=None
    )
    args, remaining = parser.parse_known_args()
    
    skills_dir = args.skills_dir if args.skills_dir else str(get_skills_dir())
    
    sandbox_image = args.container_image or os.getenv(
        'SANDBOX_CONTAINER_IMAGE',
        "ubuntu.sandbox"
    )
    container_name_base = os.getenv('SANDBOX_CONTAINER_NAME', "sandbox")
    container_name = f"{container_name_base}-{os.getpid()}"

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    sandbox_env_file = None
    sandbox_env_vars = get_sandbox_env_vars()
    if sandbox_env_vars:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False, prefix='.sandbox_env_') as f:
            for key, value in sandbox_env_vars.items():
                f.write(f"{key}={value}\n")
            sandbox_env_file = f.name
        os.chmod(sandbox_env_file, 0o600)
        atexit.register(os.unlink, sandbox_env_file)

    agent = create_agent(Path(skills_dir))
    run_cmd, save_text_file, load_skill = create_tools(container_name, Path(skills_dir))
    
    agent.tool_plain(run_cmd)
    agent.tool_plain(save_text_file)
    agent.tool_plain(load_skill)
    
    if not start_container(container_name, sandbox_image, args.mnt_dir, skills_dir, sandbox_env_file, args.no_mnt):
        return False
    
    atexit.register(stop_container, container_name)
    
    async with agent:
        await agent.to_cli(prog_name="persona")
    
    return True


def main():
    """Synchronous entry point for CLI scripts."""
    return asyncio.run(_main())


if __name__ == "__main__":
    main()

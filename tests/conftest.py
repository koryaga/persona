import pytest
import subprocess
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv(override=False)

user_config = Path(os.path.expanduser('~/.persona/.env'))
if user_config.exists():
    load_dotenv(user_config, override=False)

if Path('.env').exists():
    load_dotenv('.env', override=False)

SANDBOX_CONTAINER_NAME_BASE = os.environ.get('SANDBOX_CONTAINER_NAME', 'sandbox')
SANDBOX_CONTAINER_NAME = f"{SANDBOX_CONTAINER_NAME_BASE}-{os.getpid()}"


def pytest_configure(config):
    """Print LLM configuration before test suite runs."""
    print("\n" + "=" * 60)
    print("TEST SUITE CONFIGURATION")
    print("=" * 60)
    
    openai_model = os.getenv('OPENAI_MODEL')
    openai_api_base = os.getenv('OPENAI_API_BASE')
    openai_api_key = os.getenv('OPENAI_API_KEY')
    sandbox_image = os.getenv('SANDBOX_CONTAINER_IMAGE')
    
    # Mask API key for security
    if openai_api_key and len(openai_api_key) > 8:
        masked_key = f"{openai_api_key[:4]}...{openai_api_key[-4:]}"
    elif openai_api_key:
        masked_key = f"{openai_api_key[:4]}..."
    else:
        masked_key = "NOT SET (will use cli.py fallback)"
    
    print(f"  LLM Model:       {openai_model or 'NOT SET (will use cli.py fallback)'}")
    print(f"  API Base:        {openai_api_base or 'NOT SET (will use cli.py fallback)'}")
    print(f"  API Key:         {masked_key}")
    print(f"  Sandbox Image:    {sandbox_image or 'NOT SET (will use ubuntu.sandbox)'}")
    
    # Show .env file status
    project_env = Path('.env').exists()
    user_env = Path(os.path.expanduser('~/.persona/.env')).exists()
    
    print(f"  Project .env:    {'YES' if project_env else 'NO'}")
    print(f"  User .env:       {'YES' if user_env else 'NO'}")
    print("=" * 60 + "\n")


def ensure_container():
    """Ensure container is running, create if needed."""
    result = subprocess.run(
        ["docker", "ps", "-q", "-f", f"name={SANDBOX_CONTAINER_NAME}"],
        capture_output=True,
        text=True,
        timeout=10
    )

    if result.stdout.strip():
        print(f"[SETUP] Container {SANDBOX_CONTAINER_NAME} already running")
        return

    container_image = os.getenv('SANDBOX_CONTAINER_IMAGE', 'ubuntu.sandbox')
    cmd = ["docker", "run", "-d", "--rm", "--name", SANDBOX_CONTAINER_NAME, container_image, "sleep", "infinity"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        print(f"[SETUP] Container {SANDBOX_CONTAINER_NAME} started")
    else:
        print(f"[SETUP] Failed to start container: {result.stderr}")


def cleanup_container():
    """Stop and remove the container."""
    subprocess.run(
        ["docker", "stop", SANDBOX_CONTAINER_NAME],
        capture_output=True,
        text=True,
        timeout=20
    )
    print(f"[TEARDOWN] Container {SANDBOX_CONTAINER_NAME} stopped")


@pytest.fixture(scope="session")
def docker_sandbox():
    """Start Docker sandbox container once per test session."""
    ensure_container()
    yield SANDBOX_CONTAINER_NAME
    cleanup_container()


@pytest.fixture
def mnt_directory():
    """Path to mount directory - now using /tmp inside container."""
    return "/tmp"


@pytest.fixture
def skills_directory():
    """Path to skills directory."""
    return os.path.abspath(os.path.expanduser("skills"))

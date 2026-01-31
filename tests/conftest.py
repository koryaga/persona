import pytest
import subprocess
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SANDBOX_CONTAINER_NAME_BASE = os.environ.get('SANDBOX_CONTAINER_NAME', 'sandbox')
SANDBOX_CONTAINER_NAME = f"{SANDBOX_CONTAINER_NAME_BASE}-{os.getpid()}"


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

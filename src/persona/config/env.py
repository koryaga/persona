#!/usr/bin/env python3
import os
from pathlib import Path

import logfire
from dotenv import load_dotenv


def is_debug() -> bool:
    return os.getenv('DEBUG', '').lower() in ('true', '1', 'yes')


def configure_logfire() -> None:
    """Configure logfire for debug mode instrumentation."""
    if is_debug():
        logfire.configure(send_to_logfire=False)
        logfire.instrument_pydantic_ai()
        logfire.instrument_httpx(capture_all=True)


def load_config() -> None:
    """Load configuration from environment with priority order."""
    load_dotenv(override=False)

    user_config = Path(os.path.expanduser('~/.persona/.env'))
    if user_config.exists():
        load_dotenv(user_config, override=False)

    if Path('.env').exists():
        load_dotenv('.env', override=False)


def get_sandbox_env_vars(sandbox_env_path: str | None = None) -> dict[str, str]:
    """Read allowed environment variables from .env.sandbox file.

    Args:
        sandbox_env_path: Optional path to .env.sandbox file. If not provided,
                         defaults to .env.sandbox in project root.
    """
    if sandbox_env_path:
        sandbox_env = Path(sandbox_env_path)
    else:
        sandbox_env = Path(__file__).parent.parent.parent.parent / '.env.sandbox'
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

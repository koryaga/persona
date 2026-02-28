#!/usr/bin/env python3
import os
from pathlib import Path

import logfire
from dotenv import load_dotenv


def is_debug() -> bool:
    return os.getenv('DEBUG', '').lower() in ('true', '1', 'yes')


def is_logfire() -> bool:
    """Check if logfire is enabled via environment variable."""
    return os.getenv('LOGFIRE', '').lower() in ('true', '1', 'yes')


def configure_logfire() -> None:
    """Configure logfire for debug mode instrumentation.

    When OTEL_EXPORTER_OTLP_ENDPOINT is set, exports to that endpoint.
    Otherwise, disables sending to logfire backend.
    """
    if not is_debug() and not is_logfire():
        return

    otlp_endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT')

    config = {
        'send_to_logfire': False,
        'service_name': 'persona',
        'inspect_arguments': False,
    }

    if otlp_endpoint:
        config['environment'] = 'development'

    if is_logfire():
        config['send_to_logfire'] = 'if-token-present'

    logfire.configure(**config)

    if is_debug() or is_logfire():
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

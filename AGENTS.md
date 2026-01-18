# AGENTS.md

## Project Overview

This is a universal AI agent CLI tool (`persona`) built with Pydantic-AI that supports Anthropic-style skills. It runs from CLI and uses Docker sandbox containers for safe command execution. The project uses Python 3.13+, uv for dependency management, and follows async-first patterns for I/O operations.

## Setup Commands

- Sync dependencies: `uv sync`
- Activate venv: `source .venv/bin/activate`
- Add Python package: `uv add <package>`
- Remove Python package: `uv remove <package>`
- Build sandbox image: `docker build -t ubuntu.sandbox .`

## Build/Lint/Test Commands

- Run application: `persona` (after `uv sync && source .venv/bin/activate`)
- Run with custom skills dir: `persona --skills-dir ./skills`
- Run without mounting host directory: `persona --no-mnt`
- Run with custom mount directory: `persona --mnt-dir /path/to/dir`
- Syntax check Python files: `find . -name "*.py" -exec python3 -m py_compile {} \;`
- Run skill tests: `python3 -m unittest discover -s skills -p "*_test.py" -v`
- Run E2E tests: `pytest tests/test_cli_eval.py -v`
- Run specific E2E test: `pytest tests/test_cli_eval.py::TestAgentCLIExpectedOutput::test_skill_creator -v`
- Enable DEBUG mode: `DEBUG=true persona ...`
- Add linting: `uv add ruff && ruff check .`
- Add type checking: `uv add pyright && pyright .`

## Project Structure

```
/Users/skoryaga/src/persona
├── src/persona/           # Package source
│   ├── __init__.py       # Package with version
│   ├── cli.py            # CLI entry point
│   └── py.typed          # PEP 561 type marker
├── pyproject.toml        # Project metadata and dependencies
├── AGENTS.md             # This file for agent instructions
├── instructions.md       # System prompt for the agent
├── skills/               # Skill definitions (Anthropic-style)
│   ├── analyzing-logs/
│   ├── candidate-assessment/
│   ├── pdf/
│   ├── planning-with-files/
│   ├── skill-creator/
│   ├── skillsmp-search/
│   └── web-search/
├── mnt/                  # Default mount directory for user files
│   └── .gitignore        # Git ignore for mount directory
├── .env.example          # Configuration template
├── .env.sandbox.example  # Sandbox environment variables template
├── Dockerfile            # Sandbox container definition
└── tests/                # E2E tests with pydantic-evals
    ├── conftest.py       # Pytest fixtures
    └── test_cli_eval.py  # CLI evaluation tests
```

## Code Style Guidelines

### Imports

- Group imports in this order: standard library, third-party, local application
- Use `async with` for async file operations via `aiofiles`
- Import only what is needed; avoid wildcard imports
- Sort imports alphabetically within groups
- One import per line; no comma-separated imports

### Formatting

- Use 4 spaces for indentation (no tabs)
- Keep lines under 120 characters where reasonable
- Use blank lines to separate logical sections within functions
- No comments unless explaining non-obvious logic (per project convention)
- Use trailing commas in multi-line calls and data structures
- Opening braces on same line for function calls and control statements
- Use black-style formatting for multi-line expressions

### Types

- Use type hints for function parameters and return values
- Use `async def` for functions that perform async I/O operations
- Use Pydantic models for structured data when appropriate
- Prefer `X | Y` union syntax (Python 3.10+)
- Use `X | None` rather than `Optional[X]`
- Use `Literal` for enum-like string constants
- Use `TypedDict` or Pydantic models for complex dictionary structures

### Naming Conventions

- `snake_case` for variables, functions, and methods
- `PascalCase` for classes and types
- `UPPER_SNAKE_CASE` for constants
- Prefix private variables with underscore: `_private_var`
- Descriptive names preferred over abbreviations (e.g., `container_name` not `cname`)
- Use single-letter variables only for trivial counters or lambda functions
- Prefix async functions with meaningful verbs: `fetch_data()`, `parse_file()`

### Error Handling

- Use try/except blocks with specific exception types
- Return `False` or error strings from functions rather than raising for expected failures
- Log errors with clear messages including the operation attempted
- Always handle subprocess errors explicitly (TimeoutExpired, SubprocessError)
- Use custom exception classes for domain-specific errors
- Never suppress exceptions without explicit logging
- Clean up resources in finally blocks or use context managers

### Async Patterns

- Use `async def` for I/O-bound operations (file, network, subprocess)
- Use `await` with async libraries (aiofiles, async HTTP clients)
- Wrap blocking operations (subprocess, file I/O) in async functions for agent tools
- Return results directly; avoid unnecessary wrapping of async calls
- Use `asyncio.gather()` for concurrent async operations when appropriate
- Prefer async context managers (`async with`) over sync versions for I/O

### Docker/Sandbox Integration

- Always expand user paths: `os.path.abspath(os.path.expanduser(path))`
- Check directory existence before mounting volumes: `os.path.isdir(path)`
- Use descriptive container names with environment variable fallbacks
- Register cleanup functions with `atexit` for graceful shutdown
- Set reasonable timeouts on all container operations (30s default)
- Handle Docker daemon not running gracefully with helpful error messages
- Use `docker exec` for running commands inside the sandbox container
- Enable DEBUG mode for container lifecycle messages: `DEBUG=true persona ...`
- Default mount directory is current directory (`.`); use `--no-mnt` to disable mounting
- Sandbox environment variables can be set in `.env.sandbox` file

### Project-Specific Patterns

- Tools for the agent are decorated with `@agent.tool_plain` (not `@agent.tool`)
- Use `subprocess.run` with `capture_output=True` and `text=True` for shell commands
- Set timeouts on all subprocess calls (30s default, 10-20s for quick operations)
- Mount points: `/mnt` for user files, `/skills` for skill definitions, `/tmp` for temp files
- Use `tempfile` module for secure temporary file handling
- Agent tools should be async and return strings or structured data
- Skills are defined in `skills/{skill_name}/SKILL.md` with YAML frontmatter
- Skills can include `examples.md` and `reference.md` for detailed documentation
- Some skills include helper scripts in `scripts/` directory and API references in `references/`

### General

- Keep functions focused and under 50 lines when possible
- Use early returns to reduce nesting
- Prefer returning structured data (dicts, lists) over complex objects
- Constants at module level with environment variable fallbacks
- Use f-strings for string formatting (Python 3.13+)
- Document public APIs with docstrings; private methods may omit
- Use dataclasses for simple data containers; Pydantic models for validation
- Avoid deep nesting; extract helper functions when needed

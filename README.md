# Persona — universal cli AI agent

## Purpose

Persona is a lightweight CLI AI agent that:
- performs general user tasks, like document processing, internet search, and data manipulation
- supports [Anthropic skills](https://agentskills.io/home) from the `skills/` directory to satisfy user requests

## Key features

- exchanges files with the user via the [mnt](./mnt) folder
- Runs shell commands and executes generated Python code inside a disposable Docker sandbox container.
- Loads and exposes skill files to the agent.
- Starts/stops the sandbox container programmatically from `main.py`.

## Quick start

Prerequisites: Docker and Python 3.13+.

1. Create and activate the virtualenv:

```bash
uv venv
source .venv/bin/activate
uv sync
```

2. Build the sandbox image (the project uses `ubuntu.sandbox` by default):

```bash
docker build -t ubuntu.sandbox .
```

3. Run the agent:

```bash
python3 main.py
```
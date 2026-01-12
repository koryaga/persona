# Persona — universal AI agent

## Purpose

Persona is a lightweight AI agent running from cli that:
- performs general user tasks, like document processing, internet search and data manipulation
- supports [Anthropic skills](https://agentskills.io/home) to satisfy user requests

## Key features

- Runs shell commands and executes generated Python code inside a disposable Docker Ubuntu sandbox container
- Loads and exposes skill to the agent (see `--skills-dir`)
- Exchanges files with the user via the folder (see `--mnt-dir`)

## Prerequisites

- Docker
- Python 3.13+
- uv package manager

## Installation

```bash
git clone <repo-url>
cd persona
uv sync
source .venv/bin/activate
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your API keys and settings
```

### Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_MODEL` | Model to use | `cogito:14b` |
| `OPENAI_API_KEY` | API key | `ollama` |
| `OPENAI_API_BASE` | API base URL | `http://localhost:11434/v1` |
| `SANDBOX_CONTAINER_IMAGE` | Docker image | `ubuntu.sandbox` |
| `SANDBOX_CONTAINER_NAME` | Container name prefix | `sandbox` |

## Build sandbox image

```bash
docker build -t ubuntu.sandbox .
```

## Usage

```bash
persona [--mnt-dir PATH] [--skills-dir PATH] [--container-image IMAGE]
```

### Options

- `--mnt-dir`: Host directory to mount at `/mnt` inside sandbox (default: `mnt`)
- `--skills-dir`: Host directory to mount at `/skills` inside sandbox (default: `skills`)
- `--container-image`: Docker image to use for sandbox

### Examples

```bash
# Run with default mounts
persona

# Custom mount directories
persona --mnt-dir /home/user/project --skills-dir /home/user/persona/skills

# Different Docker image
persona --container-image my-custom-sandbox
```

## Skills

Persona supports [Anthropic-style skills](https://agentskills.io/home). Skills are loaded from the `--skills-dir` (default: `skills/`).

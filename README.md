# Persona — universal AI agent

## Purpose

Persona is a simple AI agent running from cli that:
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
git clone https://github.com/koryaga/persona.git
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


### Sandbox environment variables

Create `.env.sandbox` to pass environment variables into the sandbox container. Variables set in this file will be available inside the Docker container for skills to use.

Example `.env.sandbox`:
```bash
TRAVILY_TOKEN=your-tavily-api-token
SKILLSMP_API_KEY=your-skillsmp-api-key
```

The `web-search` skill uses Tavily API when `TRAVILY_TOKEN` is set. Without the token, it defaults to DuckDuckGo.
The `skillsmp-search` skill uses SkillsMP API when `SKILLSMP_API_KEY` is set.

## Build sandbox image

```bash
docker build -t ubuntu.sandbox .
```

## Usage

```bash
persona [--mnt-dir PATH] [--skills-dir PATH]
```

### Options

- `--mnt-dir`: Host directory to mount inside sandbox (default: `.`)
- `--no-mnt`: Don't mount any host directory at `/mnt`
- `--skills-dir`: Host directory to mount at `/skills` inside sandbox (default: `skills`)
- `--container-image`: Docker image to use for sandbox

### Examples

```bash
# Run with default mounts (current directory)
persona

# No mount at all
persona --no-mnt

# Custom user directory
persona --mnt-dir /home/user/project

# Custom user directory and skill folder 
persona --mnt-dir /home/user/project --skills-dir /home/user/persona/skills

```

## Skills {#skills}

Persona supports [Anthropic-style skills](https://agentskills.io/home). Skills are loaded from the `--skills-dir` (default: `skills/`).

Provided OOB:
- [*skill-creator*](https://github.com/anthropics/skills/tree/main/skills/skill-creator) - Create new skills or update existing ones
- [*web-search*](./skills/web-search/SKILL.md) - Web search with DuckDuckGo (default) or Tavily (with `TRAVILY_TOKEN`). Get Tavily token at: https://app.tavily.com/home
- [*skillsmp-search*](./skills/skillsmp-search/SKILL.md) - Search AI skills from SkillsMP marketplace (requires `SKILLSMP_API_KEY` in `.env.sandbox`). Get API key at: https://skillsmp.com/docs/api

More skills on [Agent Skills Marketplace](https://skillsmp.com/)

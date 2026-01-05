# Persona — universal AI agent

## Purpose

Persona is a lightweight AI agent running from cli that:
- performs general user tasks, like document processing, internet search and data manipulation
- supports [Anthropic skills](https://agentskills.io/home) to satisfy user requests

## Key features

- Runs shell commands and executes generated Python code inside a disposable Docker Ubuntu sandbox container
- Loads and exposes skill to the agent (see `--skills-dir`)
- Exchanges files with the user via the folder (see `--mnt-dir`)

## Quick start

Prerequisites: Docker and Python 3.13+.

1. Set up environment:

Below are defaults for [openrouter](https://openrouter.ai/). Any OPENAI compatible, including local ollama, is supported:
```bash
OPENAI_API_KEY=your-api-key
OPENAI_API_BASE=https://openrouter.ai/api/v
OPENAI_MODEL=nex-agi/deepseek-v3.1-nex-n1:free
```

2. Create and activate the virtualenv:

```bash
uv venv
source .venv/bin/activate
uv sync
```

3. Build the sandbox image (the project uses `ubuntu.sandbox` by default):
```bash
docker build -t ubuntu.sandbox .
```
*Optional*. You may specify general `ubuntu` container name or your own image using `SANDBOX_CONTAINER_IMAGE` env.

4. Specify [search API](https://github.com/koryaga/Persona/blob/main/instructions.md?plain=1#L9) in a _curl format_
- Example for [travily](https://www.tavily.com/):
```bash
   curl -X POST https://api.tavily.com/search -H 'Content-Type: application/json' -H 'Authorization: Bearer _TRAVILY_TOKEN_' -d '{
    "query": "<QUERY>",
    "include_answer": "advanced"
    }'
```
*Optional*. Free duckduckgo API search is used by default.

5. Run the agent:

Usage: `python3 main.py [--mnt-dir PATH] [--skills-dir PATH]`

- `--mnt-dir`: Host directory to mount at `/mnt` inside the sandbox (default:  `mnt` folder in current directory). The directory is only mounted if it exists on the host.
- `--skills-dir`: Host directory to mount at `/skills` inside the sandbox (default:  `skills` folder in current directory). The directory is only mounted if it exists on the host.

Examples:
```bash
# start with default  mounts (only mounted if dirs exist)
python3 main.py
```
```bash
# or specify custom absolute/relative host paths for mounts
python3 main.py --mnt-dir /home/user/project/ --skills-dir /home/user/persona/skills
python3 main.py --mnt-dir ./mnt --skills-dir ./skills
```

# Persona — universal AI agent

## Purpose

Persona is an AI agent CLI that:
- Performs tasks like document processing, internet search, and data manipulation
- Runs shell commands and generated code in an isolated Docker sandbox
- Supports [Anthropic-style skills](https://agentskills.io/home) for specialized workflows
- Provides session persistence and slash commands in an interactive REPL

## Quick Start

```bash
# Install
git clone https://github.com/koryaga/persona.git
cd persona
uv sync && source .venv/bin/activate

# Build sandbox
docker build -t ubuntu.sandbox .

# Configure
cp .env.example .env

# Run (interactive REPL)
persona

# Or single prompt
persona "your task here"
```

## Interactive Mode

The REPL provides a rich command-line interface with persistent sessions:

```
persona [latest] [0 tokens] [/Users/skoryaga/src/persona] [./skills] [MCP: Disabled] [cogito:14b] ➤
```

**Slash commands:**

| Command | Description |
|---------|-------------|
| `/save [name]` | Save current session |
| `/load <name>` | Load a saved session |
| `/list` | List all sessions |
| `/new` | Start new session |
| `/clear` | Clear terminal |
| `/help` | Show commands |

**Keyboard shortcuts:** `Ctrl+C` interrupt agent, `Ctrl+D` or `/exit` exit, `Ctrl+Z` suspend to background

### Interactive examples

```
# Ask a question
persona [latest] ➤ what is the weather today?

# Work with files - your mounted directory is at /mnt
persona [latest] ➤ read the README.md file from /mnt and summarize it

# Use a skill
persona [latest] ➤ /load my-project
persona [my-project] ➤ @web-search find latest AI news

# Save session for later
persona [latest] ➤ /save my-research
Session saved: my-research

# Switch between sessions
persona [latest] ➤ /load my-project
Loaded session: my-project
persona [my-project] ➤

# Start fresh
persona [my-project] ➤ /new
Started new session.
persona [latest] ➤
```

## Non-Interactive Mode

```bash
persona "list files in /tmp"
persona --stream -p "your prompt"
```

## Sessions

Conversations auto-save to `latest` after each response. Sessions are stored in your platform config directory (`~/.config/persona/sessions/` on macOS) and persist across restarts.

## Configuration

### Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_MODEL` | Model to use | `cogito:14b` |
| `OPENAI_API_KEY` | API key | `ollama` |
| `OPENAI_API_BASE` | API base URL | `http://localhost:11434/v1` |
| `DEBUG` | Show trace in console | `true OR false` |
| `LOGFIRE` | Post to Pydantic Logfire | `true OR false` |
| `MCP_ENABLED` | Enable MCP servers | `true OR false` |

### Sandbox environment variables

Create `.env.sandbox` to pass variables into the Docker container:

```bash
TRAVILY_TOKEN=your-tavily-token
SKILLSMP_API_KEY=your-skillsmp-key
```

### MCP Servers

Enable MCP servers via `mcp_config.json`. See `mcp_config.json.sample` for format.

## Skills

Persona supports [Anthropic-style skills](https://agentskills.io/home).

Built-in skills:
- **skill-creator** - Create or update skills
- **web-search** - Web search (DuckDuckGo default, Tavily with `TRAVILY_TOKEN`)
- **skillsmp-search** - Search SkillsMP marketplace (requires `SKILLSMP_API_KEY` in `.env.sandbox`)
- **planning-with-files** - Markdown-based task planning

More at [Agent Skills Marketplace](https://skillsmp.com/)

## Options

| Option | Description |
|--------|-------------|
| `--mnt-dir PATH` | Host directory to mount (default: `.`) |
| `--no-mnt` | Don't mount any directory |
| `--skills-dir PATH` | Skills directory (default: `skills/`) |
| `--container-image` | Docker image for sandbox |
| `-p, --prompt` | Single prompt (non-interactive) |
| `--stream` | Stream output in non-interactive mode |

## Examples

```bash
# Interactive mode (most common)
persona
persona --mnt-dir ~/projects/myapp
persona --no-mnt
persona --skills-dir ./my-skills

# Single prompt
persona "find all Python files in current directory"
persona --stream -p "explain this code" < code.py
```

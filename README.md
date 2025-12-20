
Persona — universal AI agent (sandboxed)
=======================================

A lightweight CLI agent that runs an AI assistant and provides general-purpose tools.

The agent uses a Docker container as a sandbox to safely run non-interactive commands and transfer files. It exposes helpers to:
- execute shell commands inside the sandbox
- copy files into the sandbox

Quick start
-----------

Install Docker and run:

```bash
python3 main.py
```

Notes
-----
- Docker is required.
- The script starts a named sandbox container on launch and stops it on exit.

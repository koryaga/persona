#!/usr/bin/env python3
import argparse
import asyncio
import os
import signal
import sys
from pathlib import Path

from persona import __version__
from persona.config import env, paths
from persona.sandbox import manager
from persona.agent import builder, tools


def _signal_handler(signum, frame):
    """Handle termination signals to ensure clean container shutdown."""
    sys.exit(0)


async def _main():
    """Main entry point for the persona CLI."""
    load_config()
    configure_logfire()
    
    parser = argparse.ArgumentParser(
        prog="persona",
        description="A universal AI agent CLI with Anthropic-style skills"
    )
    parser.add_argument("--version", action="version", version=f"persona {__version__}")
    parser.add_argument(
        "--mnt-dir",
        dest="mnt_dir",
        help="Local directory to mount into container at /mnt",
        default="."
    )
    parser.add_argument(
        "--no-mnt",
        dest="no_mnt",
        action="store_true",
        help="Don't mount any host directory at /mnt",
        default=False
    )
    parser.add_argument(
        "--skills-dir",
        dest="skills_dir",
        help="Local skills directory to mount into container",
        default=None
    )
    parser.add_argument(
        "--container-image",
        dest="container_image",
        help="Docker image to use for sandbox",
        default=None
    )
    parser.add_argument(
        "-p", "--prompt",
        dest="prompt_flag",
        help="Single prompt to execute (non-interactive mode)",
        default=None
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="Single prompt to execute (non-interactive mode)",
        default=None
    )
    args, remaining = parser.parse_known_args()
    args.prompt = args.prompt or args.prompt_flag
    
    skills_dir = args.skills_dir if args.skills_dir else str(paths.get_skills_dir())
    
    sandbox_image = args.container_image or os.getenv(
        'SANDBOX_CONTAINER_IMAGE',
        "ubuntu.sandbox"
    )
    container_name_base = os.getenv('SANDBOX_CONTAINER_NAME', "sandbox")
    container_name = f"{container_name_base}-{os.getpid()}"

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    container_mgr = manager.ContainerManager(
        name=container_name,
        image=sandbox_image,
        mnt_dir=args.mnt_dir,
        skills_dir=skills_dir,
        env_vars=env.get_sandbox_env_vars(),
        no_mnt=args.no_mnt
    )

    agent = builder.create_agent(Path(skills_dir))
    run_cmd, save_text_file, load_skill = tools.create_tools(container_mgr.name, Path(skills_dir))
    
    agent.tool_plain(run_cmd)
    agent.tool_plain(save_text_file)
    agent.tool_plain(load_skill)
    
    if not container_mgr.start():
        return False
    
    import atexit
    atexit.register(lambda: asyncio.run(container_mgr.stop()))
    
    if args.prompt:
        result = await agent.run(args.prompt)
        print(result.output)
    else:
        async with agent:
            await agent.to_cli(prog_name="persona")
    
    return True


def main():
    """Synchronous entry point for CLI scripts."""
    return asyncio.run(_main())


def load_config():
    """Load configuration from environment."""
    env.load_config()


def configure_logfire():
    """Configure logfire for debug mode."""
    env.configure_logfire()


if __name__ == "__main__":
    main()

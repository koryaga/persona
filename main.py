from pydantic_ai import Agent, ModelSettings, MCPServerTool
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
import asyncio
from pydantic_ai.mcp import MCPServerStdio
from pydantic import BaseModel
import subprocess
import os
import tempfile
import atexit
import time

# name of the container the script will manage
docker_container_name = "ubuntu_sandbox"


def ensure_container_running(name: str) -> None:
    """Ensure a container with `name` is running. If not present, run it with
    `docker run -d --name <name> --rm ubuntu:24.04 sleep infinity`.
    If a stopped container exists, attempt to start it.
    """
    try:
        # check if container is running
        ps = subprocess.run(['docker', 'ps', '-q', '-f', f'name={name}'], capture_output=True, text=True, timeout=10)
        if ps.stdout.strip():
            return
        # check if a container exists but is stopped
        pa = subprocess.run(['docker', 'ps', '-aq', '-f', f'name={name}'], capture_output=True, text=True, timeout=10)
        if pa.stdout.strip():
            subprocess.run(['docker', 'start', name], capture_output=True, text=True, timeout=15)
            # give it a moment
            time.sleep(0.5)
            return
        # otherwise run a fresh container
        run = subprocess.run([
            'docker', 'run', '-d', '--name', name, '--rm', '-v', f'{os.getcwd()}/mnt:/mnt', 'ubuntu:24.04', 'sleep', 'infinity'
        ], capture_output=True, text=True, timeout=30)
        if run.returncode != 0:
            raise RuntimeError(f"Failed to start container {name}: {run.stdout}{run.stderr}")
        # allow container to settle
        time.sleep(0.5)
    except Exception as e:
        print(f"[WARN] ensure_container_running: {e}")


def stop_container(name: str) -> None:
    """Stop the named container if it's running.
    Stopping a container started with `--rm` will remove it.
    """
    try:
        subprocess.run(['docker', 'stop', name], capture_output=True, text=True, timeout=15)
    except Exception as e:
        print(f"[WARN] stop_container: {e}")

# register cleanup at process exit
atexit.register(lambda: stop_container(docker_container_name))

duckduckgo_mcp = MCPServerStdio(
    'uvx',
    args=['duckduckgo-mcp-server'],
    timeout=10
)

agent = Agent(
    model=OpenAIChatModel(
        #"ministral-3:14b",
        "cogito:14b",
        provider=OpenAIProvider(
            base_url='http://localhost:11434/v1',
            api_key='ollama',
        ),
        settings=ModelSettings(temperature=0,top_p=0)
    ),
    instrument=True,
    system_prompt="""
            * Assist USER with its request.
            Use ReACT pattern to reason and act in a loop until USER request is fulfilled. 
            Do not involve USER until its absolutly necessary.
            * You have FULL ACCESS to a Docker container running Ubuntu 24.04 LTS. You can run any command using the `docker_exec_tool`.
            * Search the web for up-to-date information using the `search` tool . Use search to actualize knowledge when needed.
            * Create or modify files inside the Docker container using the `docker_write_tool` if necessary
            * Use python scripting in case need to handle complex logic or data processing.
            * The folder /mnt is a volume, use it to transfer/get files to/from USER.
            """,
    toolsets=[duckduckgo_mcp],

    retries=3
)


@agent.tool_plain
def docker_exec_tool(command: str) -> str:
    """
    Execute any command inside a Docker container using docker exec -it.
    Args:
        command: The command string to execute inside the container. Use ONLY NON INTERACTIVE commands of options.
    Returns:
        The output from the executed command
    """
    print(f"[DEBUG]docker_exec_tool: {command}")
    try:
        # ensure the managed container is running
        ensure_container_running(docker_container_name)
        result = subprocess.run(
            ['docker', 'exec', '-i', docker_container_name, 'sh', '-c', command],
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout + result.stderr
        return output if output else f"Command executed successfully (exit code: {result.returncode})"
    except subprocess.TimeoutExpired:
        return "Error: Command execution timed out after 30 seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"


@agent.tool_plain
def docker_write_tool(container_path: str, content: str) -> str:
    """
    Write `content` into `container_path` inside the 'ubuntu' container using docker cp.
    `container_path` mast presents on container
    """
    print(f"[DEBUG]docker_write_tool: path={container_path} len={len(content or '')}")
    tmpname = None
    try:
        # write content to a local temp file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as tf:
            tf.write(content or "")
            tmpname = tf.name
        # ensure the managed container is running and copy temp file into it
        ensure_container_running(docker_container_name)
        cp_cmd = ['docker', 'cp', tmpname, f"{docker_container_name}:{container_path}"]
        cp = subprocess.run(cp_cmd, capture_output=True, text=True, timeout=30)
        if cp.returncode != 0:
            return f"Error copying file into container (rc={cp.returncode}): {cp.stdout}{cp.stderr}"

        return f"File written to container:{container_path}"
    except subprocess.TimeoutExpired:
        return "Error: operation timed out"
    except Exception as e:
        return f"Error: {e}"
    finally:
        if tmpname and os.path.exists(tmpname):
            try:
                os.remove(tmpname)
            except Exception:
                pass

async def main():
    # start the managed container at script startup
    ensure_container_running(docker_container_name)
    await agent.to_cli()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        # ensure container stopped on normal exit as well
        stop_container(docker_container_name)

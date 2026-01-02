import asyncio
import aiofiles
import logging
import logfire
from pydantic_ai import Agent, ModelSettings, UsageLimits
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic import BaseModel
from pydantic_ai.mcp import MCPServerStdio
import os
from dotenv import load_dotenv
import subprocess
import glob
import re
import atexit
import tempfile

load_dotenv('.env')

SANDBOX_CONTAINER_IMAGE = os.getenv('SANDBOX_CONTAINER_IMAGE',"ubuntu.sandbox")
SANDBOX_CONTAINER_NAME = os.getenv('SANDBOX_CONTAINER_NAME',"sandbox")

#os.environ['OTEL_EXPORTER_OTLP_ENDPOINT'] = 'http://localhost:4318'
#logfire.configure(send_to_logfire=False)
#logfire.instrument_pydantic_ai()
#logfire.instrument_httpx(capture_all=True)

#logging.basicConfig(level=logging.INFO)

openai_model = os.getenv('OPENAI_MODEL', 'cogito:14b') # use Cogito v1 famaily 
openai_api_key = os.getenv('OPENAI_API_KEY', os.getenv('OPENAI_KEY', 'ollama'))
openai_api_base = os.getenv('OPENAI_API_BASE', os.getenv('OPENAI_BASE', 'http://localhost:11434/v1'))

# Use default ModelSettings (no temperature/top_p overrides)
model = OpenAIChatModel(
    openai_model,
    provider=OpenAIProvider(
        base_url=openai_api_base,
        api_key=openai_api_key,
    ),
    settings=ModelSettings(temperature=0, top_p=0),
)



def find_and_parse_skills():
    """Find all SKILL.md files and parse them into XML"""

    def parse_skill(file_path):
        "Parse a SKILL.md file and return XML representation"

        with open(file_path, 'r') as file:
            content = file.read()

        # Find the section between dashes
        match = re.search(r'^---$(.*?)^---$', content, re.DOTALL | re.MULTILINE)
        if match:
            metadata_block = match.group(1).strip().split('\n')
            metadata = dict(line.split(': ', 1) for line in metadata_block)

            # Construct XML
            xml_output = (
                '<skill>\n'
                f'<name>{metadata["name"]}</name>\n'
                f'<description>{metadata["description"]}</description>\n'
                f'<location>/{file_path}</location>\n'  #  added /  to map to /skills inside container
                '</skill>'
            )
            return xml_output
        else:
            raise ValueError("Metadata section not found.")

    skills_xml = []
    
    # Find all SKILL.md files recursively
    skill_files = glob.glob('skills/**/SKILL.md', recursive=True)

    for skill_file in skill_files:
        try:
            xml_content = parse_skill(skill_file)
            skills_xml.append(xml_content)
        except Exception as e:
            print(f"Error parsing {skill_file}: {e}")

    return '\n'.join(skills_xml)


base_dir = os.path.dirname(os.path.abspath(__file__))
instructions_path = os.path.join(base_dir, 'instructions.md')
with open(instructions_path, 'r') as f:
    system_prompt = f.read()

agent = Agent(model,
              instructions= 
              "Enable deep thinking subroutine. " + #Only for CogitoV1 models to enable deep thinking
              f"""
                {system_prompt}
                <available_skills>
                {find_and_parse_skills()}
                </available_skills>
                """)


@agent.tool_plain
async def run_cmd(cmd: str) -> str:
    """
    Runs a command in Ubuntu and returns the combined output.
    Args:
        cmd (str): Command to execute.
    Returns:
        str: Combined output of stdout and stderr.
    """
    
    print(f"\033[91m[DEBUG][INPUT]{cmd}\033[0m")
    try:
        # Execute the command in the container
        # Using the desktop_commander container that's already set up
        result = subprocess.run(
            ["docker", "exec", SANDBOX_CONTAINER_NAME, "bash" ,"-c", f'{cmd}'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Combine stdout and stderr
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR: {result.stderr}"
        
        #print(f"[DEBUG][OUTPUT]{output}")
        return output
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except subprocess.SubprocessError as e:
        return f"Error executing command: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

@agent.tool_plain
async def save_python_py_file(filename:str, file_body: str) -> bool:
    """
    Write a python code to /tmp/{filename}
    Returns True on success, False on failure.
    """
    print(f"\033[94m[DEBUG][FILE] {filename}\033[0m")

    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(file_body)
            tmp_path = tmp.name
        
        # Copy the temp file to the container's /tmp directory
        result = subprocess.run(
            ["docker", "cp", tmp_path, f"{SANDBOX_CONTAINER_NAME}:/tmp/{filename}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print(f"\033[91m[ERROR] Failed to copy {filename}: {result.stderr}\033[0m")
            return False
        
        # Clean up local temp file
        os.unlink(tmp_path)
        
        print(f"\033[92m[SUCCESS] {filename} copied to container /tmp/\033[0m")
        return True
    except Exception as e:
        print(f"\033[91m[ERROR] {str(e)}\033[0m")
        return False


@agent.tool_plain
async def load_skill(skill: str) -> str:
    """
    Load skill file SKILL.md into the context.
    Args:
        skill (str): Skill name.
    """
    print(f"\033[93m[DEBUG][SKILL] {skill}\033[0m")

    async with aiofiles.open(f"skills/{skill}/SKILL.md", "r") as f:
        content = await f.read()
        return f""" Reading: {skill}
                    Base directory: /skills
                    {content}
                    Skill read: {skill}
                """

def start_container(container_name: str, image_name: str) -> bool:
    """
    Start a Docker container with the specified parameters.
    
    Args:
        container_name (str): Name for the container
        image_name (str): Name of the Docker image to use
        
    Returns:
        bool: True if container started successfully, False otherwise
    """
    try:
        # Build the docker run command
        cmd = [
            "docker", "run", "-d", "--rm",
            "-v", f"{os.getcwd()}/mnt:/mnt",
            "-v", f"{os.getcwd()}/skills:/skills",
            "--name", container_name,
            image_name,
            "sleep", "infinity"
        ]
        
        # Execute the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"Container {container_name} started successfully with ID: {result.stdout.strip()}")
            return True
        else:
            print(f"Failed to start container {container_name}: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("Command timed out")
        return False
    except Exception as e:
        print(f"Error starting container: {str(e)}")
        return False


def stop_container(container_name: str) -> bool:
    """
    Stop a Docker container with the specified name.
    
    Args:
        container_name (str): Name of the container to stop
        
    Returns:
        bool: True if container stopped successfully, False otherwise
    """
    try:
        # Check if container exists and is running
        result = subprocess.run(
            ["docker", "ps", "-q", "-f", f"name={container_name}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            # Container exists and is running, stop it
            stop_result = subprocess.run(
                ["docker", "stop", container_name],
                capture_output=True,
                text=True,
                timeout=20
            )
            
            if stop_result.returncode == 0:
                print(f"Container {container_name} stopped successfully")
                return True
            else:
                print(f"Failed to stop container {container_name}: {stop_result.stderr}")
                return False
        else:
            print(f"Container {container_name} not found or not running")
            return True  # Consider it a success if container doesn't exist
            
    except Exception as e:
        print(f"Error stopping container: {str(e)}")
        return False
         

async def main():
    print("[DEBUG] Starting main function")
    
    # Start the container when the program starts
    if not start_container(SANDBOX_CONTAINER_NAME, SANDBOX_CONTAINER_IMAGE ):
        return False
    
    # Register cleanup function to stop container on exit
    atexit.register(stop_container, SANDBOX_CONTAINER_NAME)
    
    async with agent:
        #print("[DEBUG] Running agent in CLI mode")
        await agent.to_cli(prog_name="PersonaAI")



if __name__ == "__main__":
    asyncio.run(main())

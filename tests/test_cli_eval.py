import pytest
import subprocess
import os
import sys
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Contains, Evaluator, EvaluatorContext
from typing import Dict, Any, Optional, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_PATH = os.path.join(PROJECT_ROOT, 'src')
PYTHONPATH = os.environ.get('PYTHONPATH', '') + f":{SRC_PATH}"
VENV_PYTHON = os.path.join(PROJECT_ROOT, '.venv', 'bin', 'python')
USE_VENV_PYTHON = os.path.exists(VENV_PYTHON)
PYTHON_EXEC = VENV_PYTHON if USE_VENV_PYTHON else sys.executable

CLI_ENV = os.environ.copy()
CLI_ENV['PYTHONPATH'] = PYTHONPATH


SANDBOX_CONTAINER_NAME_BASE = "sandbox"
SANDBOX_CONTAINER_NAME = f"{SANDBOX_CONTAINER_NAME_BASE}-{os.getpid()}"

OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_API_BASE = os.getenv('OPENAI_API_BASE', '')


def run_cli_prompt(prompt: str) -> str:
    """Run persona CLI with a single prompt and capture the output."""
    result = subprocess.run(
        [PYTHON_EXEC, "-m", "persona.cli"],
        input=f"{prompt}\n/exit\n",
        capture_output=True,
        text=True,
        timeout=180,
        env=CLI_ENV
    )
    return result.stdout + result.stderr


def run_cli_non_interactive(prompt: str, args: Optional[List[str]] = None) -> str:
    """Run persona CLI in non-interactive mode with a single prompt."""
    cmd = [PYTHON_EXEC, "-m", "persona.cli"]
    if args:
        cmd.extend(args)
    cmd.append(prompt)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=180,
        env=CLI_ENV
    )
    return result.stdout + result.stderr


def run_cli_with_flag(prompt: str, flag: str) -> str:
    """Run persona CLI with specific flag and prompt value."""
    cmd = [PYTHON_EXEC, "-m", "persona.cli", flag, prompt]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=180,
        env=CLI_ENV
    )
    return result.stdout + result.stderr


def is_container_running() -> bool:
    """Check if this process's sandbox container is already running."""
    result = subprocess.run(
        ["docker", "ps", "-q", "-f", f"name={SANDBOX_CONTAINER_NAME}"],
        capture_output=True,
        text=True,
        timeout=10
    )
    return bool(result.stdout.strip())


def ensure_container():
    """Ensure container is running, create if needed."""
    if is_container_running():
        return
    cmd = ["docker", "run", "-d", "--rm", "--name", SANDBOX_CONTAINER_NAME, "ubuntu.sandbox", "sleep", "infinity"]
    subprocess.run(cmd, capture_output=True, text=True, timeout=30)


class LLMJudge(Evaluator[str, str]):
    """Custom evaluator using OpenAI-compatible API for LLM-as-a-Judge."""

    def __init__(self, rubric: str, model: str = "gpt-4o"):
        self.rubric = rubric
        self.model = model
        self.api_base = OPENAI_API_BASE
        self.api_key = OPENAI_API_KEY

    def evaluate(self, ctx: EvaluatorContext[str, str]) -> Dict[str, Any]:
        prompt = f"""You are grading output according to a rubric.

Rubric: {self.rubric}

Input: {ctx.inputs}
Output: {ctx.output}

Respond with a JSON object with this structure:
{{"reason": string, "pass": boolean, "score": number}}

Examples:
{{"reason": "response mentions skill-creator", "pass": true, "score": 1.0}}
{{"reason": "response does not mention skill-creator", "pass": false, "score": 0.0}}
"""

        try:
            url = f"{self.api_base}/chat/completions" if self.api_base else "https://api.openai.com/v1/chat/completions"
            response = httpx.post(
                url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            result = json.loads(content)
            return {
                "passed": result.get("pass", False),
                "score": result.get("score", 0.0),
                "reason": result.get("reason", ""),
            }
        except Exception as e:
            return {"passed": False, "score": 0.0, "reason": str(e)}


class TestAgentCLIExpectedOutput:
    """Core CLI tests for agent functionality."""

    @pytest.fixture(autouse=True)
    def ensure_container_fixture(self):
        """Ensure container is running before each test."""
        ensure_container()
        yield

    def test_file_list_files(self):
        """Verify agent can list files using pydantic-evals Contains."""
        output = run_cli_prompt("List files in /var")
        case = Case(
            name="file_search",
            inputs="List files in /var",
            expected_output="Should show file list results",
        )
        dataset = Dataset(cases=[case], evaluators=[Contains(value="file")])
        report = dataset.evaluate_sync(lambda p: output)
        assert report.cases[0].assertions["Contains"]

    def test_process_list_shows_processes(self):
        """Verify agent can list running processes."""
        output = run_cli_prompt("Show me the running processes")
        output_lower = output.lower()
        found_process = any(word in output_lower for word in ["process", "pid", "cpu", "memory", "running"])
        assert found_process, f"Output should show processes. Got: {output[:300]}"

    def test_skill_creator_llm_judge(self):
        """Verify skill-creator skill is available using LLM-as-a-Judge."""
        prompt = "What skills do you have?"
        output = run_cli_prompt(prompt)

        rubric = """Evaluate if the agent response lists the skill-creator skill.

The response should mention 'skill-creator' as an available skill."""

        case = Case(
            name="skill_creator",
            inputs=prompt,
            expected_output="Should list skill-creator skill",
        )

        dataset = Dataset(
            cases=[case],
            evaluators=[
                LLMJudge(
                    rubric=rubric,
                    model=OPENAI_MODEL,
                )
            ]
        )

        report = dataset.evaluate_sync(lambda p: output)
        case_result = report.cases[0]
        assertions = case_result.assertions
        assert assertions.get("passed", False), f"LLM Judge failed"

    def test_help_command(self):
        """Verify help command returns helpful information."""
        output = run_cli_prompt("Help me understand what you can do")
        output_lower = output.lower()
        found_help = any(word in output_lower for word in ["help", "can", "skill", "capability", "able"])
        assert found_help, f"Output should provide helpful info. Got: {output[:300]}"


class TestNonInteractiveMode:
    """Tests for non-interactive CLI mode."""

    def test_basic_prompt(self):
        """Verify non-interactive mode works with a basic prompt."""
        output = run_cli_non_interactive("List files in /var")
        output_lower = output.lower()
        found_var = any(word in output_lower for word in ["var", "file", "lib", "run", "tmp"])
        assert found_var, f"Output should mention /var contents. Got: {output[:300]}"

    def test_mnt_dir_argument(self):
        """Verify non-interactive mode works with --mnt-dir argument."""
        output = run_cli_non_interactive("List files in /mnt", args=["--mnt-dir", "."])
        output_lower = output.lower()
        found_mnt = any(word in output_lower for word in ["mnt", "file", "dir", "list"])
        assert found_mnt, f"Output should mention /mnt. Got: {output[:300]}"

    def test_web_search_skill(self):
        """Verify agent can use web-search skill in non-interactive mode."""
        output = run_cli_non_interactive("Use web-search skill to search for 'Python tutorial'")
        output_lower = output.lower()
        found_web = any(word in output_lower for word in ["web", "search", "python", "tutorial", "skill"])
        assert found_web, f"Output should mention web search. Got: {output[:300]}"

    def test_no_mnt_flag(self):
        """Verify non-interactive mode works with --no-mnt flag."""
        output = run_cli_non_interactive("List files in /tmp", args=["--no-mnt"])
        output_lower = output.lower()
        found_tmp = any(word in output_lower for word in ["tmp", "file", "dir"])
        assert found_tmp, f"Output should mention /tmp. Got: {output[:300]}"

    def test_container_image_flag(self):
        """Verify non-interactive mode works with --container-image flag."""
        output = run_cli_non_interactive("Who are you?", args=["--container-image", "ubuntu.sandbox"])
        output_lower = output.lower()
        found_agent = any(word in output_lower for word in ["agent", "ai", "help", "assistant"])
        assert found_agent, f"Output should identify as agent. Got: {output[:300]}"


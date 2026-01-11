import pytest
import subprocess
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Contains, Evaluator, EvaluatorContext
from typing import Dict, Any


SANDBOX_CONTAINER_NAME_BASE = "sandbox"
SANDBOX_CONTAINER_NAME = f"{SANDBOX_CONTAINER_NAME_BASE}-{os.getpid()}"

OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'xiaomi/mimo-v2-flash:free')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_API_BASE = os.getenv('OPENAI_API_BASE', 'https://openrouter.ai/api/v1')


def run_cli_prompt(prompt: str) -> str:
    """Run main.py CLI with a single prompt and capture the output."""
    result = subprocess.run(
        ["python3", "main.py"],
        input=f"{prompt}\n/exit\n",
        capture_output=True,
        text=True,
        timeout=60
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


class OpenRouterJudge(Evaluator[str, str]):
    """Custom evaluator using OpenRouter API for LLM-as-a-Judge."""

    def __init__(self, rubric: str, model: str = "xiaomi/mimo-v2-flash:free"):
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
            response = httpx.post(
                f"{self.api_base}/chat/completions",
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
        """Verify skill-creator skill is available using LLM-as-a-Judge via OpenRouter."""
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
                OpenRouterJudge(
                    rubric=rubric,
                    model=OPENAI_MODEL,
                )
            ]
        )

        report = dataset.evaluate_sync(lambda p: output)
        case_result = report.cases[0]
        assertions = case_result.assertions
        assert assertions.get("passed", False), f"OpenRouter Judge failed"

    def test_help_command(self):
        """Verify help command returns helpful information."""
        output = run_cli_prompt("Help me understand what you can do")
        output_lower = output.lower()
        found_help = any(word in output_lower for word in ["help", "can", "skill", "capability", "able"])
        assert found_help, f"Output should provide helpful info. Got: {output[:300]}"

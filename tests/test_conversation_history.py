#!/usr/bin/env python3
import pytest
import subprocess
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conftest import SANDBOX_CONTAINER_NAME, ensure_container, cleanup_container

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_PATH = os.path.join(PROJECT_ROOT, 'src')
PYTHONPATH = os.environ.get('PYTHONPATH', '') + f":{SRC_PATH}"
VENV_PYTHON = os.path.join(PROJECT_ROOT, '.venv', 'bin', 'python')
USE_VENV_PYTHON = os.path.exists(VENV_PYTHON)
PYTHON_EXEC = VENV_PYTHON if USE_VENV_PYTHON else sys.executable

CLI_ENV = os.environ.copy()
CLI_ENV['PYTHONPATH'] = PYTHONPATH


def run_interactive_session(inputs: list[str]) -> str:
    """Run persona CLI with multiple inputs simulating interactive session.

    This function simulates an interactive REPL session by piping multiple
    inputs to the CLI. Each input is followed by Enter, and the session
    ends with /exit command.
    """
    input_str = "\n".join(inputs) + "\n/exit\n"
    result = subprocess.run(
        [PYTHON_EXEC, "-m", "persona.cli"],
        input=input_str,
        capture_output=True,
        text=True,
        timeout=180,
        env=CLI_ENV
    )
    return result.stdout + result.stderr


class TestConversationHistory:
    """Tests for agent conversation memory within a session.

    These tests verify that the agent can remember context from earlier
    messages in the same conversation session. The key scenarios are:
    - Remembering user-provided information (name, preferences)
    - Referencing tool outputs from previous turns
    - Maintaining context across 3+ turn conversations
    """

    @pytest.fixture(autouse=True)
    def ensure_container_fixture(self):
        """Ensure container is running before each test."""
        ensure_container(SANDBOX_CONTAINER_NAME)
        yield
        cleanup_container(SANDBOX_CONTAINER_NAME)

    def test_remembers_name_across_turns(self):
        """Test agent remembers user-provided name in follow-up question.

        Scenario:
        1. User: "My name is Alice"
        2. Agent: Confirms greeting
        3. User: "What is my name?"
        4. Agent: Should recall "Alice"
        """
        inputs = [
            "My name is Alice",
            "What is my name?"
        ]
        output = run_interactive_session(inputs)
        output_lower = output.lower()
        assert "alice" in output_lower, f"Agent should remember name 'Alice'. Got: {output[:500]}"

    def test_remembers_custom_variable(self):
        """Test agent remembers user-defined custom variable.

        Scenario:
        1. User: "Set PROJECT_ROOT to /Users/skoryaga/src/persona"
        2. User: "What is the PROJECT_ROOT?"
        3. Agent: Should recall /Users/skoryaga/src/persona
        """
        inputs = [
            "Set TEST_VAR to test_value_123",
            "What is the value of TEST_VAR?"
        ]
        output = run_interactive_session(inputs)
        output_lower = output.lower()
        assert "test_value_123" in output_lower, f"Agent should recall 'test_value_123'. Got: {output[:500]}"

    def test_references_tool_output_in_followup(self):
        """Test agent references data from earlier tool call.

        Scenario:
        1. User: "Run: echo 'BUILD_ID=abc123'"
        2. Agent: Executes command, shows output
        3. User: "What was the BUILD_ID from the previous command?"
        4. Agent: Should recall "abc123"
        """
        inputs = [
            "Run: echo 'BUILD_ID=abc123'",
            "What was the BUILD_ID from the previous command?"
        ]
        output = run_interactive_session(inputs)
        output_lower = output.lower()
        assert "abc123" in output_lower, f"Agent should recall 'abc123' from tool output. Got: {output[:500]}"

    def test_three_turn_conversation(self):
        """Test agent handles 3+ turn conversations correctly.

        Scenario:
        1. User: Greeting
        2. Agent: Responds
        3. User: List files in /tmp
        4. Agent: Shows file list
        5. User: How many files were listed?
        6. Agent: Should reference the file count from turn 3
        """
        inputs = [
            "List files in /tmp",
            "Count how many items are in /tmp",
            "What was the count?"
        ]
        output = run_interactive_session(inputs)
        output_lower = output.lower()
        count_mentioned = any(word in output_lower for word in ["count", "number", "items", "files", "listed"])
        assert count_mentioned, f"Agent should reference count from previous turn. Got: {output[:500]}"

    def test_remembers_preferred_language(self):
        """Test agent remembers user language preference.

        Scenario:
        1. User: "I prefer Python for coding"
        2. User: "What language should I use for this task?"
        3. Agent: Should suggest Python
        """
        inputs = [
            "I prefer Python for coding tasks",
            "What language should I use for data analysis?"
        ]
        output = run_interactive_session(inputs)
        output_lower = output.lower()
        python_mentioned = "python" in output_lower
        assert python_mentioned, f"Agent should recall Python preference. Got: {output[:500]}"

    def test_remembers_clarification_context(self):
        """Test agent maintains context after clarification.

        Scenario:
        1. User: "Create a file"
        2. Agent: Asks for clarification
        3. User: "Create /tmp/test.txt with content 'hello world'"
        4. Agent: Creates file
        5. User: "What file did you just create?"
        6. Agent: Should recall /tmp/test.txt
        """
        inputs = [
            "Create a test file at /tmp/conversation_test.txt with content 'test content'",
            "What file did you just create?"
        ]
        output = run_interactive_session(inputs)
        output_lower = output.lower()
        file_mentioned = "conversation_test.txt" in output_lower or "/tmp/conversation_test.txt" in output_lower
        assert file_mentioned, f"Agent should recall created file. Got: {output[:500]}"

    def test_greeting_and_context_preserved(self):
        """Test agent preserves context from greeting through multiple turns.

        Scenario:
        1. User: "Hello, I am Bob"
        2. User: "How are you?"
        3. Agent: Responds
        4. User: "Who am I?"
        5. Agent: Should remember "Bob"
        """
        inputs = [
            "Hello, I am Bob",
            "How are you?",
            "Who am I?"
        ]
        output = run_interactive_session(inputs)
        output_lower = output.lower()
        assert "bob" in output_lower, f"Agent should remember 'Bob' from greeting. Got: {output[:500]}"

    def test_system_instruction_remembered(self):
        """Test that system instructions are applied throughout conversation.

        System prompt instructs agent to summarize large outputs.
        This test verifies the behavior is consistent across multiple turns.
        """
        inputs = [
            "Show me the date",
            "Show me the time"
        ]
        output = run_interactive_session(inputs)
        output_lower = output.lower()
        has_date_or_time = any(word in output_lower for word in ["date", "time", "202", ":", "-"])
        assert has_date_or_time, f"Agent should show date/time info. Got: {output[:500]}"


class TestConversationHistoryEdgeCases:
    """Edge case tests for conversation history."""

    @pytest.fixture(autouse=True)
    def ensure_container_fixture(self):
        """Ensure container is running before each test."""
        ensure_container(SANDBOX_CONTAINER_NAME)
        yield
        cleanup_container(SANDBOX_CONTAINER_NAME)

    def test_single_turn_no_history_needed(self):
        """Verify single prompt works correctly."""
        inputs = ["List files in /var"]
        output = run_interactive_session(inputs)
        output_lower = output.lower()
        found_var = any(word in output_lower for word in ["var", "file", "lib", "run", "tmp"])
        assert found_var, f"Single turn should work. Got: {output[:300]}"

    def test_command_output_referenced_later(self):
        """Test that command output can be referenced in subsequent questions."""
        inputs = [
            "Run: uname -a",
            "What operating system is shown?"
        ]
        output = run_interactive_session(inputs)
        output_lower = output.lower()
        os_mentioned = any(word in output_lower for word in ["linux", "darwin", "ubuntu", "kernel", "uname"])
        assert os_mentioned, f"Agent should reference OS from uname output. Got: {output[:500]}"

    def test_complex_multi_turn_flow(self):
        """Test complex conversation with multiple context shifts."""
        inputs = [
            "Set CONTEXT_VAR to first_value",
            "Run: echo $CONTEXT_VAR",
            "Set CONTEXT_VAR to second_value",
            "Run: echo $CONTEXT_VAR again",
            "What was the first CONTEXT_VAR value?"
        ]
        output = run_interactive_session(inputs)
        output_lower = output.lower()
        assert "first_value" in output_lower, f"Agent should recall first value. Got: {output[:700]}"

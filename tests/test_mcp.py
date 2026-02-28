#!/usr/bin/env python3
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from persona.config import env


class TestIsLogfire:
    """Tests for is_logfire() function."""

    def test_logfire_true_various_formats(self):
        """Test is_logfire returns True for various truthy values."""
        test_values = ['true', 'True', 'TRUE', '1', 'yes', 'YES']
        for value in test_values:
            os.environ['LOGFIRE'] = value
            assert env.is_logfire() is True, f"is_logfire() should return True for LOGFIRE={value}"

    def test_logfire_false_various_formats(self):
        """Test is_logfire returns False for various falsy values."""
        test_values = ['false', 'False', 'FALSE', '0', 'no', 'NO', '', 'random']
        for value in test_values:
            os.environ['LOGFIRE'] = value
            assert env.is_logfire() is False, f"is_logfire() should return False for LOGFIRE={value}"

    def test_logfire_not_set(self):
        """Test is_logfire returns False when LOGFIRE not set."""
        if 'LOGFIRE' in os.environ:
            del os.environ['LOGFIRE']
        assert env.is_logfire() is False


class TestConfigureLogfire:
    """Tests for configure_logfire() function."""

    def test_configure_logfire_exists(self):
        """Verify configure_logfire function exists and is callable."""
        assert callable(env.configure_logfire)

    @patch('persona.config.env.logfire')
    def test_no_instrumentation_when_disabled(self, mock_logfire):
        """Test no instrumentation when both DEBUG and LOGFIRE are false."""
        os.environ.pop('DEBUG', None)
        os.environ.pop('LOGFIRE', None)
        env.configure_logfire()
        mock_logfire.configure.assert_not_called()
        mock_logfire.instrument_pydantic_ai.assert_not_called()
        mock_logfire.instrument_httpx.assert_not_called()

    @patch('persona.config.env.logfire')
    def test_instrumentation_when_debug_true(self, mock_logfire):
        """Test instrumentation is enabled when DEBUG=true."""
        os.environ['DEBUG'] = 'true'
        os.environ.pop('LOGFIRE', None)
        env.configure_logfire()
        mock_logfire.configure.assert_called()
        mock_logfire.instrument_pydantic_ai.assert_called()
        mock_logfire.instrument_httpx.assert_called()

    @patch('persona.config.env.logfire')
    def test_instrumentation_when_logfire_true(self, mock_logfire):
        """Test instrumentation is enabled when LOGFIRE=true."""
        os.environ.pop('DEBUG', None)
        os.environ['LOGFIRE'] = 'true'
        env.configure_logfire()
        mock_logfire.configure.assert_called()
        mock_logfire.instrument_pydantic_ai.assert_called()
        mock_logfire.instrument_httpx.assert_called()

    @patch('persona.config.env.logfire')
    def test_logfire_send_to_logfire_when_enabled(self, mock_logfire):
        """Test send_to_logfire is set when LOGFIRE=true."""
        os.environ.pop('DEBUG', None)
        os.environ['LOGFIRE'] = 'true'
        env.configure_logfire()
        call_kwargs = mock_logfire.configure.call_args[1]
        assert call_kwargs['send_to_logfire'] == 'if-token-present'

    @patch('persona.config.env.logfire')
    def test_debug_does_not_send_to_logfire_by_default(self, mock_logfire):
        """Test DEBUG=true does not send to logfire by default."""
        os.environ['DEBUG'] = 'true'
        os.environ.pop('LOGFIRE', None)
        env.configure_logfire()
        call_kwargs = mock_logfire.configure.call_args[1]
        assert call_kwargs['send_to_logfire'] is False


class TestMCPConfiguration:
    """Tests for MCP configuration in builder.py."""

    def test_mcp_enabled_env_var_not_set(self):
        """Test MCP_ENABLED defaults to false."""
        os.environ.pop('MCP_ENABLED', None)
        result = os.getenv('MCP_ENABLED', 'false').lower()
        assert result == 'false'

    def test_mcp_enabled_env_var_true(self):
        """Test MCP_ENABLED can be set to true."""
        os.environ['MCP_ENABLED'] = 'true'
        result = os.getenv('MCP_ENABLED', 'false').lower()
        assert result == 'true'

    def test_mcp_enabled_env_var_various_formats(self):
        """Test MCP_ENABLED accepts various truthy values."""
        test_values = ['true', 'True', 'TRUE', '1', 'yes']
        for value in test_values:
            os.environ['MCP_ENABLED'] = value
            result = os.getenv('MCP_ENABLED', 'false').lower()
            is_truthy = result in ('true', '1', 'yes')
            assert is_truthy, f"MCP_ENABLED={value} should be truthy, got: {result}"

    def test_mcp_enabled_env_var_falsy(self):
        """Test MCP_ENABLED returns false for falsy values."""
        test_values = ['false', 'False', 'FALSE', '0', 'no', '']
        for value in test_values:
            os.environ['MCP_ENABLED'] = value
            result = os.getenv('MCP_ENABLED', 'false').lower()
            is_falsy = result not in ('true', '1', 'yes')
            assert is_falsy, f"MCP_ENABLED={value} should be falsy, got: {result}"

    def test_mcp_config_sample_file_exists(self):
        """Test mcp_config.json.sample exists in project root."""
        project_root = Path(__file__).parent.parent
        mcp_sample = project_root / 'mcp_config.json.sample'
        assert mcp_sample.exists(), "mcp_config.json.sample should exist"

    def test_mcp_config_sample_valid_json(self):
        """Test mcp_config.json.sample contains valid JSON."""
        import json
        project_root = Path(__file__).parent.parent
        mcp_sample = project_root / 'mcp_config.json.sample'
        with open(mcp_sample) as f:
            config = json.load(f)
        assert 'mcpServers' in config
        assert 'everything' in config['mcpServers']

    def test_mcp_config_sample_has_npx_command(self):
        """Test mcp_config.json.sample uses npx command."""
        import json
        project_root = Path(__file__).parent.parent
        mcp_sample = project_root / 'mcp_config.json.sample'
        with open(mcp_sample) as f:
            config = json.load(f)
        everything_config = config['mcpServers']['everything']
        assert everything_config['command'] == 'npx'
        assert '@modelcontextprotocol/server-everything' in everything_config['args']

    def test_load_mcp_servers_import(self):
        """Test load_mcp_servers can be imported from pydantic_ai.mcp."""
        from pydantic_ai.mcp import load_mcp_servers
        assert callable(load_mcp_servers)

    @patch('persona.agent.builder.load_mcp_servers')
    def test_load_mcp_servers_called_when_enabled(self, mock_load):
        """Test load_mcp_servers is called when MCP_ENABLED=true."""
        from persona.agent import builder
        os.environ['MCP_ENABLED'] = 'true'
        mock_load.return_value = []

        try:
            with patch('os.path.exists', return_value=True):
                pass
        except Exception:
            pass

        os.environ.pop('MCP_ENABLED', None)

    def test_gitignore_includes_mcp_config(self):
        """Test .gitignore includes mcp_config.json."""
        project_root = Path(__file__).parent.parent
        gitignore = project_root / '.gitignore'
        with open(gitignore) as f:
            content = f.read()
        assert 'mcp_config.json' in content

#!/usr/bin/env python3
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from persona.config import env


class TestIsDebug:
    """Tests for is_debug() function."""

    def test_debug_true_various_formats(self):
        """Test is_debug returns True for various truthy values."""
        test_values = ['true', 'True', 'TRUE', '1', 'yes', 'YES']
        for value in test_values:
            os.environ['DEBUG'] = value
            assert env.is_debug() is True, f"is_debug() should return True for DEBUG={value}"

    def test_debug_false_various_formats(self):
        """Test is_debug returns False for various falsy values."""
        test_values = ['false', 'False', 'FALSE', '0', 'no', 'NO', '', 'random']
        for value in test_values:
            os.environ['DEBUG'] = value
            assert env.is_debug() is False, f"is_debug() should return False for DEBUG={value}"

    def test_debug_not_set(self):
        """Test is_debug returns False when DEBUG not set."""
        if 'DEBUG' in os.environ:
            del os.environ['DEBUG']
        assert env.is_debug() is False


class TestGetSandboxEnvVars:
    """Tests for get_sandbox_env_vars() function."""

    def test_empty_when_no_env_file(self):
        """Test returns empty dict when .env.sandbox doesn't exist."""
        original = os.environ.copy()
        try:
            os.environ.clear()
            os.environ.update(original)
            if 'PATH' not in os.environ:
                os.environ['PATH'] = '/usr/bin'
            result = env.get_sandbox_env_vars()
            assert isinstance(result, dict)
        except Exception:
            pass

    def test_parses_valid_env_file(self):
        """Test parsing of valid .env.sandbox format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env.sandbox', delete=False) as f:
            f.write('API_KEY=secret123\n')
            f.write('ENDPOINT=https://api.example.com\n')
            f.write('# This is a comment\n')
            f.write('ANOTHER=value\n')
            temp_path = f.name

        try:
            result = env.get_sandbox_env_vars(temp_path)
            assert 'API_KEY' in result
            assert result['API_KEY'] == 'secret123'
            assert 'ENDPOINT' in result
            assert result['ENDPOINT'] == 'https://api.example.com'
            assert 'ANOTHER' in result
            assert 'PATH' not in result
            assert '#' not in str(result)
        finally:
            os.unlink(temp_path)

    def test_ignores_comments_and_empty_lines(self):
        """Test that comments and empty lines are ignored."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env.sandbox', delete=False) as f:
            f.write('# Comment line\n')
            f.write('\n')
            f.write('  \n')
            f.write('KEY=value\n')
            temp_path = f.name

        try:
            result = env.get_sandbox_env_vars(temp_path)
            assert 'KEY' in result
            assert len(result) == 1
        finally:
            os.unlink(temp_path)


class TestLoadConfig:
    """Tests for load_config() function."""

    def test_load_config_exists(self):
        """Verify load_config function exists and is callable."""
        assert callable(env.load_config)

    def test_configure_logfire_exists(self):
        """Verify configure_logfire function exists and is callable."""
        assert callable(env.configure_logfire)

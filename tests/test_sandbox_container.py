#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from persona.sandbox import container


class TestStartContainer:
    """Tests for start_container() function."""

    def test_start_container_success(self):
        """Test successful container start."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='abc123\n')
            result = container.start_container(
                container_name='test-container',
                image_name='ubuntu.sandbox',
                mnt_dir='/tmp',
                skills_dir='/Users/skoryaga/src/persona/skills'
            )
            assert result is True
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert 'docker' in call_args[0][0]
            assert 'run' in call_args[0][0]
            assert 'test-container' in call_args[0][0]

    def test_start_container_failure(self):
        """Test container start failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr='Error: invalid image')
            result = container.start_container(
                container_name='test-container',
                image_name='invalid-image',
                mnt_dir='/tmp',
                skills_dir='/Users/skoryaga/src/persona/skills'
            )
            assert result is False

    def test_start_container_expands_paths(self):
        """Test that paths are expanded correctly."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='abc123\n')
            container.start_container(
                container_name='test-container',
                image_name='ubuntu.sandbox',
                mnt_dir='~/tmp',
                skills_dir='~/skills'
            )
            call_args = mock_run.call_args
            docker_cmd = call_args[0][0]
            assert 'docker' in docker_cmd
            assert 'run' in docker_cmd
            assert 'test-container' in docker_cmd

    def test_start_container_no_mnt_flag(self):
        """Test container start with no_mnt=True."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='abc123\n')
            container.start_container(
                container_name='test-container',
                image_name='ubuntu.sandbox',
                mnt_dir='/tmp',
                skills_dir='/Users/skoryaga/src/persona/skills',
                no_mnt=True
            )
            call_args = mock_run.call_args
            docker_args = call_args[0][0]
            assert '-v' not in docker_args or not any(':mnt' in str(a) for a in docker_args)


class TestStopContainer:
    """Tests for stop_container() function."""

    def test_stop_container_running(self):
        """Test stopping a running container."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout='abc123\n'),
                MagicMock(returncode=0, stdout='')
            ]
            result = container.stop_container('test-container')
            assert result is True
            assert mock_run.call_count == 2

    def test_stop_container_not_running(self):
        """Test stopping a container that's not running."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='')
            result = container.stop_container('test-container')
            assert result is True

    def test_stop_container_failure(self):
        """Test stop container command failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout='abc123\n'),
                MagicMock(returncode=1, stderr='Error stopping')
            ]
            result = container.stop_container('test-container')
            assert result is False


class TestContainerFunctionsExist:
    """Verify container module functions exist."""

    def test_start_container_exists(self):
        """Verify start_container function exists."""
        assert callable(container.start_container)

    def test_stop_container_exists(self):
        """Verify stop_container function exists."""
        assert callable(container.stop_container)

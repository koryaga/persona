#!/usr/bin/env python3
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from persona.sandbox import manager


class TestContainerManagerInit:
    """Tests for ContainerManager initialization."""

    def test_init_with_defaults(self):
        """Test ContainerManager initializes with default values."""
        mgr = manager.ContainerManager(
            name='test-container',
            image='ubuntu.sandbox',
            mnt_dir='/tmp',
            skills_dir='/Users/skoryaga/src/persona/skills',
            env_vars={},
            no_mnt=False
        )
        assert mgr.name == 'test-container'
        assert mgr.image == 'ubuntu.sandbox'
        assert mgr.mnt_dir == '/tmp'
        assert mgr.skills_dir == '/Users/skoryaga/src/persona/skills'
        assert mgr.env_vars == {}
        assert mgr.no_mnt is False
        assert mgr._env_file is None

    def test_init_with_env_vars(self):
        """Test ContainerManager with environment variables."""
        env_vars = {'API_KEY': 'secret', 'ENDPOINT': 'http://example.com'}
        mgr = manager.ContainerManager(
            name='test-container',
            image='ubuntu.sandbox',
            mnt_dir='/tmp',
            skills_dir='/Users/skoryaga/src/persona/skills',
            env_vars=env_vars,
            no_mnt=False
        )
        assert mgr.env_vars == env_vars


class TestContainerManagerStart:
    """Tests for ContainerManager.start() method."""

    def test_start_success(self):
        """Test successful container start."""
        mgr = manager.ContainerManager(
            name='test-container',
            image='ubuntu.sandbox',
            mnt_dir='/tmp',
            skills_dir='/Users/skoryaga/src/persona/skills',
            env_vars={},
            no_mnt=False
        )
        with patch('persona.sandbox.container.start_container', return_value=True):
            result = mgr.start()
            assert result is True
            assert mgr._env_file is None

    def test_start_failure(self):
        """Test container start failure."""
        mgr = manager.ContainerManager(
            name='test-container',
            image='ubuntu.sandbox',
            mnt_dir='/tmp',
            skills_dir='/Users/skoryaga/src/persona/skills',
            env_vars={},
            no_mnt=False
        )
        with patch('persona.sandbox.container.start_container', return_value=False):
            result = mgr.start()
            assert result is False
            assert mgr._env_file is None

    def test_start_creates_env_file(self):
        """Test that start creates temporary env file for env_vars."""
        mgr = manager.ContainerManager(
            name='test-container',
            image='ubuntu.sandbox',
            mnt_dir='/tmp',
            skills_dir='/Users/skoryaga/src/persona/skills',
            env_vars={'API_KEY': 'secret123'},
            no_mnt=False
        )
        with patch('persona.sandbox.container.start_container', return_value=True):
            result = mgr.start()
            assert result is True
            assert mgr._env_file is not None
            assert os.path.exists(mgr._env_file)
            os.unlink(mgr._env_file)


class TestContainerManagerStop:
    """Tests for ContainerManager.stop() method."""

    def test_stop_success(self):
        """Test successful container stop."""
        mgr = manager.ContainerManager(
            name='test-container',
            image='ubuntu.sandbox',
            mnt_dir='/tmp',
            skills_dir='/Users/skoryaga/src/persona/skills',
            env_vars={},
            no_mnt=False
        )
        with patch('persona.sandbox.container.stop_container', return_value=True):
            result = mgr.stop()
            assert result is True

    def test_stop_cleans_env_file(self):
        """Test that stop cleans up temporary env file."""
        mgr = manager.ContainerManager(
            name='test-container',
            image='ubuntu.sandbox',
            mnt_dir='/tmp',
            skills_dir='/Users/skoryaga/src/persona/skills',
            env_vars={'API_KEY': 'secret123'},
            no_mnt=False
        )
        with patch('persona.sandbox.container.start_container', return_value=True):
            mgr.start()
            assert mgr._env_file is not None
            env_file_path = mgr._env_file
        with patch('persona.sandbox.container.stop_container', return_value=True):
            mgr.stop()
        assert not os.path.exists(env_file_path)


class TestContainerManagerContextManager:
    """Tests for ContainerManager context manager."""

    def test_context_manager_enter(self):
        """Test context manager entry starts container."""
        mgr = manager.ContainerManager(
            name='test-container',
            image='ubuntu.sandbox',
            mnt_dir='/tmp',
            skills_dir='/Users/skoryaga/src/persona/skills',
            env_vars={},
            no_mnt=False
        )
        with patch('persona.sandbox.container.start_container', return_value=True):
            with mgr as result:
                assert result is mgr

    def test_context_manager_exit(self):
        """Test context manager exit stops container."""
        mgr = manager.ContainerManager(
            name='test-container',
            image='ubuntu.sandbox',
            mnt_dir='/tmp',
            skills_dir='/Users/skoryaga/src/persona/skills',
            env_vars={},
            no_mnt=False
        )
        with patch('persona.sandbox.container.start_container', return_value=True):
            with patch('persona.sandbox.container.stop_container', return_value=True):
                with mgr:
                    pass

    def test_context_manager_start_failure(self):
        """Test context manager raises on start failure."""
        mgr = manager.ContainerManager(
            name='test-container',
            image='ubuntu.sandbox',
            mnt_dir='/tmp',
            skills_dir='/Users/skoryaga/src/persona/skills',
            env_vars={},
            no_mnt=False
        )
        with patch('persona.sandbox.container.start_container', return_value=False):
            try:
                with mgr:
                    pass
                assert False, "Should have raised RuntimeError"
            except RuntimeError as e:
                assert 'Failed to start container' in str(e)


class TestContainerManagerClass:
    """Verify ContainerManager class exists and is properly defined."""

    def test_container_manager_exists(self):
        """Verify ContainerManager class exists."""
        assert hasattr(manager, 'ContainerManager')
        assert callable(manager.ContainerManager)

    def test_module_exports(self):
        """Verify module exports expected functions."""
        assert hasattr(manager, 'ContainerManager')

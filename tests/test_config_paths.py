#!/usr/bin/env python3
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from persona.config import paths


def test_get_skills_dir():
    """Test that get_skills_dir() resolves to correct path."""
    skills_dir = paths.get_skills_dir()
    
    assert skills_dir.exists(), f"Skills directory does not exist: {skills_dir}"
    assert skills_dir.is_dir(), f"Skills path is not a directory: {skills_dir}"
    
    web_search_skill = skills_dir / "web-search" / "SKILL.md"
    assert web_search_skill.exists(), f"web-search/SKILL.md not found at: {web_search_skill}"
    
    assert str(skills_dir).endswith("persona/skills"), f"Skills path should end with 'persona/skills': {skills_dir}"


def test_get_instructions_path():
    """Test that get_instructions_path() resolves to correct path."""
    instructions_path = paths.get_instructions_path()
    
    assert instructions_path.exists(), f"Instructions file does not exist: {instructions_path}"
    assert instructions_path.is_file(), f"Instructions path is not a file: {instructions_path}"
    assert instructions_path.name == "instructions.md", f"Instructions file name should be 'instructions.md': {instructions_path}"

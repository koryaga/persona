#!/usr/bin/env python3
import importlib.resources as resources
import sys
from pathlib import Path


def get_skills_dir() -> Path:
    """Find skills directory - bundled in package or from project root."""
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', '')
        return Path(meipass) / 'skills'
    
    try:
        pkg_skills = resources.files('persona')
        if pkg_skills.is_dir():
            skills_path = pkg_skills / 'skills'
            if skills_path.is_dir():
                return Path(str(skills_path))
    except (TypeError, ModuleNotFoundError, AttributeError, FileNotFoundError):
        pass
    
    return Path(__file__).parent.parent.parent / 'skills'


def get_instructions_path() -> Path:
    """Find instructions.md - bundled in package or from project root."""
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', '')
        return Path(meipass) / 'instructions.md'
    
    try:
        pkg_instructions = resources.files('persona')
        if pkg_instructions.is_file():
            instructions_path = pkg_instructions / 'instructions.md'
            if instructions_path.is_file():
                return Path(str(instructions_path))
    except (TypeError, ModuleNotFoundError, AttributeError, FileNotFoundError):
        pass
    
    return Path(__file__).parent.parent.parent.parent / 'instructions.md'

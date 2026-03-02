#!/usr/bin/env python3
import os
import re
from pathlib import Path


def parse_skill(file_path: Path, skills_dir: Path):
    """Parse a single SKILL.md file and extract metadata."""
    with open(file_path, 'r') as file:
        content = file.read()
    
    match = re.search(r'^---$(.*?)^---$', content, re.DOTALL | re.MULTILINE)
    if match:
        metadata_block = match.group(1).strip().split('\n')
        metadata = dict(line.split(': ', 1) for line in metadata_block)
        
        relative_path = file_path.relative_to(skills_dir)
        container_path = f"/skills/{relative_path}"
        
        xml_output = (
            '<skill>\n'
            f'<name>{metadata["name"]}</name>\n'
            f'<description>{metadata["description"]}</description>\n'
            f'<location>{container_path}</location>\n'
            '</skill>'
        )
        return xml_output
    else:
        raise ValueError("Metadata section not found.")


def find_and_parse_skills(skills_dir: Path):
    """Find all SKILL.md files and parse them into XML."""
    skills_xml = []
    skill_files = []
    
    for root, _, files in os.walk(skills_dir, followlinks=True):
        for file in files:
            if file == "SKILL.md":
                skill_files.append(Path(root) / file)
    
    for skill_file in skill_files:
        try:
            xml_content = parse_skill(skill_file, skills_dir)
            skills_xml.append(xml_content)
        except Exception as e:
            print(f"Error parsing {skill_file}: {e}")
    
    return '\n'.join(skills_xml)

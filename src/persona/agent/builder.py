#!/usr/bin/env python3
import datetime
import os
from pathlib import Path
from typing import Optional

from pydantic_ai import Agent, ModelSettings
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from persona.config import paths
from persona.skills import parser


def create_agent(skills_dir: Path, model_settings: Optional[dict] = None):
    """Create and configure the agent."""
    instructions_path = paths.get_instructions_path()
    with open(instructions_path, 'r') as f:
        system_prompt = f.read()
    
    openai_model = os.getenv('OPENAI_MODEL', 'cogito:14b')
    openai_api_key = os.getenv('OPENAI_API_KEY', 'ollama')
    openai_api_base = os.getenv('OPENAI_API_BASE', 'http://localhost:11434/v1')
    
    if model_settings:
        model = OpenAIChatModel(
            openai_model,
            provider=OpenAIProvider(
                base_url=openai_api_base,
                api_key=openai_api_key,
            ),
            settings=ModelSettings(**model_settings),
        )
    else:
        model = OpenAIChatModel(
            openai_model,
            provider=OpenAIProvider(
                base_url=openai_api_base,
                api_key=openai_api_key,
            ),
            settings=ModelSettings(temperature=0, top_p=0),
        )
    
    def get_instructions() -> str:
        return (
            f"{system_prompt}"
            f"Current date and time: {datetime.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}"
            """ When users ask you to perform tasks, check if any of the available skills below can help complete the task more effectively.

            How to use skills:
            - Invoke skills using `load_skill` tool with the skill name only: load_skill <skill_name>
            - When you invoke a skill, you will see `Reading: <skill_name>`
            - The skill's prompt will expand and provide detailed instructions
            - Base directory provided in output for resolving bundled resources

            Usage notes:
            - Only use skills listed in Available_skills section below
            - Do not invoke a skill that is already loaded in your context
            """
            "Available_skills:"
            f"{parser.find_and_parse_skills(skills_dir)}"
            ""
        )
    
    agent = Agent(
        model,
        retries=5,
        instructions=get_instructions,
    )
    
    return agent

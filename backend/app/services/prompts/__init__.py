# backend/app/services/prompts/__init__.py
"""
Prompt-System für Claude API

Module:
- research_service: Dynamische Gebäude-Recherche mit Cache
- prompt_builder: Template-basierter Prompt-Aufbau

Stand: 29.12.2025
"""

from .research_service import (
    ClaudeResearchService,
    get_research_service,
    BuildingResearch,
)
from .prompt_builder import (
    PromptBuilder,
    get_prompt_builder,
)

__all__ = [
    "ClaudeResearchService",
    "get_research_service",
    "BuildingResearch",
    "PromptBuilder",
    "get_prompt_builder",
]

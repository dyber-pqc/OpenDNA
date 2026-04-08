"""Academy content: Levels 4-7, badges, daily challenges, glossary (Phase 14)."""
from .content import LEVELS, BADGES, GLOSSARY, get_level, list_levels
from .challenges import daily_challenge, check_answer, leaderboard_top, record_completion

__all__ = [
    "LEVELS", "BADGES", "GLOSSARY",
    "get_level", "list_levels",
    "daily_challenge", "check_answer", "leaderboard_top", "record_completion",
]

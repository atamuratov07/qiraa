"""Imports every model, so Base.metadata knows every table (Alembic, create_all).

Entry points (main, cli, migrations, tests) import this module. Feature code imports
models from their feature
"""

from app.auth.models import User, UserSession
from app.core.base import Base
from app.grammar.models import GrammarOption, GrammarQuestion
from app.passages.models import Passage, PassageOption, PassageQuestion
from app.practice.models import Attempt, AttemptAnswer

__all__ = [
    "Attempt",
    "AttemptAnswer",
    "Base",
    "GrammarOption",
    "GrammarQuestion",
    "Passage",
    "PassageOption",
    "PassageQuestion",
    "User",
    "UserSession",
]

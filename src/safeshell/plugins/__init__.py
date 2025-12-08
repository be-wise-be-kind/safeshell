"""
File: src/safeshell/plugins/__init__.py
Purpose: Plugin system package exports
Exports: Plugin, EvaluationResult, Decision
Depends: safeshell.plugins.base, safeshell.models
Overview: Re-exports plugin base class and related types for convenient imports
"""

from safeshell.models import Decision, EvaluationResult
from safeshell.plugins.base import Plugin

__all__ = ["Plugin", "EvaluationResult", "Decision"]

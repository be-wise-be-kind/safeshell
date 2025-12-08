"""
File: src/safeshell/rules/__init__.py
Purpose: Rules module for config-based policy evaluation
Exports: Rule, RuleAction, RuleSet, RuleEvaluator, load_rules, GLOBAL_RULES_PATH
Depends: safeshell.rules.schema, safeshell.rules.evaluator, safeshell.rules.loader
Overview: Public API for the rules module - YAML-based rule configuration system
"""

from safeshell.rules.defaults import DEFAULT_RULES_YAML
from safeshell.rules.evaluator import RuleEvaluator
from safeshell.rules.loader import GLOBAL_RULES_PATH, load_rules
from safeshell.rules.schema import Rule, RuleAction, RuleSet

__all__ = [
    "Rule",
    "RuleAction",
    "RuleSet",
    "RuleEvaluator",
    "load_rules",
    "GLOBAL_RULES_PATH",
    "DEFAULT_RULES_YAML",
]

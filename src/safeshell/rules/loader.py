"""
File: src/safeshell/rules/loader.py
Purpose: Load and merge rule files from global and repo locations
Exports: load_rules, GLOBAL_RULES_PATH
Depends: safeshell.rules.schema, safeshell.exceptions, safeshell.common, pyyaml, pathlib, loguru
Overview: Loads rules from ~/.safeshell/rules.yaml (global) and .safeshell/rules.yaml (repo)
"""

from pathlib import Path

import yaml
from loguru import logger
from pydantic import ValidationError

from safeshell.common import SAFESHELL_DIR
from safeshell.exceptions import RuleLoadError
from safeshell.rules.schema import Rule, RuleSet

GLOBAL_RULES_PATH = SAFESHELL_DIR / "rules.yaml"


def load_rules(working_dir: str | Path) -> list[Rule]:
    """Load and merge global and repo rules.

    Load order:
    1. Global rules (~/.safeshell/rules.yaml)
    2. Repo rules (.safeshell/rules.yaml in working_dir or parents)

    Repo rules are additive only - they cannot relax global rules.
    A malicious repo cannot disable your global protections.

    Args:
        working_dir: Current working directory for repo rule discovery

    Returns:
        Merged list of rules from all sources

    Raises:
        RuleLoadError: If a rules file exists but is invalid
    """
    rules: list[Rule] = []

    # 1. Load global rules (user's protections)
    if GLOBAL_RULES_PATH.exists():
        global_rules = _load_rule_file(GLOBAL_RULES_PATH)
        rules.extend(global_rules)
        logger.debug(f"Loaded {len(global_rules)} global rules")

    # 2. Load repo rules (additive only)
    repo_path = _find_repo_rules(Path(working_dir))
    if repo_path:
        repo_rules = _load_rule_file(repo_path)
        rules.extend(repo_rules)
        logger.debug(f"Loaded {len(repo_rules)} repo rules from {repo_path}")

    logger.info(f"Loaded {len(rules)} total rules")
    return rules


def _load_rule_file(path: Path) -> list[Rule]:
    """Load rules from a YAML file.

    Args:
        path: Path to the rules YAML file

    Returns:
        List of Rule objects from the file

    Raises:
        RuleLoadError: If the file is invalid YAML or fails validation
    """
    try:
        content = path.read_text()
        data = yaml.safe_load(content)

        if data is None:
            # Empty file
            return []

        ruleset = RuleSet.model_validate(data)
        return ruleset.rules

    except yaml.YAMLError as e:
        raise RuleLoadError(f"Invalid YAML in {path}: {e}") from e
    except ValidationError as e:
        raise RuleLoadError(f"Invalid rule schema in {path}: {e}") from e
    except OSError as e:
        raise RuleLoadError(f"Failed to read {path}: {e}") from e


def _find_repo_rules(working_dir: Path) -> Path | None:
    """Find .safeshell/rules.yaml in working_dir or parents.

    Walks up the directory tree looking for a .safeshell/rules.yaml file.
    Stops at the filesystem root.

    Args:
        working_dir: Starting directory for search

    Returns:
        Path to the repo rules file, or None if not found
    """
    current = working_dir.resolve()

    while current != current.parent:
        rules_path = current / ".safeshell" / "rules.yaml"
        if rules_path.exists():
            return rules_path
        current = current.parent

    return None

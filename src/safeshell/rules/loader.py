"""
File: src/safeshell/rules/loader.py
Purpose: Load and merge rule files from global and repo locations
Exports: load_rules, load_default_rules, GLOBAL_RULES_PATH, BUILTIN_RULE_SOURCES
Depends: safeshell.rules.schema, safeshell.rules.defaults, safeshell.rules.azure,
         safeshell.exceptions, safeshell.common, pyyaml, pathlib, loguru
Overview: Loads rules from built-in sources (defaults.py, azure.py),
          ~/.safeshell/rules.yaml, and .safeshell/rules.yaml
"""

from pathlib import Path

import yaml
from loguru import logger
from pydantic import ValidationError

from safeshell.common import SAFESHELL_DIR
from safeshell.exceptions import RuleLoadError
from safeshell.rules.azure import AZURE_RULES_YAML
from safeshell.rules.defaults import DEFAULT_RULES_YAML
from safeshell.rules.github import GITHUB_RULES_YAML
from safeshell.rules.schema import Rule, RuleSet

# All built-in rule sources, loaded in order
BUILTIN_RULE_SOURCES = [
    DEFAULT_RULES_YAML,
    AZURE_RULES_YAML,
    GITHUB_RULES_YAML,
]

GLOBAL_RULES_PATH = SAFESHELL_DIR / "rules.yaml"


class _DefaultRulesCache:
    """Simple cache for default rules parsed from code."""

    def __init__(self) -> None:
        self._rules: list[Rule] | None = None

    def get(self) -> list[Rule]:
        """Get cached default rules, parsing on first access.

        Loads rules from all built-in sources (defaults, azure, etc.)
        and combines them into a single list.
        """
        if self._rules is not None:
            return self._rules

        self._rules = []
        for source_yaml in BUILTIN_RULE_SOURCES:
            try:
                data = yaml.safe_load(source_yaml)
                if data is not None:
                    ruleset = RuleSet.model_validate(data)
                    self._rules.extend(ruleset.rules)
            except yaml.YAMLError as e:
                logger.error(f"Invalid YAML in built-in rules: {e}")
            except ValidationError as e:
                logger.error(f"Invalid schema in built-in rules: {e}")

        logger.debug(f"Parsed {len(self._rules)} default rules from code")
        return self._rules


_default_rules_cache = _DefaultRulesCache()


def get_builtin_rules_yaml() -> str:
    """Get combined YAML string of all built-in rules for writing to rules.yaml.

    This combines DEFAULT_RULES_YAML and other built-in sources (like azure.py)
    into a single YAML string suitable for writing to ~/.safeshell/rules.yaml.

    Returns:
        Combined YAML string with all built-in rules
    """
    # Start with the default rules YAML (includes header comments)
    combined = DEFAULT_RULES_YAML

    # For additional sources, extract just the rules and append them
    for source_yaml in BUILTIN_RULE_SOURCES[1:]:  # Skip defaults, already included
        # Parse to get the rules list
        data = yaml.safe_load(source_yaml)
        if data and "rules" in data:
            # Extract comment header from the source (everything before 'rules:')
            header_end = source_yaml.find("rules:")
            if header_end > 0:
                header = source_yaml[:header_end].strip()
                combined += f"\n\n{header}\n"

            # Serialize just the rules as YAML list items
            rules_yaml = yaml.dump(
                data["rules"],
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
            # Indent and format as list continuation
            combined += "\n"
            for line in rules_yaml.strip().split("\n"):
                combined += f"  {line}\n"

    return combined


def load_default_rules() -> list[Rule]:
    """Load the built-in default rules from code.

    Returns:
        List of default Rule objects shipped with SafeShell
    """
    return _default_rules_cache.get()


def load_rules(working_dir: str | Path) -> list[Rule]:
    """Load and merge default, global, and repo rules.

    Load order:
    1. Default rules (built-in, from defaults.py)
    2. Global rules (~/.safeshell/rules.yaml)
    3. Repo rules (.safeshell/rules.yaml in working_dir or parents)

    Rules are additive - later rules can add restrictions but cannot relax earlier ones.
    A malicious repo cannot disable your global protections.

    Args:
        working_dir: Current working directory for repo rule discovery

    Returns:
        Merged list of rules from all sources

    Raises:
        RuleLoadError: If a rules file exists but is invalid
    """
    rules: list[Rule] = []

    # 1. Load default rules (shipped with SafeShell)
    default_rules = load_default_rules()
    rules.extend(default_rules)
    logger.debug(f"Loaded {len(default_rules)} default rules")

    # 2. Load global rules (user's protections)
    if GLOBAL_RULES_PATH.exists():
        global_rules = _load_rule_file(GLOBAL_RULES_PATH)
        rules.extend(global_rules)
        logger.debug(f"Loaded {len(global_rules)} global rules")

    # 3. Load repo rules (additive only)
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

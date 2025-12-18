"""
File: src/safeshell/rules/loader.py
Purpose: Load and merge rule files from global and repo locations
Exports: load_rules, load_default_rules, _apply_overrides, GLOBAL_RULES_PATH, BUILTIN_RULE_SOURCES
Depends: safeshell.rules.schema, safeshell.rules.defaults, safeshell.rules.azure,
         safeshell.exceptions, safeshell.common, pyyaml, pathlib, loguru
Overview: Loads rules from built-in sources (defaults.py, azure.py),
          ~/.safeshell/rules.yaml, and .safeshell/rules.yaml
"""

from pathlib import Path
from typing import Any

import yaml
from loguru import logger
from pydantic import ValidationError

from safeshell.common import SAFESHELL_DIR
from safeshell.exceptions import OverrideError, RuleLoadError
from safeshell.rules.azure import AZURE_RULES_YAML
from safeshell.rules.defaults import DEFAULT_RULES_YAML
from safeshell.rules.github import GITHUB_RULES_YAML
from safeshell.rules.schema import Rule, RuleOverride, RuleSet

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


def _apply_overrides(
    rules: list[Rule],
    overrides: list[RuleOverride],
    source_path: str,
) -> list[Rule]:
    """Apply overrides to a list of rules.

    Overrides are applied in order. A rule can be:
    - Disabled (removed from list)
    - Modified (properties updated)

    Args:
        rules: The current rule list to modify
        overrides: List of overrides to apply
        source_path: Path of the file containing overrides (for error messages)

    Returns:
        New list of rules with overrides applied

    Raises:
        OverrideError: If an override references a non-existent rule
    """
    if not overrides:
        return rules

    # Build name -> rule index for efficient lookup
    rule_by_name: dict[str, Rule] = {r.name: r for r in rules}

    # Track which rules to remove
    rules_to_remove: set[str] = set()

    # Track modifications
    modifications: dict[str, dict[str, Any]] = {}

    for override in overrides:
        if override.name not in rule_by_name:
            available = ", ".join(sorted(rule_by_name.keys())[:10])
            raise OverrideError(
                f"Override in {source_path} references non-existent rule '{override.name}'. "
                f"Available rules: {available}..."
            )

        if override.disabled:
            rules_to_remove.add(override.name)
            logger.info(f"Override: disabling rule '{override.name}' from {source_path}")
        else:
            # Collect modifications
            mods: dict[str, Any] = {}
            if override.action is not None:
                mods["action"] = override.action
            if override.message is not None:
                mods["message"] = override.message
            if override.context is not None:
                mods["context"] = override.context
            if override.allow_override is not None:
                mods["allow_override"] = override.allow_override

            if mods:
                modifications[override.name] = mods
                logger.info(
                    f"Override: modifying rule '{override.name}' "
                    f"({list(mods.keys())}) from {source_path}"
                )

    # Apply modifications and filter out disabled rules
    result: list[Rule] = []
    for rule in rules:
        if rule.name in rules_to_remove:
            continue

        if rule.name in modifications:
            # Create modified copy using model_copy
            rule = rule.model_copy(update=modifications[rule.name])

        result.append(rule)

    return result


def load_rules(working_dir: str | Path) -> list[Rule]:
    """Load and merge default, global, and repo rules with overrides.

    Load order with overrides:
    1. Default rules (built-in, from defaults.py)
    2. Global rules (~/.safeshell/rules.yaml) - can override defaults
    3. Repo rules (.safeshell/rules.yaml) - can add rules but NOT override

    Security: Repo rules can only ADD restrictions, never weaken.
    Global rules can disable/modify default rules since user controls them.

    Args:
        working_dir: Current working directory for repo rule discovery

    Returns:
        Merged list of rules from all sources

    Raises:
        RuleLoadError: If a rules file exists but is invalid
        OverrideError: If an override references a non-existent rule
    """
    rules: list[Rule] = []

    # 1. Load default rules (shipped with SafeShell)
    default_rules = load_default_rules()
    rules.extend(default_rules)
    logger.debug(f"Loaded {len(default_rules)} default rules")

    # 2. Load global rules with overrides (user's protections)
    if GLOBAL_RULES_PATH.exists():
        global_rules, global_overrides = _load_rule_file(GLOBAL_RULES_PATH)

        # Apply global overrides to default rules
        if global_overrides:
            rules = _apply_overrides(rules, global_overrides, str(GLOBAL_RULES_PATH))
            logger.debug(f"Applied {len(global_overrides)} global overrides")

        rules.extend(global_rules)
        logger.debug(f"Loaded {len(global_rules)} global rules")

    # 3. Load repo rules (additive only - no overrides allowed for security)
    repo_path = _find_repo_rules(Path(working_dir))
    if repo_path:
        repo_rules, repo_overrides = _load_rule_file(repo_path)

        # SECURITY: Ignore repo overrides - malicious repo cannot weaken protections
        if repo_overrides:
            logger.warning(
                f"Ignoring {len(repo_overrides)} overrides in repo rules ({repo_path}). "
                "Repo rules cannot override default or global rules for security reasons."
            )

        rules.extend(repo_rules)
        logger.debug(f"Loaded {len(repo_rules)} repo rules from {repo_path}")

    logger.info(f"Loaded {len(rules)} total rules")
    return rules


def _load_rule_file(path: Path) -> tuple[list[Rule], list[RuleOverride]]:
    """Load rules and overrides from a YAML file.

    Args:
        path: Path to the rules YAML file

    Returns:
        Tuple of (rules list, overrides list)

    Raises:
        RuleLoadError: If the file is invalid YAML or fails validation
    """
    try:
        content = path.read_text()
        data = yaml.safe_load(content)

        if data is None:
            # Empty file
            return [], []

        ruleset = RuleSet.model_validate(data)
        return ruleset.rules, ruleset.overrides

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

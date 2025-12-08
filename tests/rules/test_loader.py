"""Tests for rules loader."""

from pathlib import Path
from unittest.mock import patch

import pytest

from safeshell.exceptions import RuleLoadError
from safeshell.rules.loader import (
    _find_repo_rules,
    _load_rule_file,
    load_rules,
)
from safeshell.rules.schema import RuleAction


class TestLoadRuleFile:
    """Tests for _load_rule_file function."""

    def test_load_valid_yaml(self, tmp_path: Path) -> None:
        """Test loading a valid rules YAML file."""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
rules:
  - name: test-rule
    commands: ["git"]
    action: deny
    message: "Blocked"
""")
        rules = _load_rule_file(rules_file)
        assert len(rules) == 1
        assert rules[0].name == "test-rule"
        assert rules[0].action == RuleAction.DENY

    def test_load_empty_file(self, tmp_path: Path) -> None:
        """Test loading an empty rules file returns empty list."""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("")
        rules = _load_rule_file(rules_file)
        assert rules == []

    def test_load_file_with_empty_rules(self, tmp_path: Path) -> None:
        """Test loading a file with empty rules list."""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("rules: []")
        rules = _load_rule_file(rules_file)
        assert rules == []

    def test_load_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """Test that invalid YAML raises RuleLoadError."""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("invalid: yaml: [")
        with pytest.raises(RuleLoadError) as exc_info:
            _load_rule_file(rules_file)
        assert "Invalid YAML" in str(exc_info.value)

    def test_load_invalid_schema_raises(self, tmp_path: Path) -> None:
        """Test that invalid rule schema raises RuleLoadError."""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
rules:
  - name: invalid-rule
    commands: []
    action: deny
    message: "Missing commands"
""")
        with pytest.raises(RuleLoadError) as exc_info:
            _load_rule_file(rules_file)
        assert "Invalid rule schema" in str(exc_info.value)

    def test_load_multiple_rules(self, tmp_path: Path) -> None:
        """Test loading multiple rules from one file."""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
rules:
  - name: rule1
    commands: ["git"]
    action: deny
    message: "Rule 1"
  - name: rule2
    commands: ["rm"]
    action: require_approval
    message: "Rule 2"
  - name: rule3
    commands: ["curl"]
    action: redirect
    redirect_to: "curl-wrapper $ARGS"
    message: "Rule 3"
""")
        rules = _load_rule_file(rules_file)
        assert len(rules) == 3
        assert rules[0].name == "rule1"
        assert rules[1].name == "rule2"
        assert rules[2].name == "rule3"


class TestFindRepoRules:
    """Tests for _find_repo_rules function."""

    def test_find_rules_in_current_dir(self, tmp_path: Path) -> None:
        """Test finding rules in current directory."""
        rules_dir = tmp_path / ".safeshell"
        rules_dir.mkdir()
        rules_file = rules_dir / "rules.yaml"
        rules_file.write_text("rules: []")

        result = _find_repo_rules(tmp_path)
        assert result == rules_file

    def test_find_rules_in_parent_dir(self, tmp_path: Path) -> None:
        """Test finding rules in parent directory."""
        # Create rules in parent
        rules_dir = tmp_path / ".safeshell"
        rules_dir.mkdir()
        rules_file = rules_dir / "rules.yaml"
        rules_file.write_text("rules: []")

        # Look from subdirectory
        subdir = tmp_path / "src" / "deep"
        subdir.mkdir(parents=True)

        result = _find_repo_rules(subdir)
        assert result == rules_file

    def test_no_rules_returns_none(self, tmp_path: Path) -> None:
        """Test that missing rules returns None."""
        result = _find_repo_rules(tmp_path)
        assert result is None


class TestLoadRules:
    """Tests for load_rules function."""

    def test_load_global_rules(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading global rules only."""
        # Set up global rules
        global_dir = tmp_path / "global" / ".safeshell"
        global_dir.mkdir(parents=True)
        global_rules = global_dir / "rules.yaml"
        global_rules.write_text("""
rules:
  - name: global-rule
    commands: ["git"]
    action: deny
    message: "Global block"
""")

        # Patch GLOBAL_RULES_PATH
        with patch("safeshell.rules.loader.GLOBAL_RULES_PATH", global_rules):
            rules = load_rules(tmp_path)

        assert len(rules) == 1
        assert rules[0].name == "global-rule"

    def test_load_repo_rules(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading repo rules only (no global rules)."""
        # Set up repo rules
        repo_dir = tmp_path / ".safeshell"
        repo_dir.mkdir()
        repo_rules = repo_dir / "rules.yaml"
        repo_rules.write_text("""
rules:
  - name: repo-rule
    commands: ["rm"]
    action: deny
    message: "Repo block"
""")

        # Patch GLOBAL_RULES_PATH to non-existent file
        nonexistent = tmp_path / "nonexistent" / "rules.yaml"
        with patch("safeshell.rules.loader.GLOBAL_RULES_PATH", nonexistent):
            rules = load_rules(tmp_path)

        assert len(rules) == 1
        assert rules[0].name == "repo-rule"

    def test_merge_global_and_repo_rules(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test merging global and repo rules."""
        # Set up global rules
        global_dir = tmp_path / "global" / ".safeshell"
        global_dir.mkdir(parents=True)
        global_rules = global_dir / "rules.yaml"
        global_rules.write_text("""
rules:
  - name: global-rule
    commands: ["git"]
    action: deny
    message: "Global block"
""")

        # Set up repo rules
        repo_dir = tmp_path / "repo" / ".safeshell"
        repo_dir.mkdir(parents=True)
        repo_rules = repo_dir / "rules.yaml"
        repo_rules.write_text("""
rules:
  - name: repo-rule
    commands: ["rm"]
    action: deny
    message: "Repo block"
""")

        # Patch GLOBAL_RULES_PATH
        with patch("safeshell.rules.loader.GLOBAL_RULES_PATH", global_rules):
            rules = load_rules(tmp_path / "repo")

        assert len(rules) == 2
        rule_names = [r.name for r in rules]
        assert "global-rule" in rule_names
        assert "repo-rule" in rule_names

    def test_no_rules_returns_empty_list(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing rules files returns empty list."""
        nonexistent = tmp_path / "nonexistent" / "rules.yaml"
        with patch("safeshell.rules.loader.GLOBAL_RULES_PATH", nonexistent):
            rules = load_rules(tmp_path)
        assert rules == []

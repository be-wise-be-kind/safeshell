"""Tests for rules loader."""

from pathlib import Path
from unittest.mock import patch

import pytest

from safeshell.exceptions import OverrideError, RuleLoadError
from safeshell.rules.loader import (
    _apply_overrides,
    _find_repo_rules,
    _load_rule_file,
    load_rules,
)
from safeshell.rules.schema import Rule, RuleAction, RuleContext, RuleOverride


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
        rules, overrides = _load_rule_file(rules_file)
        assert len(rules) == 1
        assert rules[0].name == "test-rule"
        assert rules[0].action == RuleAction.DENY
        assert overrides == []

    def test_load_empty_file(self, tmp_path: Path) -> None:
        """Test loading an empty rules file returns empty lists."""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("")
        rules, overrides = _load_rule_file(rules_file)
        assert rules == []
        assert overrides == []

    def test_load_file_with_empty_rules(self, tmp_path: Path) -> None:
        """Test loading a file with empty rules list."""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("rules: []")
        rules, overrides = _load_rule_file(rules_file)
        assert rules == []
        assert overrides == []

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
        rules, overrides = _load_rule_file(rules_file)
        assert len(rules) == 3
        assert rules[0].name == "rule1"
        assert rules[1].name == "rule2"
        assert rules[2].name == "rule3"
        assert overrides == []

    def test_load_rules_with_overrides(self, tmp_path: Path) -> None:
        """Test loading a file with both rules and overrides."""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
rules:
  - name: custom-rule
    commands: ["echo"]
    action: deny
    message: "Custom"
overrides:
  - name: some-default-rule
    disabled: true
""")
        rules, overrides = _load_rule_file(rules_file)
        assert len(rules) == 1
        assert len(overrides) == 1
        assert overrides[0].name == "some-default-rule"
        assert overrides[0].disabled is True


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

        # Patch GLOBAL_RULES_PATH and mock out default rules
        with (
            patch("safeshell.rules.loader.GLOBAL_RULES_PATH", global_rules),
            patch("safeshell.rules.loader.load_default_rules", return_value=[]),
        ):
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

        # Patch GLOBAL_RULES_PATH to non-existent file and mock out default rules
        nonexistent = tmp_path / "nonexistent" / "rules.yaml"
        with (
            patch("safeshell.rules.loader.GLOBAL_RULES_PATH", nonexistent),
            patch("safeshell.rules.loader.load_default_rules", return_value=[]),
        ):
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

        # Patch GLOBAL_RULES_PATH and mock out default rules
        with (
            patch("safeshell.rules.loader.GLOBAL_RULES_PATH", global_rules),
            patch("safeshell.rules.loader.load_default_rules", return_value=[]),
        ):
            rules = load_rules(tmp_path / "repo")

        assert len(rules) == 2
        rule_names = [r.name for r in rules]
        assert "global-rule" in rule_names
        assert "repo-rule" in rule_names

    def test_no_rules_returns_empty_list(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing rules files returns empty list (when no defaults)."""
        nonexistent = tmp_path / "nonexistent" / "rules.yaml"
        with (
            patch("safeshell.rules.loader.GLOBAL_RULES_PATH", nonexistent),
            patch("safeshell.rules.loader.load_default_rules", return_value=[]),
        ):
            rules = load_rules(tmp_path)
        assert rules == []

    def test_default_rules_loaded_first(self, tmp_path: Path) -> None:
        """Test that default rules are always loaded first."""
        # Set up global rules
        global_dir = tmp_path / "global" / ".safeshell"
        global_dir.mkdir(parents=True)
        global_rules = global_dir / "rules.yaml"
        global_rules.write_text("""
rules:
  - name: user-rule
    commands: ["echo"]
    action: deny
    message: "User block"
""")

        # Load rules with defaults (don't mock them out)
        with patch("safeshell.rules.loader.GLOBAL_RULES_PATH", global_rules):
            rules = load_rules(tmp_path)

        # Should have 49 default rules + 1 user rule
        assert len(rules) >= 50
        # Default rules should come first
        assert rules[0].name == "deny-rm-rf-root"
        # User rule should be at the end
        assert rules[-1].name == "user-rule"


class TestApplyOverrides:
    """Tests for _apply_overrides function."""

    def test_disable_rule(self) -> None:
        """Test disabling a rule removes it from the list."""
        rules = [
            Rule(
                name="rule-1",
                commands=["git"],
                action=RuleAction.DENY,
                message="Rule 1",
            ),
            Rule(
                name="rule-2",
                commands=["rm"],
                action=RuleAction.DENY,
                message="Rule 2",
            ),
        ]
        overrides = [RuleOverride(name="rule-1", disabled=True)]

        result = _apply_overrides(rules, overrides, "test.yaml")

        assert len(result) == 1
        assert result[0].name == "rule-2"

    def test_modify_action(self) -> None:
        """Test modifying a rule's action."""
        rules = [
            Rule(
                name="rule-1",
                commands=["git"],
                action=RuleAction.DENY,
                message="Rule 1",
            ),
        ]
        overrides = [RuleOverride(name="rule-1", action=RuleAction.REQUIRE_APPROVAL)]

        result = _apply_overrides(rules, overrides, "test.yaml")

        assert len(result) == 1
        assert result[0].action == RuleAction.REQUIRE_APPROVAL
        assert result[0].message == "Rule 1"  # Unchanged

    def test_modify_multiple_properties(self) -> None:
        """Test modifying multiple properties at once."""
        rules = [
            Rule(
                name="rule-1",
                commands=["git"],
                action=RuleAction.DENY,
                message="Original message",
                context=RuleContext.ALL,
            ),
        ]
        overrides = [
            RuleOverride(
                name="rule-1",
                action=RuleAction.ALLOW,
                message="Modified message",
                context=RuleContext.AI_ONLY,
            )
        ]

        result = _apply_overrides(rules, overrides, "test.yaml")

        assert result[0].action == RuleAction.ALLOW
        assert result[0].message == "Modified message"
        assert result[0].context == RuleContext.AI_ONLY

    def test_nonexistent_rule_raises(self) -> None:
        """Test that overriding non-existent rule raises OverrideError."""
        rules = [
            Rule(
                name="rule-1",
                commands=["git"],
                action=RuleAction.DENY,
                message="Rule 1",
            ),
        ]
        overrides = [RuleOverride(name="nonexistent", disabled=True)]

        with pytest.raises(OverrideError) as exc_info:
            _apply_overrides(rules, overrides, "test.yaml")

        assert "non-existent rule 'nonexistent'" in str(exc_info.value)
        assert "rule-1" in str(exc_info.value)  # Shows available rules

    def test_original_rules_unchanged(self) -> None:
        """Test that original rule objects are not mutated."""
        original_rule = Rule(
            name="rule-1",
            commands=["git"],
            action=RuleAction.DENY,
            message="Original",
        )
        rules = [original_rule]
        overrides = [RuleOverride(name="rule-1", action=RuleAction.ALLOW)]

        result = _apply_overrides(rules, overrides, "test.yaml")

        # Original unchanged
        assert original_rule.action == RuleAction.DENY
        # Result modified
        assert result[0].action == RuleAction.ALLOW

    def test_empty_overrides_returns_same_rules(self) -> None:
        """Test that empty overrides list returns rules unchanged."""
        rules = [
            Rule(
                name="rule-1",
                commands=["git"],
                action=RuleAction.DENY,
                message="Rule 1",
            ),
        ]
        overrides: list[RuleOverride] = []

        result = _apply_overrides(rules, overrides, "test.yaml")

        assert len(result) == 1
        assert result[0].name == "rule-1"


class TestLoadRulesWithOverrides:
    """Integration tests for load_rules with overrides."""

    def test_global_override_disables_default(self, tmp_path: Path) -> None:
        """Test global rules can disable default rules."""
        global_rules = tmp_path / "rules.yaml"
        global_rules.write_text("""
rules: []
overrides:
  - name: deny-rm-rf-root
    disabled: true
""")

        with patch("safeshell.rules.loader.GLOBAL_RULES_PATH", global_rules):
            rules = load_rules(tmp_path)

        rule_names = {r.name for r in rules}
        assert "deny-rm-rf-root" not in rule_names

    def test_global_override_modifies_default(self, tmp_path: Path) -> None:
        """Test global rules can modify default rule action."""
        global_rules = tmp_path / "rules.yaml"
        global_rules.write_text("""
rules: []
overrides:
  - name: approve-force-push
    action: allow
""")

        with patch("safeshell.rules.loader.GLOBAL_RULES_PATH", global_rules):
            rules = load_rules(tmp_path)

        force_push_rule = next(r for r in rules if r.name == "approve-force-push")
        assert force_push_rule.action == RuleAction.ALLOW

    def test_repo_overrides_ignored(self, tmp_path: Path) -> None:
        """Test repo rules cannot override (security)."""
        repo_dir = tmp_path / ".safeshell"
        repo_dir.mkdir()
        repo_rules = repo_dir / "rules.yaml"
        repo_rules.write_text("""
rules: []
overrides:
  - name: deny-rm-rf-root
    disabled: true
""")

        nonexistent = tmp_path / "nonexistent" / "rules.yaml"
        with patch("safeshell.rules.loader.GLOBAL_RULES_PATH", nonexistent):
            rules = load_rules(tmp_path)

        # Rule should still exist - repo overrides are ignored
        rule_names = {r.name for r in rules}
        assert "deny-rm-rf-root" in rule_names

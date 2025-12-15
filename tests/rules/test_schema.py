"""Tests for rules schema models."""

import pytest
from pydantic import ValidationError

from safeshell.rules.condition_types import CommandMatches, FileExists
from safeshell.rules.schema import Rule, RuleAction, RuleSet


class TestRuleAction:
    """Tests for RuleAction enum."""

    def test_action_values(self) -> None:
        """Test that all action values are correct."""
        assert RuleAction.ALLOW.value == "allow"
        assert RuleAction.DENY.value == "deny"
        assert RuleAction.REQUIRE_APPROVAL.value == "require_approval"
        assert RuleAction.REDIRECT.value == "redirect"

    def test_action_from_string(self) -> None:
        """Test creating action from string value."""
        assert RuleAction("deny") == RuleAction.DENY
        assert RuleAction("require_approval") == RuleAction.REQUIRE_APPROVAL


class TestRule:
    """Tests for Rule model."""

    def test_minimal_valid_rule(self) -> None:
        """Test creating a rule with minimal required fields."""
        rule = Rule(
            name="test-rule",
            commands=["git"],
            action=RuleAction.DENY,
            message="Test message",
        )
        assert rule.name == "test-rule"
        assert rule.commands == ["git"]
        assert rule.action == RuleAction.DENY
        assert rule.message == "Test message"
        assert rule.conditions == []
        assert rule.directory is None
        assert rule.allow_override is True
        assert rule.redirect_to is None

    def test_full_rule_with_all_fields(self) -> None:
        """Test creating a rule with all fields specified."""
        rule = Rule(
            name="full-rule",
            commands=["git", "rm"],
            directory=r"/home/user/.*",
            conditions=[
                FileExists(file_exists=".gitignore"),
                CommandMatches(command_matches=r"^git\s+status"),
            ],
            action=RuleAction.REQUIRE_APPROVAL,
            allow_override=False,
            message="Approval needed",
        )
        assert rule.name == "full-rule"
        assert rule.commands == ["git", "rm"]
        assert rule.directory == r"/home/user/.*"
        assert len(rule.conditions) == 2
        assert rule.action == RuleAction.REQUIRE_APPROVAL
        assert rule.allow_override is False

    def test_redirect_rule_requires_redirect_to(self) -> None:
        """Test that redirect action requires redirect_to field."""
        with pytest.raises(ValidationError) as exc_info:
            Rule(
                name="redirect-rule",
                commands=["rm"],
                action=RuleAction.REDIRECT,
                message="Redirect message",
                # Missing redirect_to
            )
        assert "redirect_to is required" in str(exc_info.value)

    def test_redirect_rule_with_redirect_to(self) -> None:
        """Test that redirect action works with redirect_to field."""
        rule = Rule(
            name="redirect-rule",
            commands=["rm"],
            action=RuleAction.REDIRECT,
            redirect_to="trash $ARGS",
            message="Redirecting to trash",
        )
        assert rule.action == RuleAction.REDIRECT
        assert rule.redirect_to == "trash $ARGS"

    def test_empty_commands_raises(self) -> None:
        """Test that empty commands list raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Rule(
                name="empty-commands",
                commands=[],
                action=RuleAction.DENY,
                message="Test",
            )
        assert "At least one command must be specified" in str(exc_info.value)

    def test_rule_from_dict(self) -> None:
        """Test creating rule from dictionary (as would be loaded from YAML)."""
        data = {
            "name": "dict-rule",
            "commands": ["git"],
            "conditions": [{"command_matches": r"^git\s+status"}],
            "action": "deny",
            "message": "Blocked",
        }
        rule = Rule.model_validate(data)
        assert rule.name == "dict-rule"
        assert rule.action == RuleAction.DENY
        assert len(rule.conditions) == 1
        assert isinstance(rule.conditions[0], CommandMatches)


class TestRuleSet:
    """Tests for RuleSet model."""

    def test_empty_ruleset(self) -> None:
        """Test creating an empty ruleset."""
        ruleset = RuleSet()
        assert ruleset.rules == []

    def test_ruleset_with_rules(self) -> None:
        """Test creating a ruleset with multiple rules."""
        rules = [
            Rule(
                name="rule1",
                commands=["git"],
                action=RuleAction.DENY,
                message="Message 1",
            ),
            Rule(
                name="rule2",
                commands=["rm"],
                action=RuleAction.REQUIRE_APPROVAL,
                message="Message 2",
            ),
        ]
        ruleset = RuleSet(rules=rules)
        assert len(ruleset.rules) == 2

    def test_ruleset_from_yaml_dict(self) -> None:
        """Test creating ruleset from YAML-like dictionary."""
        data = {
            "rules": [
                {
                    "name": "rule1",
                    "commands": ["git"],
                    "action": "deny",
                    "message": "Blocked",
                },
                {
                    "name": "rule2",
                    "commands": ["rm"],
                    "action": "require_approval",
                    "message": "Approval needed",
                },
            ]
        }
        ruleset = RuleSet.model_validate(data)
        assert len(ruleset.rules) == 2
        assert ruleset.rules[0].name == "rule1"
        assert ruleset.rules[1].action == RuleAction.REQUIRE_APPROVAL

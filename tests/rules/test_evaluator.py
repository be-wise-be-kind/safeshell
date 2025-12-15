"""Tests for rules evaluator."""

# ruff: noqa: S108 - /tmp usage is fine in tests

import pytest

from safeshell.models import CommandContext, Decision
from safeshell.rules.condition_types import CommandContains, CommandMatches, GitBranchIn
from safeshell.rules.evaluator import RuleEvaluator
from safeshell.rules.schema import Rule, RuleAction


class TestRuleEvaluator:
    """Tests for RuleEvaluator class."""

    @pytest.fixture
    def simple_deny_rule(self) -> Rule:
        """A simple deny rule for git commands."""
        return Rule(
            name="block-git",
            commands=["git"],
            action=RuleAction.DENY,
            message="Git blocked",
        )

    @pytest.fixture
    def simple_context(self) -> CommandContext:
        """A simple command context."""
        return CommandContext.from_command("git status", "/tmp")

    @pytest.mark.asyncio
    async def test_fast_path_allows_unmatched_commands(self) -> None:
        """Test that commands not in any rule are allowed immediately."""
        rules = [
            Rule(
                name="block-git",
                commands=["git"],
                action=RuleAction.DENY,
                message="Git blocked",
            )
        ]
        evaluator = RuleEvaluator(rules)
        context = CommandContext.from_command("ls -la", "/tmp")

        result = await evaluator.evaluate(context)

        assert result.decision == Decision.ALLOW
        assert "No rules apply" in result.reason

    @pytest.mark.asyncio
    async def test_matching_command_applies_rule(self) -> None:
        """Test that a matching command applies the rule action."""
        rules = [
            Rule(
                name="block-git",
                commands=["git"],
                action=RuleAction.DENY,
                message="Git blocked",
            )
        ]
        evaluator = RuleEvaluator(rules)
        context = CommandContext.from_command("git status", "/tmp")

        result = await evaluator.evaluate(context)

        assert result.decision == Decision.DENY
        assert result.plugin_name == "block-git"
        assert result.reason == "Git blocked"

    @pytest.mark.asyncio
    async def test_require_approval_action(self) -> None:
        """Test that REQUIRE_APPROVAL action works."""
        rules = [
            Rule(
                name="approve-git",
                commands=["git"],
                action=RuleAction.REQUIRE_APPROVAL,
                message="Needs approval",
            )
        ]
        evaluator = RuleEvaluator(rules)
        context = CommandContext.from_command("git push", "/tmp")

        result = await evaluator.evaluate(context)

        assert result.decision == Decision.REQUIRE_APPROVAL
        assert result.reason == "Needs approval"


class TestStructuredConditions:
    """Tests for structured condition evaluation."""

    @pytest.mark.asyncio
    async def test_condition_passes(self) -> None:
        """Test that a passing condition matches the rule."""
        rules = [
            Rule(
                name="test-rule",
                commands=["echo"],
                conditions=[CommandContains(command_contains="hello")],
                action=RuleAction.DENY,
                message="Blocked",
            )
        ]
        evaluator = RuleEvaluator(rules)
        context = CommandContext.from_command("echo hello", "/tmp")

        result = await evaluator.evaluate(context)

        assert result.decision == Decision.DENY

    @pytest.mark.asyncio
    async def test_condition_fails(self) -> None:
        """Test that a failing condition skips the rule."""
        rules = [
            Rule(
                name="test-rule",
                commands=["echo"],
                conditions=[CommandContains(command_contains="goodbye")],
                action=RuleAction.DENY,
                message="Blocked",
            )
        ]
        evaluator = RuleEvaluator(rules)
        context = CommandContext.from_command("echo hello", "/tmp")

        result = await evaluator.evaluate(context)

        assert result.decision == Decision.ALLOW
        assert "No rules matched" in result.reason

    @pytest.mark.asyncio
    async def test_multiple_conditions_all_must_pass(self) -> None:
        """Test that all conditions must pass for rule to match."""
        rules = [
            Rule(
                name="test-rule",
                commands=["git"],
                conditions=[
                    CommandMatches(command_matches=r"^git\s+commit"),
                    CommandContains(command_contains="message"),
                    CommandContains(command_contains="nonexistent"),  # This fails
                ],
                action=RuleAction.DENY,
                message="Blocked",
            )
        ]
        evaluator = RuleEvaluator(rules)
        context = CommandContext.from_command("git commit -m message", "/tmp")

        result = await evaluator.evaluate(context)

        assert result.decision == Decision.ALLOW

    @pytest.mark.asyncio
    async def test_command_matches_condition(self) -> None:
        """Test that command_matches condition works."""
        rules = [
            Rule(
                name="check-cmd",
                commands=["git"],
                conditions=[CommandMatches(command_matches=r"commit")],
                action=RuleAction.DENY,
                message="Blocked commit",
            )
        ]
        evaluator = RuleEvaluator(rules)

        # Should match - command contains "commit"
        context = CommandContext.from_command("git commit -m test", "/tmp")
        result = await evaluator.evaluate(context)
        assert result.decision == Decision.DENY

        # Should not match - command doesn't contain "commit"
        context = CommandContext.from_command("git status", "/tmp")
        result = await evaluator.evaluate(context)
        assert result.decision == Decision.ALLOW

    @pytest.mark.asyncio
    async def test_git_branch_in_condition(self) -> None:
        """Test that git_branch_in condition works."""
        from safeshell.models import ExecutionContext

        rules = [
            Rule(
                name="check-branch",
                commands=["git"],
                conditions=[GitBranchIn(git_branch_in=["main", "master"])],
                action=RuleAction.DENY,
                message="Blocked on protected branch",
            )
        ]
        evaluator = RuleEvaluator(rules)

        # Should match - on main branch
        context = CommandContext(
            raw_command="git commit",
            parsed_args=["git", "commit"],
            working_dir="/tmp",
            git_repo_root="/tmp",
            git_branch="main",
            environment={},
            execution_context=ExecutionContext.HUMAN,
        )
        result = await evaluator.evaluate(context)
        assert result.decision == Decision.DENY

        # Should not match - on feature branch
        context = CommandContext(
            raw_command="git commit",
            parsed_args=["git", "commit"],
            working_dir="/tmp",
            git_repo_root="/tmp",
            git_branch="feature/new-thing",
            environment={},
            execution_context=ExecutionContext.HUMAN,
        )
        result = await evaluator.evaluate(context)
        assert result.decision == Decision.ALLOW


class TestDirectoryPattern:
    """Tests for directory pattern matching."""

    @pytest.mark.asyncio
    async def test_directory_pattern_matches(self) -> None:
        """Test that directory pattern matches correctly."""
        rules = [
            Rule(
                name="project-rule",
                commands=["git"],
                directory=r"/tmp/project.*",
                action=RuleAction.DENY,
                message="Blocked in project",
            )
        ]
        evaluator = RuleEvaluator(rules)

        # Should match
        context = CommandContext.from_command("git status", "/tmp/project-foo")
        result = await evaluator.evaluate(context)
        assert result.decision == Decision.DENY

    @pytest.mark.asyncio
    async def test_directory_pattern_no_match(self) -> None:
        """Test that non-matching directory skips rule."""
        rules = [
            Rule(
                name="project-rule",
                commands=["git"],
                directory=r"/tmp/project.*",
                action=RuleAction.DENY,
                message="Blocked in project",
            )
        ]
        evaluator = RuleEvaluator(rules)

        # Should not match - different directory
        context = CommandContext.from_command("git status", "/home/user")
        result = await evaluator.evaluate(context)
        assert result.decision == Decision.ALLOW


class TestDecisionAggregation:
    """Tests for decision aggregation with multiple rules."""

    @pytest.mark.asyncio
    async def test_deny_wins_over_approval(self) -> None:
        """Test that DENY is more restrictive than REQUIRE_APPROVAL."""
        rules = [
            Rule(
                name="approve-rule",
                commands=["git"],
                action=RuleAction.REQUIRE_APPROVAL,
                message="Need approval",
            ),
            Rule(
                name="deny-rule",
                commands=["git"],
                action=RuleAction.DENY,
                message="Blocked",
            ),
        ]
        evaluator = RuleEvaluator(rules)
        context = CommandContext.from_command("git push", "/tmp")

        result = await evaluator.evaluate(context)

        assert result.decision == Decision.DENY
        assert result.plugin_name == "deny-rule"

    @pytest.mark.asyncio
    async def test_approval_wins_over_allow(self) -> None:
        """Test that REQUIRE_APPROVAL is more restrictive than ALLOW."""
        rules = [
            Rule(
                name="allow-rule",
                commands=["git"],
                action=RuleAction.ALLOW,
                message="Allowed",
            ),
            Rule(
                name="approve-rule",
                commands=["git"],
                action=RuleAction.REQUIRE_APPROVAL,
                message="Need approval",
            ),
        ]
        evaluator = RuleEvaluator(rules)
        context = CommandContext.from_command("git push", "/tmp")

        result = await evaluator.evaluate(context)

        assert result.decision == Decision.REQUIRE_APPROVAL

    @pytest.mark.asyncio
    async def test_multiple_commands_in_rule(self) -> None:
        """Test that a rule can match multiple command executables."""
        rules = [
            Rule(
                name="multi-cmd-rule",
                commands=["git", "rm", "mv"],
                action=RuleAction.DENY,
                message="Blocked",
            )
        ]
        evaluator = RuleEvaluator(rules)

        for cmd in ["git status", "rm -rf foo", "mv a b"]:
            context = CommandContext.from_command(cmd, "/tmp")
            result = await evaluator.evaluate(context)
            assert result.decision == Decision.DENY

        # ls is not in the list
        context = CommandContext.from_command("ls", "/tmp")
        result = await evaluator.evaluate(context)
        assert result.decision == Decision.ALLOW

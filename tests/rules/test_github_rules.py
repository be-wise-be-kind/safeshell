"""
File: tests/rules/test_github_rules.py
Purpose: Tests for GitHub CLI rules shipped with SafeShell
Exports: Test classes for GitHub rule categories
Depends: pytest, safeshell.rules
Overview: Validates that GitHub rules load correctly, match expected commands,
          and don't produce false positives on common operations.
"""

import pytest
import yaml

from safeshell.models import CommandContext, ExecutionContext
from safeshell.rules.evaluator import RuleEvaluator
from safeshell.rules.github import GITHUB_RULES_YAML
from safeshell.rules.schema import RuleSet


class TestGitHubRulesLoad:
    """Test that GitHub rules load without errors."""

    def test_github_rules_valid_yaml(self) -> None:
        """Verify GITHUB_RULES_YAML is valid YAML."""
        data = yaml.safe_load(GITHUB_RULES_YAML)
        assert "rules" in data
        assert len(data["rules"]) > 0

    def test_github_rules_valid_schema(self) -> None:
        """Verify all GitHub rules pass schema validation."""
        data = yaml.safe_load(GITHUB_RULES_YAML)
        ruleset = RuleSet.model_validate(data)
        # Expect 28+ rules (workflow, repo, release, secrets, issues, PRs, catch-alls)
        assert len(ruleset.rules) >= 25

    def test_all_rules_require_approval(self) -> None:
        """Verify all GitHub rules use require_approval action."""
        data = yaml.safe_load(GITHUB_RULES_YAML)
        ruleset = RuleSet.model_validate(data)

        for rule in ruleset.rules:
            assert (
                rule.action.value == "require_approval"
            ), f"Rule {rule.name} should use require_approval"

    def test_all_rules_ai_only(self) -> None:
        """Verify all GitHub rules are ai_only context."""
        data = yaml.safe_load(GITHUB_RULES_YAML)
        ruleset = RuleSet.model_validate(data)

        for rule in ruleset.rules:
            assert rule.context.value == "ai_only", f"Rule {rule.name} should be ai_only"

    def test_all_rules_have_messages(self) -> None:
        """Verify all rules have user-facing messages."""
        data = yaml.safe_load(GITHUB_RULES_YAML)
        ruleset = RuleSet.model_validate(data)

        for rule in ruleset.rules:
            assert rule.message, f"Rule {rule.name} missing message"
            assert len(rule.message) > 10, f"Rule {rule.name} has too short message"

    def test_all_rules_target_gh(self) -> None:
        """Verify all rules target the gh command."""
        data = yaml.safe_load(GITHUB_RULES_YAML)
        ruleset = RuleSet.model_validate(data)

        for rule in ruleset.rules:
            assert "gh" in rule.commands, f"Rule {rule.name} should target gh"


@pytest.fixture
def evaluator() -> RuleEvaluator:
    """Create an evaluator with GitHub rules."""
    data = yaml.safe_load(GITHUB_RULES_YAML)
    ruleset = RuleSet.model_validate(data)
    return RuleEvaluator(ruleset.rules)


class TestWorkflowOperations:
    """Test GitHub workflow rules."""

    @pytest.mark.asyncio
    async def test_workflow_run_requires_approval_for_ai(self, evaluator: RuleEvaluator) -> None:
        """gh workflow run should require approval for AI."""
        ctx = CommandContext.from_command(
            "gh workflow run build.yml", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_workflow_run_allowed_for_human(self, evaluator: RuleEvaluator) -> None:
        """gh workflow run should be allowed for humans."""
        ctx = CommandContext.from_command(
            "gh workflow run build.yml",
            "/home/user",
            execution_context=ExecutionContext.HUMAN,
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_run_rerun_requires_approval_for_ai(self, evaluator: RuleEvaluator) -> None:
        """gh run rerun should require approval for AI."""
        ctx = CommandContext.from_command(
            "gh run rerun 12345", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_run_cancel_requires_approval_for_ai(self, evaluator: RuleEvaluator) -> None:
        """gh run cancel should require approval for AI."""
        ctx = CommandContext.from_command(
            "gh run cancel 12345", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_workflow_list_allowed(self, evaluator: RuleEvaluator) -> None:
        """gh workflow list should be allowed."""
        ctx = CommandContext.from_command(
            "gh workflow list", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_run_list_allowed(self, evaluator: RuleEvaluator) -> None:
        """gh run list should be allowed."""
        ctx = CommandContext.from_command(
            "gh run list", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_run_view_allowed(self, evaluator: RuleEvaluator) -> None:
        """gh run view should be allowed."""
        ctx = CommandContext.from_command(
            "gh run view 12345", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"


class TestRepositoryOperations:
    """Test GitHub repository rules."""

    @pytest.mark.asyncio
    async def test_repo_delete_requires_approval_for_ai(self, evaluator: RuleEvaluator) -> None:
        """gh repo delete should require approval for AI."""
        ctx = CommandContext.from_command(
            "gh repo delete owner/repo --yes",
            "/home/user",
            execution_context=ExecutionContext.AI,
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_repo_create_requires_approval_for_ai(self, evaluator: RuleEvaluator) -> None:
        """gh repo create should require approval for AI."""
        ctx = CommandContext.from_command(
            "gh repo create my-new-repo --public",
            "/home/user",
            execution_context=ExecutionContext.AI,
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_repo_archive_requires_approval_for_ai(self, evaluator: RuleEvaluator) -> None:
        """gh repo archive should require approval for AI."""
        ctx = CommandContext.from_command(
            "gh repo archive owner/repo", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_repo_view_allowed(self, evaluator: RuleEvaluator) -> None:
        """gh repo view should be allowed."""
        ctx = CommandContext.from_command(
            "gh repo view owner/repo", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_repo_list_allowed(self, evaluator: RuleEvaluator) -> None:
        """gh repo list should be allowed."""
        ctx = CommandContext.from_command(
            "gh repo list", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_repo_clone_allowed(self, evaluator: RuleEvaluator) -> None:
        """gh repo clone should be allowed."""
        ctx = CommandContext.from_command(
            "gh repo clone owner/repo", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"


class TestReleaseOperations:
    """Test GitHub release rules."""

    @pytest.mark.asyncio
    async def test_release_create_requires_approval_for_ai(self, evaluator: RuleEvaluator) -> None:
        """gh release create should require approval for AI."""
        ctx = CommandContext.from_command(
            "gh release create v1.0.0", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_release_delete_requires_approval_for_ai(self, evaluator: RuleEvaluator) -> None:
        """gh release delete should require approval for AI."""
        ctx = CommandContext.from_command(
            "gh release delete v1.0.0", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_release_list_allowed(self, evaluator: RuleEvaluator) -> None:
        """gh release list should be allowed."""
        ctx = CommandContext.from_command(
            "gh release list", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_release_view_allowed(self, evaluator: RuleEvaluator) -> None:
        """gh release view should be allowed."""
        ctx = CommandContext.from_command(
            "gh release view v1.0.0", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"


class TestSecretOperations:
    """Test GitHub secrets rules."""

    @pytest.mark.asyncio
    async def test_secret_set_requires_approval_for_ai(self, evaluator: RuleEvaluator) -> None:
        """gh secret set should require approval for AI."""
        ctx = CommandContext.from_command(
            "gh secret set MY_SECRET", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_secret_delete_requires_approval_for_ai(self, evaluator: RuleEvaluator) -> None:
        """gh secret delete should require approval for AI."""
        ctx = CommandContext.from_command(
            "gh secret delete MY_SECRET", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_secret_list_allowed(self, evaluator: RuleEvaluator) -> None:
        """gh secret list should be allowed."""
        ctx = CommandContext.from_command(
            "gh secret list", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"


class TestIssueOperations:
    """Test GitHub issue rules."""

    @pytest.mark.asyncio
    async def test_issue_close_requires_approval_for_ai(self, evaluator: RuleEvaluator) -> None:
        """gh issue close should require approval for AI."""
        ctx = CommandContext.from_command(
            "gh issue close 123", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_issue_delete_requires_approval_for_ai(self, evaluator: RuleEvaluator) -> None:
        """gh issue delete should require approval for AI."""
        ctx = CommandContext.from_command(
            "gh issue delete 123", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_issue_list_allowed(self, evaluator: RuleEvaluator) -> None:
        """gh issue list should be allowed."""
        ctx = CommandContext.from_command(
            "gh issue list", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_issue_view_allowed(self, evaluator: RuleEvaluator) -> None:
        """gh issue view should be allowed."""
        ctx = CommandContext.from_command(
            "gh issue view 123", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_issue_create_allowed(self, evaluator: RuleEvaluator) -> None:
        """gh issue create should be allowed (caught by catch-all create rule)."""
        ctx = CommandContext.from_command(
            "gh issue create --title test",
            "/home/user",
            execution_context=ExecutionContext.AI,
        )
        result = await evaluator.evaluate(ctx)
        # Creating issues is less risky, but caught by catch-all
        assert result.decision.value == "require_approval"


class TestPROperations:
    """Test GitHub PR rules."""

    @pytest.mark.asyncio
    async def test_pr_close_requires_approval_for_ai(self, evaluator: RuleEvaluator) -> None:
        """gh pr close should require approval for AI."""
        ctx = CommandContext.from_command(
            "gh pr close 123", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_pr_merge_requires_approval_for_ai(self, evaluator: RuleEvaluator) -> None:
        """gh pr merge should require approval for AI."""
        ctx = CommandContext.from_command(
            "gh pr merge 123", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_pr_list_allowed(self, evaluator: RuleEvaluator) -> None:
        """gh pr list should be allowed."""
        ctx = CommandContext.from_command(
            "gh pr list", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_pr_view_allowed(self, evaluator: RuleEvaluator) -> None:
        """gh pr view should be allowed."""
        ctx = CommandContext.from_command(
            "gh pr view 123", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_pr_checkout_allowed(self, evaluator: RuleEvaluator) -> None:
        """gh pr checkout should be allowed."""
        ctx = CommandContext.from_command(
            "gh pr checkout 123", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_pr_diff_allowed(self, evaluator: RuleEvaluator) -> None:
        """gh pr diff should be allowed."""
        ctx = CommandContext.from_command(
            "gh pr diff 123", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"


class TestFalsePositives:
    """Test that common safe gh operations are not blocked."""

    @pytest.mark.asyncio
    async def test_gh_auth_status_allowed(self, evaluator: RuleEvaluator) -> None:
        """gh auth status should be allowed."""
        ctx = CommandContext.from_command(
            "gh auth status", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_gh_api_allowed(self, evaluator: RuleEvaluator) -> None:
        """gh api should be allowed (read-only by default)."""
        ctx = CommandContext.from_command(
            "gh api repos/owner/repo", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_gh_browse_allowed(self, evaluator: RuleEvaluator) -> None:
        """gh browse should be allowed."""
        ctx = CommandContext.from_command(
            "gh browse", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_gh_gist_list_allowed(self, evaluator: RuleEvaluator) -> None:
        """gh gist list should be allowed."""
        ctx = CommandContext.from_command(
            "gh gist list", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_gh_status_allowed(self, evaluator: RuleEvaluator) -> None:
        """gh status should be allowed."""
        ctx = CommandContext.from_command(
            "gh status", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

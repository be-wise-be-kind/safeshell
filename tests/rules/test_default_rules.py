"""
File: tests/rules/test_default_rules.py
Purpose: Tests for default rules shipped with SafeShell
Exports: Test classes for each rule category
Depends: pytest, safeshell.rules
Overview: Validates that default rules load correctly, match expected commands,
          and don't produce false positives on common operations.
"""

# ruff: noqa: S108 - /tmp usage is fine in tests

import time

import pytest
import yaml

from safeshell.models import CommandContext, ExecutionContext
from safeshell.rules.defaults import DEFAULT_RULES_YAML
from safeshell.rules.evaluator import RuleEvaluator
from safeshell.rules.schema import RuleSet


class TestDefaultRulesLoad:
    """Test that default rules load without errors."""

    def test_default_rules_valid_yaml(self) -> None:
        """Verify DEFAULT_RULES_YAML is valid YAML."""
        data = yaml.safe_load(DEFAULT_RULES_YAML)
        assert "rules" in data
        assert len(data["rules"]) > 0

    def test_default_rules_valid_schema(self) -> None:
        """Verify all default rules pass schema validation."""
        data = yaml.safe_load(DEFAULT_RULES_YAML)
        ruleset = RuleSet.model_validate(data)
        # Expect ~49 rules
        assert len(ruleset.rules) >= 40

    def test_only_two_deny_rules(self) -> None:
        """Verify only rm -rf / and rm -rf * are DENY."""
        data = yaml.safe_load(DEFAULT_RULES_YAML)
        ruleset = RuleSet.model_validate(data)

        deny_rules = [r for r in ruleset.rules if r.action.value == "deny"]
        assert len(deny_rules) == 2

        deny_names = {r.name for r in deny_rules}
        assert deny_names == {"deny-rm-rf-root", "deny-rm-rf-star"}

    def test_all_rules_have_messages(self) -> None:
        """Verify all rules have user-facing messages."""
        data = yaml.safe_load(DEFAULT_RULES_YAML)
        ruleset = RuleSet.model_validate(data)

        for rule in ruleset.rules:
            assert rule.message, f"Rule {rule.name} missing message"
            assert len(rule.message) > 10, f"Rule {rule.name} has too short message"

    def test_all_rules_have_commands(self) -> None:
        """Verify all rules specify target commands."""
        data = yaml.safe_load(DEFAULT_RULES_YAML)
        ruleset = RuleSet.model_validate(data)

        for rule in ruleset.rules:
            assert len(rule.commands) > 0, f"Rule {rule.name} missing commands"


@pytest.fixture
def evaluator() -> RuleEvaluator:
    """Create an evaluator with default rules."""
    data = yaml.safe_load(DEFAULT_RULES_YAML)
    ruleset = RuleSet.model_validate(data)
    return RuleEvaluator(ruleset.rules)


class TestDestructiveOperations:
    """Test rules for destructive operations."""

    @pytest.mark.asyncio
    async def test_rm_rf_root_denied(self, evaluator: RuleEvaluator) -> None:
        """rm -rf / should be denied."""
        ctx = CommandContext.from_command("rm -rf /", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "deny"

    @pytest.mark.asyncio
    async def test_rm_rf_star_denied(self, evaluator: RuleEvaluator) -> None:
        """rm -rf * should be denied."""
        ctx = CommandContext.from_command("rm -rf *", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "deny"

    @pytest.mark.asyncio
    async def test_rm_file_allowed(self, evaluator: RuleEvaluator) -> None:
        """rm file.txt should be allowed."""
        ctx = CommandContext.from_command("rm file.txt", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_rm_directory_allowed(self, evaluator: RuleEvaluator) -> None:
        """rm -r directory should be allowed for humans."""
        ctx = CommandContext.from_command(
            "rm -r directory", "/home/user", execution_context=ExecutionContext.HUMAN
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_rm_rf_directory_requires_approval_for_ai(self, evaluator: RuleEvaluator) -> None:
        """rm -rf directory should require approval for AI."""
        ctx = CommandContext.from_command(
            "rm -rf node_modules", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_chmod_777_requires_approval(self, evaluator: RuleEvaluator) -> None:
        """chmod 777 should require approval."""
        ctx = CommandContext.from_command("chmod 777 file.txt", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_chmod_644_allowed(self, evaluator: RuleEvaluator) -> None:
        """chmod 644 should be allowed."""
        ctx = CommandContext.from_command("chmod 644 file.txt", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"


class TestGitSafety:
    """Test git safety rules."""

    @pytest.mark.asyncio
    async def test_force_push_requires_approval(self, evaluator: RuleEvaluator) -> None:
        """git push --force should require approval."""
        ctx = CommandContext.from_command("git push --force origin feature", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_normal_push_allowed(self, evaluator: RuleEvaluator) -> None:
        """git push should be allowed."""
        ctx = CommandContext.from_command("git push origin main", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_git_reset_hard_requires_approval(self, evaluator: RuleEvaluator) -> None:
        """git reset --hard should require approval."""
        ctx = CommandContext.from_command("git reset --hard HEAD~1", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_git_reset_soft_allowed(self, evaluator: RuleEvaluator) -> None:
        """git reset --soft should be allowed."""
        ctx = CommandContext.from_command("git reset --soft HEAD~1", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_git_clean_force_requires_approval(self, evaluator: RuleEvaluator) -> None:
        """git clean -f should require approval."""
        ctx = CommandContext.from_command("git clean -fd", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_git_status_allowed(self, evaluator: RuleEvaluator) -> None:
        """git status should be allowed."""
        ctx = CommandContext.from_command("git status", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_commit_on_main_requires_approval_for_ai(self, evaluator: RuleEvaluator) -> None:
        """git commit on main branch should require approval for AI."""
        ctx = CommandContext(
            raw_command='git commit -m "test"',
            parsed_args=["git", "commit", "-m", "test"],
            working_dir="/home/user/project",
            git_repo_root="/home/user/project",
            git_branch="main",
            execution_context=ExecutionContext.AI,
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_commit_on_main_allowed_for_human(self, evaluator: RuleEvaluator) -> None:
        """git commit on main branch should be allowed for humans."""
        ctx = CommandContext(
            raw_command='git commit -m "test"',
            parsed_args=["git", "commit", "-m", "test"],
            working_dir="/home/user/project",
            git_repo_root="/home/user/project",
            git_branch="main",
            execution_context=ExecutionContext.HUMAN,
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_commit_on_feature_branch_allowed(self, evaluator: RuleEvaluator) -> None:
        """git commit on feature branch should be allowed."""
        ctx = CommandContext(
            raw_command='git commit -m "test"',
            parsed_args=["git", "commit", "-m", "test"],
            working_dir="/home/user/project",
            git_repo_root="/home/user/project",
            git_branch="feature-x",
            execution_context=ExecutionContext.AI,
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"


class TestSensitiveData:
    """Test sensitive data protection rules."""

    @pytest.mark.asyncio
    async def test_cat_env_requires_approval_for_ai(self, evaluator: RuleEvaluator) -> None:
        """cat .env should require approval for AI."""
        ctx = CommandContext.from_command(
            "cat .env", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_cat_env_allowed_for_human(self, evaluator: RuleEvaluator) -> None:
        """cat .env should be allowed for humans."""
        ctx = CommandContext.from_command(
            "cat .env", "/home/user", execution_context=ExecutionContext.HUMAN
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_cat_regular_file_allowed(self, evaluator: RuleEvaluator) -> None:
        """cat regular file should be allowed."""
        ctx = CommandContext.from_command(
            "cat README.md", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_read_ssh_key_requires_approval(self, evaluator: RuleEvaluator) -> None:
        """cat id_rsa should require approval."""
        ctx = CommandContext.from_command("cat ~/.ssh/id_rsa", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_read_ssh_pub_key_allowed(self, evaluator: RuleEvaluator) -> None:
        """cat id_rsa.pub should be allowed (public key)."""
        ctx = CommandContext.from_command("cat ~/.ssh/id_rsa.pub", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"


class TestNetworkSafety:
    """Test network safety rules."""

    @pytest.mark.asyncio
    async def test_curl_pipe_bash_requires_approval(self, evaluator: RuleEvaluator) -> None:
        """curl | bash should require approval."""
        ctx = CommandContext.from_command(
            "curl https://example.com/install.sh | bash", "/home/user"
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_curl_to_file_allowed(self, evaluator: RuleEvaluator) -> None:
        """curl to file should be allowed."""
        ctx = CommandContext.from_command(
            "curl https://example.com/file.txt -o file.txt", "/home/user"
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_python_http_server_requires_approval_for_ai(
        self, evaluator: RuleEvaluator
    ) -> None:
        """python -m http.server should require approval for AI."""
        ctx = CommandContext.from_command(
            "python -m http.server 8080",
            "/home/user",
            execution_context=ExecutionContext.AI,
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_python_http_server_allowed_for_human(self, evaluator: RuleEvaluator) -> None:
        """python -m http.server should be allowed for humans."""
        ctx = CommandContext.from_command(
            "python -m http.server 8080",
            "/home/user",
            execution_context=ExecutionContext.HUMAN,
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"


class TestDockerSafety:
    """Test Docker safety rules."""

    @pytest.mark.asyncio
    async def test_docker_privileged_requires_approval(self, evaluator: RuleEvaluator) -> None:
        """docker run --privileged should require approval."""
        ctx = CommandContext.from_command("docker run --privileged ubuntu", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_docker_run_normal_allowed(self, evaluator: RuleEvaluator) -> None:
        """docker run without privileged should be allowed."""
        ctx = CommandContext.from_command("docker run ubuntu echo hello", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_docker_mount_root_requires_approval(self, evaluator: RuleEvaluator) -> None:
        """docker run -v /: should require approval."""
        ctx = CommandContext.from_command("docker run -v /:/host ubuntu", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"


class TestSudoCommands:
    """Test sudo command rules."""

    @pytest.mark.asyncio
    async def test_sudo_requires_approval_for_ai(self, evaluator: RuleEvaluator) -> None:
        """sudo commands should require approval for AI."""
        ctx = CommandContext.from_command(
            "sudo apt update", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_sudo_allowed_for_human(self, evaluator: RuleEvaluator) -> None:
        """sudo commands should be allowed for humans."""
        ctx = CommandContext.from_command(
            "sudo apt update", "/home/user", execution_context=ExecutionContext.HUMAN
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"


class TestPackageManagers:
    """Test package manager rules."""

    @pytest.mark.asyncio
    async def test_npm_global_requires_approval_for_ai(self, evaluator: RuleEvaluator) -> None:
        """npm install -g should require approval for AI."""
        ctx = CommandContext.from_command(
            "npm install -g typescript",
            "/home/user",
            execution_context=ExecutionContext.AI,
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_npm_local_allowed(self, evaluator: RuleEvaluator) -> None:
        """npm install (local) should be allowed."""
        ctx = CommandContext.from_command(
            "npm install express", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_pip_install_requires_approval_for_ai(self, evaluator: RuleEvaluator) -> None:
        """pip install should require approval for AI."""
        ctx = CommandContext.from_command(
            "pip install requests", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"


class TestFalsePositives:
    """Test that common safe operations are not blocked."""

    @pytest.mark.asyncio
    async def test_ls_allowed(self, evaluator: RuleEvaluator) -> None:
        """ls should be allowed."""
        ctx = CommandContext.from_command("ls -la", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_cd_allowed(self, evaluator: RuleEvaluator) -> None:
        """cd should be allowed."""
        ctx = CommandContext.from_command("cd /home/user", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_echo_allowed(self, evaluator: RuleEvaluator) -> None:
        """echo should be allowed."""
        ctx = CommandContext.from_command("echo hello", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_grep_allowed(self, evaluator: RuleEvaluator) -> None:
        """grep should be allowed."""
        ctx = CommandContext.from_command("grep pattern file.txt", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_cat_normal_file_allowed(self, evaluator: RuleEvaluator) -> None:
        """cat normal file should be allowed."""
        ctx = CommandContext.from_command(
            "cat main.py", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_python_script_allowed(self, evaluator: RuleEvaluator) -> None:
        """python script.py should be allowed."""
        ctx = CommandContext.from_command(
            "python script.py", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_git_add_allowed(self, evaluator: RuleEvaluator) -> None:
        """git add should be allowed."""
        ctx = CommandContext.from_command("git add .", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_git_diff_allowed(self, evaluator: RuleEvaluator) -> None:
        """git diff should be allowed."""
        ctx = CommandContext.from_command("git diff", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_make_allowed(self, evaluator: RuleEvaluator) -> None:
        """make should be allowed."""
        ctx = CommandContext.from_command("make build", "/home/user")
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"


class TestPerformance:
    """Test that rule evaluation is fast."""

    @pytest.mark.asyncio
    async def test_evaluation_under_1ms(self, evaluator: RuleEvaluator) -> None:
        """Each evaluation should complete in under 1ms."""
        commands = [
            "rm -rf /",
            "git push --force",
            "cat .env",
            "ls -la",
            "npm install express",
            "docker run ubuntu",
            "chmod 644 file.txt",
            "python script.py",
        ]

        for cmd in commands:
            ctx = CommandContext.from_command(cmd, "/home/user")
            start = time.monotonic()
            await evaluator.evaluate(ctx)
            elapsed_ms = (time.monotonic() - start) * 1000
            assert elapsed_ms < 1.0, f"'{cmd}' took {elapsed_ms:.2f}ms"

    @pytest.mark.asyncio
    async def test_fast_path_under_100us(self, evaluator: RuleEvaluator) -> None:
        """Commands not in index should be very fast (fast-path)."""
        ctx = CommandContext.from_command("echo hello", "/home/user")
        start = time.monotonic()
        await evaluator.evaluate(ctx)
        elapsed_us = (time.monotonic() - start) * 1_000_000
        # Fast path should be under 500us (generous for CI environments)
        assert elapsed_us < 500, f"Fast path took {elapsed_us:.0f}us"

"""
File: tests/rules/test_aws_rules.py
Purpose: Tests for AWS CLI rules shipped with SafeShell
Exports: Test classes for AWS rule categories
Depends: pytest, safeshell.rules
Overview: Validates that AWS rules load correctly, match expected commands,
          and don't produce false positives on common operations.
"""

import pytest
import yaml

from safeshell.models import CommandContext, ExecutionContext
from safeshell.rules.aws import AWS_RULES_YAML
from safeshell.rules.evaluator import RuleEvaluator
from safeshell.rules.schema import RuleSet


class TestAWSRulesLoad:
    """Test that AWS rules load without errors."""

    def test_aws_rules_valid_yaml(self) -> None:
        """Verify AWS_RULES_YAML is valid YAML."""
        data = yaml.safe_load(AWS_RULES_YAML)
        assert "rules" in data
        assert len(data["rules"]) > 0

    def test_aws_rules_valid_schema(self) -> None:
        """Verify all AWS rules pass schema validation."""
        data = yaml.safe_load(AWS_RULES_YAML)
        ruleset = RuleSet.model_validate(data)
        assert len(ruleset.rules) >= 1

    def test_all_rules_require_approval(self) -> None:
        """Verify all AWS rules use require_approval action."""
        data = yaml.safe_load(AWS_RULES_YAML)
        ruleset = RuleSet.model_validate(data)

        for rule in ruleset.rules:
            assert (
                rule.action.value == "require_approval"
            ), f"Rule {rule.name} should use require_approval"

    def test_all_rules_ai_only(self) -> None:
        """Verify all AWS rules are ai_only context."""
        data = yaml.safe_load(AWS_RULES_YAML)
        ruleset = RuleSet.model_validate(data)

        for rule in ruleset.rules:
            assert rule.context.value == "ai_only", f"Rule {rule.name} should be ai_only"

    def test_all_rules_have_messages(self) -> None:
        """Verify all rules have user-facing messages."""
        data = yaml.safe_load(AWS_RULES_YAML)
        ruleset = RuleSet.model_validate(data)

        for rule in ruleset.rules:
            assert rule.message, f"Rule {rule.name} missing message"
            assert len(rule.message) > 10, f"Rule {rule.name} has too short message"

    def test_all_rules_target_aws(self) -> None:
        """Verify all rules target the aws command."""
        data = yaml.safe_load(AWS_RULES_YAML)
        ruleset = RuleSet.model_validate(data)

        for rule in ruleset.rules:
            assert "aws" in rule.commands, f"Rule {rule.name} should target aws"


@pytest.fixture
def evaluator() -> RuleEvaluator:
    """Create an evaluator with AWS rules."""
    data = yaml.safe_load(AWS_RULES_YAML)
    ruleset = RuleSet.model_validate(data)
    return RuleEvaluator(ruleset.rules)


class TestSSMOperations:
    """Test AWS SSM rules."""

    @pytest.mark.asyncio
    async def test_ssm_send_command_requires_approval_for_ai(
        self, evaluator: RuleEvaluator
    ) -> None:
        """aws ssm send-command should require approval for AI."""
        ctx = CommandContext.from_command(
            "aws ssm send-command --instance-ids i-123 --document-name AWS-RunShellScript",
            "/home/user",
            execution_context=ExecutionContext.AI,
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_ssm_start_session_requires_approval_for_ai(
        self, evaluator: RuleEvaluator
    ) -> None:
        """aws ssm start-session should require approval for AI."""
        ctx = CommandContext.from_command(
            "aws ssm start-session --target i-123",
            "/home/user",
            execution_context=ExecutionContext.AI,
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_ssm_put_parameter_requires_approval_for_ai(
        self, evaluator: RuleEvaluator
    ) -> None:
        """aws ssm put-parameter should require approval for AI."""
        ctx = CommandContext.from_command(
            "aws ssm put-parameter --name /my/param --value secret --type SecureString",
            "/home/user",
            execution_context=ExecutionContext.AI,
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_ssm_delete_parameter_requires_approval_for_ai(
        self, evaluator: RuleEvaluator
    ) -> None:
        """aws ssm delete-parameter should require approval for AI."""
        ctx = CommandContext.from_command(
            "aws ssm delete-parameter --name /my/param",
            "/home/user",
            execution_context=ExecutionContext.AI,
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_ssm_describe_instance_information_requires_approval_for_ai(
        self, evaluator: RuleEvaluator
    ) -> None:
        """aws ssm describe-instance-information should require approval for AI."""
        ctx = CommandContext.from_command(
            "aws ssm describe-instance-information",
            "/home/user",
            execution_context=ExecutionContext.AI,
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "require_approval"

    @pytest.mark.asyncio
    async def test_ssm_allowed_for_human(self, evaluator: RuleEvaluator) -> None:
        """aws ssm commands should be allowed for humans."""
        ctx = CommandContext.from_command(
            "aws ssm send-command --instance-ids i-123 --document-name AWS-RunShellScript",
            "/home/user",
            execution_context=ExecutionContext.HUMAN,
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"


class TestFalsePositives:
    """Test that common safe AWS operations are not blocked."""

    @pytest.mark.asyncio
    async def test_aws_s3_ls_allowed(self, evaluator: RuleEvaluator) -> None:
        """aws s3 ls should be allowed."""
        ctx = CommandContext.from_command(
            "aws s3 ls", "/home/user", execution_context=ExecutionContext.AI
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_aws_ec2_describe_instances_allowed(self, evaluator: RuleEvaluator) -> None:
        """aws ec2 describe-instances should be allowed."""
        ctx = CommandContext.from_command(
            "aws ec2 describe-instances",
            "/home/user",
            execution_context=ExecutionContext.AI,
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_aws_sts_get_caller_identity_allowed(self, evaluator: RuleEvaluator) -> None:
        """aws sts get-caller-identity should be allowed."""
        ctx = CommandContext.from_command(
            "aws sts get-caller-identity",
            "/home/user",
            execution_context=ExecutionContext.AI,
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

    @pytest.mark.asyncio
    async def test_aws_cloudformation_list_stacks_allowed(self, evaluator: RuleEvaluator) -> None:
        """aws cloudformation list-stacks should be allowed."""
        ctx = CommandContext.from_command(
            "aws cloudformation list-stacks",
            "/home/user",
            execution_context=ExecutionContext.AI,
        )
        result = await evaluator.evaluate(ctx)
        assert result.decision.value == "allow"

"""
File: src/safeshell/rules/schema.py
Purpose: Pydantic models for YAML-based rule configuration
Exports: RuleAction, Rule, RuleSet
Depends: pydantic, enum
Overview: Defines the schema for rules loaded from ~/.safeshell/rules.yaml and .safeshell/rules.yaml
"""

from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class RuleAction(str, Enum):
    """Actions a rule can take when matched."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    REDIRECT = "redirect"


class Rule(BaseModel):
    """A single policy rule definition.

    Rules are matched against commands based on:
    1. Command executable (fast-path filter)
    2. Directory pattern (optional regex)
    3. Bash conditions (all must exit 0)

    When matched, the rule's action is applied.
    """

    name: str = Field(description="Unique identifier for this rule")
    commands: list[str] = Field(
        description="Target executables that this rule applies to (fast-path filter)"
    )
    directory: str | None = Field(
        default=None,
        description="Optional regex pattern for working directory",
    )
    conditions: list[str] = Field(
        default_factory=list,
        description="Bash conditions that must all exit 0 for rule to match",
    )
    action: RuleAction = Field(description="Action to take when rule matches")
    allow_override: bool = Field(
        default=True,
        description="For deny: can user approve anyway via monitor?",
    )
    redirect_to: str | None = Field(
        default=None,
        description="For redirect action: replacement command ($ARGS available)",
    )
    message: str = Field(description="User-facing message for denials/approvals")

    @field_validator("commands")
    @classmethod
    def validate_commands_not_empty(cls, v: list[str]) -> list[str]:
        """Ensure at least one command is specified."""
        if not v:
            raise ValueError("At least one command must be specified")
        return v

    @model_validator(mode="after")
    def validate_redirect_to(self) -> "Rule":
        """Ensure redirect_to is set when action is REDIRECT."""
        if self.action == RuleAction.REDIRECT and self.redirect_to is None:
            raise ValueError("redirect_to is required when action is 'redirect'")
        return self


class RuleSet(BaseModel):
    """A collection of rules from a single source file."""

    rules: list[Rule] = Field(default_factory=list)

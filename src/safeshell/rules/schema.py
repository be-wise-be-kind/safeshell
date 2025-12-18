"""
File: src/safeshell/rules/schema.py
Purpose: Pydantic models for YAML-based rule configuration
Exports: RuleAction, RuleContext, Rule, RuleOverride, RuleSet
Depends: pydantic, enum, condition_types
Overview: Defines the schema for rules loaded from ~/.safeshell/rules.yaml and .safeshell/rules.yaml
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from safeshell.rules.condition_types import Condition, parse_condition


class RuleAction(str, Enum):
    """Actions a rule can take when matched."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    REDIRECT = "redirect"


class RuleContext(str, Enum):
    """Context in which a rule applies."""

    ALL = "all"  # Applies to both AI and human (default)
    AI_ONLY = "ai_only"  # Only applies to AI agents
    HUMAN_ONLY = "human_only"  # Only applies to human terminals


class Rule(BaseModel):
    """A single policy rule definition.

    Rules are matched against commands based on:
    1. Command executable (fast-path filter)
    2. Directory pattern (optional regex)
    3. Structured conditions (all must evaluate to True)

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
    conditions: list[Condition] = Field(
        default_factory=list,
        description="Structured conditions that must all pass for rule to match",
    )

    action: RuleAction = Field(description="Action to take when rule matches")
    context: RuleContext = Field(
        default=RuleContext.ALL,
        description="Context in which this rule applies (all, ai_only, human_only)",
    )
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

    @field_validator("conditions", mode="before")
    @classmethod
    def parse_conditions(cls, v: list[Any]) -> list[Condition]:
        """Parse conditions from YAML format to Condition objects."""
        if not v:
            return []
        return [parse_condition(item) if isinstance(item, dict) else item for item in v]

    @model_validator(mode="after")
    def validate_redirect_to(self) -> "Rule":
        """Ensure redirect_to is set when action is REDIRECT."""
        if self.action == RuleAction.REDIRECT and self.redirect_to is None:
            raise ValueError("redirect_to is required when action is 'redirect'")
        return self


class RuleOverride(BaseModel):
    """Override configuration for a default or global rule.

    Allows users to disable or modify rules by name. Overrides are applied
    at load time so disabled rules never enter the evaluator.
    """

    name: str = Field(description="Name of the rule to override (must exist)")
    disabled: bool = Field(
        default=False,
        description="If true, completely removes this rule from evaluation",
    )
    action: RuleAction | None = Field(
        default=None,
        description="Override the rule's action (e.g., change deny to require_approval)",
    )
    message: str | None = Field(
        default=None,
        description="Override the rule's user-facing message",
    )
    context: RuleContext | None = Field(
        default=None,
        description="Override the rule's context (all, ai_only, human_only)",
    )
    allow_override: bool | None = Field(
        default=None,
        description="Override whether user can approve anyway via monitor",
    )

    @model_validator(mode="after")
    def validate_not_empty_override(self) -> "RuleOverride":
        """Ensure at least one override field is set besides name."""
        if not self.disabled and all(
            v is None for v in [self.action, self.message, self.context, self.allow_override]
        ):
            raise ValueError(
                f"Override for '{self.name}' must either set disabled=true "
                "or provide at least one property to override"
            )
        return self


class RuleSet(BaseModel):
    """A collection of rules from a single source file."""

    rules: list[Rule] = Field(default_factory=list)
    overrides: list[RuleOverride] = Field(
        default_factory=list,
        description="Overrides for rules from earlier sources (defaults, global)",
    )

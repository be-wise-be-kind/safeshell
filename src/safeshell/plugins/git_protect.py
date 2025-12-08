"""
File: src/safeshell/plugins/git_protect.py
Purpose: Git branch protection plugin - blocks commits on protected branches
Exports: GitProtectPlugin
Depends: safeshell.plugins.base, safeshell.models
Overview: Prevents direct commits to main/master branches, protecting against accidental pushes
"""

from safeshell.models import CommandContext, EvaluationResult
from safeshell.plugins.base import Plugin


class GitProtectPlugin(Plugin):
    """Protect against destructive git operations on protected branches.

    MVP behavior:
    - DENY: git commit when on main or master branch

    Phase 2 additions:
    - REQUIRE_APPROVAL: git push --force to protected branches
    - REQUIRE_APPROVAL: git reset --hard
    """

    PROTECTED_BRANCHES: frozenset[str] = frozenset({"main", "master", "develop"})

    @property
    def name(self) -> str:
        return "git-protect"

    @property
    def description(self) -> str:
        return "Protects main/master branches from direct commits"

    def matches(self, ctx: CommandContext) -> bool:
        """Only evaluate git commands in git repositories."""
        # Must be in a git repo
        if not ctx.git_repo_root:
            return False

        # Must be a git command
        if not ctx.parsed_args:
            return False

        return ctx.parsed_args[0] == "git"

    def evaluate(self, ctx: CommandContext) -> EvaluationResult:
        """Evaluate git command for protected branch violations."""
        # Should have at least "git <subcommand>"
        if len(ctx.parsed_args) < 2:
            return self._allow("No git subcommand specified")

        subcommand = ctx.parsed_args[1]

        if subcommand == "commit":
            return self._evaluate_commit(ctx)

        if subcommand == "push":
            return self._evaluate_push(ctx)

        # Allow other git commands
        return self._allow(f"Git subcommand '{subcommand}' is not restricted")

    def _evaluate_commit(self, ctx: CommandContext) -> EvaluationResult:
        """Block commits on protected branches."""
        if ctx.git_branch in self.PROTECTED_BRANCHES:
            return self._deny(
                f"Cannot commit directly to protected branch '{ctx.git_branch}'. "
                f"Create a feature branch first."
            )
        return self._allow("Not on a protected branch")

    def _evaluate_push(self, ctx: CommandContext) -> EvaluationResult:
        """Evaluate push commands - block force push to protected branches."""
        args = ctx.parsed_args[2:]  # Everything after "git push"

        # Check for force push flags
        is_force = "--force" in args or "-f" in args or "--force-with-lease" in args

        if is_force and ctx.git_branch in self.PROTECTED_BRANCHES:
            # Phase 2: This will become REQUIRE_APPROVAL
            return self._deny(
                f"Force push to protected branch '{ctx.git_branch}' is blocked. "
                f"This is a destructive operation that could lose commits."
            )

        return self._allow("Push operation is allowed")

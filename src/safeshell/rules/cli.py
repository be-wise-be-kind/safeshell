"""
File: src/safeshell/rules/cli.py
Purpose: CLI commands for rule management
Exports: app (Typer app)
Depends: typer, rich, safeshell.rules.loader, safeshell.rules.schema
Overview: Provides 'safeshell rules' subcommands including validation
"""

# ruff: noqa: B008 - typer.Option() in argument defaults is standard typer pattern

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from safeshell.exceptions import RuleLoadError
from safeshell.rules.loader import GLOBAL_RULES_PATH, _find_repo_rules, _load_rule_file
from safeshell.rules.schema import Rule, RuleOverride

app = typer.Typer(
    name="rules",
    help="Manage SafeShell rules.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def validate(
    path: Path | None = typer.Option(
        None,
        "--path",
        "-p",
        help="Path to rules.yaml file to validate (defaults to global + repo rules)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed rule information",
    ),
) -> None:
    """Validate rules.yaml files for syntax and schema errors.

    Checks YAML syntax, schema compliance, and provides helpful error messages.
    Without --path, validates both global (~/.safeshell/rules.yaml) and
    repo (.safeshell/rules.yaml) rules.

    Examples:
        safeshell rules validate
        safeshell rules validate --path ./my-rules.yaml
        safeshell rules validate -v
    """
    if path:
        _validate_single_file(path, verbose)
    else:
        _validate_all_rules(verbose)


def _validate_single_file(path: Path, verbose: bool) -> None:
    """Validate a single rules file.

    Args:
        path: Path to the rules file
        verbose: Whether to show detailed rule information
    """
    if not path.exists():
        console.print(f"[red]Error:[/red] File not found: {path}")
        raise typer.Exit(1)

    try:
        rules, overrides = _load_rule_file(path)
        msg = f"[green]Valid:[/green] {path} ({len(rules)} rules"
        if overrides:
            msg += f", {len(overrides)} overrides"
        msg += ")"
        console.print(msg)

        if verbose:
            if rules:
                _show_rules_table(rules)
            if overrides:
                _show_overrides_table(overrides)

    except RuleLoadError as e:
        console.print(f"[red]Invalid:[/red] {path}")
        console.print(f"  Error: {e}")
        raise typer.Exit(1) from e


def _validate_all_rules(verbose: bool) -> None:
    """Validate global and repo rules.

    Args:
        verbose: Whether to show detailed rule information
    """
    errors: list[Path] = []
    total_rules = 0
    total_overrides = 0
    all_rules: list[Rule] = []
    all_overrides: list[RuleOverride] = []

    # Check global rules
    if GLOBAL_RULES_PATH.exists():
        try:
            rules, overrides = _load_rule_file(GLOBAL_RULES_PATH)
            msg = f"[green]Valid:[/green] {GLOBAL_RULES_PATH} ({len(rules)} rules"
            if overrides:
                msg += f", {len(overrides)} overrides"
            msg += ")"
            console.print(msg)
            total_rules += len(rules)
            total_overrides += len(overrides)
            all_rules.extend(rules)
            all_overrides.extend(overrides)
        except RuleLoadError as e:
            console.print(f"[red]Invalid:[/red] {GLOBAL_RULES_PATH}")
            console.print(f"  Error: {e}")
            errors.append(GLOBAL_RULES_PATH)
    else:
        console.print(f"[yellow]Not found:[/yellow] {GLOBAL_RULES_PATH}")

    # Check repo rules
    repo_path = _find_repo_rules(Path.cwd())
    if repo_path:
        try:
            rules, overrides = _load_rule_file(repo_path)
            msg = f"[green]Valid:[/green] {repo_path} ({len(rules)} rules"
            if overrides:
                msg += f", {len(overrides)} overrides [yellow](ignored)[/yellow]"
            msg += ")"
            console.print(msg)
            total_rules += len(rules)
            # Note: repo overrides are ignored for security but we still validate them
            all_rules.extend(rules)
        except RuleLoadError as e:
            console.print(f"[red]Invalid:[/red] {repo_path}")
            console.print(f"  Error: {e}")
            errors.append(repo_path)
    else:
        console.print("[dim]No repo rules found in current directory[/dim]")

    # Show verbose output
    if verbose:
        if all_rules:
            console.print()
            _show_rules_table(all_rules)
        if all_overrides:
            console.print()
            _show_overrides_table(all_overrides)

    # Summary
    console.print()
    if errors:
        console.print(f"[red]Validation failed:[/red] {len(errors)} file(s) with errors")
        raise typer.Exit(1)

    summary = f"[green]All rules valid:[/green] {total_rules} total rules"
    if total_overrides:
        summary += f", {total_overrides} overrides"
    console.print(summary)


def _show_rules_table(rules: list[Rule]) -> None:
    """Display rules in a table.

    Args:
        rules: List of Rule objects to display
    """
    table = Table(title="Rules")
    table.add_column("Name", style="cyan")
    table.add_column("Commands")
    table.add_column("Action", style="magenta")
    table.add_column("Context")
    table.add_column("Conditions")

    for rule in rules:
        # Truncate commands list if too long
        cmds = ", ".join(rule.commands[:3])
        if len(rule.commands) > 3:
            cmds += f"... (+{len(rule.commands) - 3})"

        conditions = str(len(rule.conditions)) if rule.conditions else "-"
        context = rule.context.value if rule.context else "all"

        table.add_row(
            rule.name,
            cmds,
            rule.action.value,
            context,
            conditions,
        )

    console.print(table)


def _show_overrides_table(overrides: list[RuleOverride]) -> None:
    """Display overrides in a table.

    Args:
        overrides: List of RuleOverride objects to display
    """
    table = Table(title="Overrides")
    table.add_column("Target Rule", style="cyan")
    table.add_column("Disabled", style="red")
    table.add_column("Modified Properties")

    for override in overrides:
        mods: list[str] = []
        if override.action is not None:
            mods.append(f"action={override.action.value}")
        if override.message is not None:
            mods.append("message")
        if override.context is not None:
            mods.append(f"context={override.context.value}")
        if override.allow_override is not None:
            mods.append(f"allow_override={override.allow_override}")

        table.add_row(
            override.name,
            "Yes" if override.disabled else "-",
            ", ".join(mods) if mods else "-",
        )

    console.print(table)

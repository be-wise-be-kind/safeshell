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
from rich.table import Table

from safeshell.console import console, print_error, print_success
from safeshell.exceptions import RuleLoadError
from safeshell.rules.loader import GLOBAL_RULES_PATH, _find_repo_rules, _load_rule_file
from safeshell.rules.schema import Rule
from safeshell.theme import ICON_ERROR, ICON_SUCCESS, ICON_WARNING

app = typer.Typer(
    name="rules",
    help="Manage SafeShell rules.",
    no_args_is_help=True,
)


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
        print_error(f"File not found: {path}")
        raise typer.Exit(1)

    try:
        rules = _load_rule_file(path)
        console.print(
            f"[success]{ICON_SUCCESS}[/success] Valid: [path]{path}[/path] ({len(rules)} rules)"
        )

        if verbose and rules:
            _show_rules_table(rules)

    except RuleLoadError as e:
        console.print(f"[error]{ICON_ERROR}[/error] Invalid: [path]{path}[/path]")
        console.print(f"  Error: {e}")
        raise typer.Exit(1) from e


def _validate_all_rules(verbose: bool) -> None:
    """Validate global and repo rules.

    Args:
        verbose: Whether to show detailed rule information
    """
    errors: list[Path] = []
    total_rules = 0
    all_rules = []

    # Check global rules
    if GLOBAL_RULES_PATH.exists():
        try:
            rules = _load_rule_file(GLOBAL_RULES_PATH)
            console.print(
                f"[success]{ICON_SUCCESS}[/success] Valid: "
                f"[path]{GLOBAL_RULES_PATH}[/path] ({len(rules)} rules)"
            )
            total_rules += len(rules)
            all_rules.extend(rules)
        except RuleLoadError as e:
            console.print(f"[error]{ICON_ERROR}[/error] Invalid: [path]{GLOBAL_RULES_PATH}[/path]")
            console.print(f"  Error: {e}")
            errors.append(GLOBAL_RULES_PATH)
    else:
        console.print(
            f"[warning]{ICON_WARNING}[/warning] Not found: [path]{GLOBAL_RULES_PATH}[/path]"
        )

    # Check repo rules
    repo_path = _find_repo_rules(Path.cwd())
    if repo_path:
        try:
            rules = _load_rule_file(repo_path)
            console.print(
                f"[success]{ICON_SUCCESS}[/success] Valid: "
                f"[path]{repo_path}[/path] ({len(rules)} rules)"
            )
            total_rules += len(rules)
            all_rules.extend(rules)
        except RuleLoadError as e:
            console.print(f"[error]{ICON_ERROR}[/error] Invalid: [path]{repo_path}[/path]")
            console.print(f"  Error: {e}")
            errors.append(repo_path)
    else:
        console.print("[muted]No repo rules found in current directory[/muted]")

    # Show verbose output
    if verbose and all_rules:
        console.print()
        _show_rules_table(all_rules)

    # Summary
    console.print()
    if errors:
        print_error(f"Validation failed: {len(errors)} file(s) with errors")
        raise typer.Exit(1)

    print_success(f"All rules valid: {total_rules} total rules")


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

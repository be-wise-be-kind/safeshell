# How to: Add CLI Commands

**Purpose**: Guide for extending SafeShell CLI with new commands

**Scope**: Typer app structure, command patterns, Rich output, testing

**Overview**: This guide explains how to add new commands to the SafeShell CLI. SafeShell
    uses Typer for CLI framework and Rich for terminal output. Understanding the
    existing patterns ensures consistent UX.

**Dependencies**: typer, rich, cli.py

**Exports**: CLI implementation patterns, testing approach

**Related**: ai-context.md for CLI architecture

**Implementation**: Step-by-step with code examples

---

## CLI Structure Overview

SafeShell CLI uses a hierarchical structure:

```
safeshell                    # Main entry point
├── version                  # Root command
├── init                     # Root command
├── check                    # Root command
├── status                   # Root command
├── monitor                  # Root command
├── up/down/restart          # Root commands
├── refresh                  # Root command
├── daemon                   # Subcommand group
│   ├── start
│   ├── stop
│   ├── restart
│   ├── status
│   └── logs
├── wrapper                  # Subcommand group
│   ├── install
│   └── path
├── rules                    # Subcommand group
│   └── validate
└── perf                     # Subcommand group
    └── benchmark
```

---

## Adding a Root Command

### Step 1: Define the Command

```python
# In src/safeshell/cli.py

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.command()
def my_command(
    name: str = typer.Argument(..., help="The name to process"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """
    Short description of what this command does.

    This longer description appears in --help output and explains
    the command's purpose and usage in more detail.
    """
    if verbose:
        console.print(f"[dim]Processing: {name}[/dim]")

    # Command logic here
    console.print(f"[green]Success![/green] Processed {name}")
```

### Step 2: Add Type Hints

All parameters must have type hints (MyPy strict mode):

```python
@app.command()
def list_rules(
    source: str | None = typer.Option(None, help="Filter by source"),
    limit: int = typer.Option(10, help="Max rules to show"),
) -> None:
    """List loaded rules."""
    ...
```

---

## Adding a Subcommand Group

### Step 1: Create Subcommand Module

```python
# In src/safeshell/mymodule/cli.py

import typer
from rich.console import Console

app = typer.Typer(help="My module commands")
console = Console()


@app.command()
def action1() -> None:
    """First action in this module."""
    console.print("Action 1 executed")


@app.command()
def action2(name: str) -> None:
    """Second action with parameter."""
    console.print(f"Action 2 for {name}")
```

### Step 2: Register in Main CLI

```python
# In src/safeshell/cli.py

from safeshell.mymodule.cli import app as mymodule_app

app.add_typer(mymodule_app, name="mymodule")
```

Now accessible as:
```bash
safeshell mymodule action1
safeshell mymodule action2 something
```

---

## Rich Output Patterns

### Console Setup

```python
from rich.console import Console

console = Console()

# Basic output
console.print("Hello, world!")

# Styled output
console.print("[green]Success[/green]")
console.print("[red]Error:[/red] Something went wrong")
console.print("[yellow]Warning:[/yellow] Be careful")
console.print("[dim]Debug info[/dim]")
```

### Tables

```python
from rich.table import Table

@app.command()
def list_items() -> None:
    """List items in a table."""
    table = Table(title="Items")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Count", justify="right")

    table.add_row("Item 1", "Active", "42")
    table.add_row("Item 2", "Inactive", "0")

    console.print(table)
```

### Panels

```python
from rich.panel import Panel

@app.command()
def show_info() -> None:
    """Show information in a panel."""
    content = """
    Name: SafeShell
    Version: 0.1.0
    Status: Running
    """
    console.print(Panel(content, title="System Info"))
```

### Progress Indicators

```python
from rich.progress import Progress

@app.command()
def process_items() -> None:
    """Process items with progress bar."""
    items = ["a", "b", "c", "d", "e"]

    with Progress() as progress:
        task = progress.add_task("Processing...", total=len(items))
        for item in items:
            # Process item
            time.sleep(0.5)
            progress.update(task, advance=1)
```

---

## Error Handling

### Using Typer Exit

```python
@app.command()
def risky_command() -> None:
    """Command that might fail."""
    try:
        result = do_something_risky()
    except SomeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    console.print("[green]Success![/green]")
```

### Graceful Degradation

```python
@app.command()
def check_status() -> None:
    """Check status with fallback."""
    try:
        status = get_daemon_status()
    except DaemonNotRunning:
        console.print("[yellow]Daemon not running[/yellow]")
        console.print("Start with: safeshell daemon start")
        raise typer.Exit(code=1)

    console.print(f"Status: {status}")
```

---

## CLI Modules Reference

| Module | Purpose | Commands |
|--------|---------|----------|
| `cli.py` | Root commands | version, init, check, status, monitor, up, down, restart, refresh |
| `daemon/cli.py` | Daemon management | start, stop, restart, status, logs |
| `wrapper/cli.py` | Wrapper setup | install, path |
| `rules/cli.py` | Rule management | validate |
| `perf/cli.py` | Performance | benchmark |

---

## Testing CLI Commands

### Using CliRunner

```python
# In tests/test_cli.py

from typer.testing import CliRunner
from safeshell.cli import app

runner = CliRunner()


def test_version_command():
    """Test version command outputs version."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_check_command_allow():
    """Test check command with allowed command."""
    result = runner.invoke(app, ["check", "ls -la"])
    assert result.exit_code == 0
    assert "ALLOW" in result.stdout


def test_check_command_deny(mocker):
    """Test check command with denied command."""
    # Mock rule evaluation to return DENY
    mocker.patch(
        "safeshell.daemon.client.evaluate_command",
        return_value=Decision(action="deny", reason="Test denial"),
    )

    result = runner.invoke(app, ["check", "rm -rf /"])
    assert result.exit_code == 0
    assert "DENY" in result.stdout
```

### Testing Subcommands

```python
def test_daemon_start(mocker):
    """Test daemon start command."""
    mock_start = mocker.patch("safeshell.daemon.lifecycle.start_daemon")

    result = runner.invoke(app, ["daemon", "start"])

    assert result.exit_code == 0
    mock_start.assert_called_once()


def test_rules_validate():
    """Test rules validation command."""
    result = runner.invoke(app, ["rules", "validate"])
    assert result.exit_code == 0
```

### Testing Error Cases

```python
def test_command_with_invalid_args():
    """Test command with missing required argument."""
    result = runner.invoke(app, ["check"])  # Missing command arg
    assert result.exit_code != 0
    assert "Missing argument" in result.stdout


def test_daemon_not_running(mocker):
    """Test error when daemon not running."""
    mocker.patch(
        "safeshell.daemon.client.get_status",
        side_effect=DaemonNotRunning(),
    )

    result = runner.invoke(app, ["status"])
    assert result.exit_code == 1
    assert "not running" in result.stdout.lower()
```

---

## Common Patterns

### Confirmation Prompt

```python
@app.command()
def dangerous_action(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Action that requires confirmation."""
    if not force:
        confirm = typer.confirm("Are you sure?")
        if not confirm:
            console.print("Aborted")
            raise typer.Abort()

    # Do the dangerous thing
    console.print("Done!")
```

### Optional JSON Output

```python
@app.command()
def show_data(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Show data in human or JSON format."""
    data = {"name": "test", "count": 42}

    if json_output:
        import json
        console.print(json.dumps(data, indent=2))
    else:
        console.print(f"Name: {data['name']}")
        console.print(f"Count: {data['count']}")
```

### Async Command Support

```python
import asyncio

@app.command()
def async_command() -> None:
    """Command that runs async code."""
    asyncio.run(_async_command())


async def _async_command() -> None:
    """Actual async implementation."""
    result = await some_async_operation()
    console.print(f"Result: {result}")
```

---

## Checklist for New Commands

- [ ] Command has descriptive docstring
- [ ] All parameters have type hints
- [ ] Parameters have help text
- [ ] Uses Rich console for output (not print)
- [ ] Error cases handled with proper exit codes
- [ ] Registered in appropriate app (root or subcommand)
- [ ] Unit tests with CliRunner
- [ ] Tests cover success and error cases
- [ ] AGENTS.md updated with new command (if user-facing)
- [ ] how-to-use-safeshell-cli.md updated (if user-facing)

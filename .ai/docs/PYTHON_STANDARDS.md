# Python Coding Standards

**Purpose**: PEP 8 compliance, naming conventions, and best practices for SafeShell

---

## Style Guidelines

### Line Length and Formatting
- Maximum line length: 100 characters
- Indentation: 4 spaces (no tabs)
- String quotes: Double quotes preferred
- Trailing commas: Use in multi-line structures

### Naming Conventions
- **Variables/Functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private members**: `_leading_underscore`
- **Module-level "private"**: `__double_leading_underscore`

### Import Organization
Imports should be grouped and ordered:
1. Standard library imports
2. Third-party imports
3. Local application imports

Each group separated by a blank line. Ruff handles this automatically.

```python
import os
import sys
from pathlib import Path

import typer
from rich.console import Console

from safeshell.core import evaluate_command
from safeshell.plugins import load_plugins
```

---

## Type Hints

Type hints are required for all function signatures.

### Basic Usage
```python
def process_command(command: str, timeout: int = 30) -> bool:
    """Process a shell command with timeout."""
    ...
```

### Complex Types
Use Python 3.11+ built-in generics:
```python
def get_plugins(names: list[str] | None = None) -> dict[str, Plugin]:
    """Load plugins by name."""
    ...
```

### Optional Values
```python
def find_config(path: Path | None = None) -> Config:
    """Find configuration file."""
    ...
```

---

## Docstrings

Use Google-style docstrings for all public functions and classes.

### Function Docstrings
```python
def evaluate_command(command: str, policy: Policy) -> EvalResult:
    """Evaluate a command against a security policy.

    Args:
        command: The shell command to evaluate.
        policy: The policy to evaluate against.

    Returns:
        The evaluation result with decision and reasoning.

    Raises:
        PolicyError: If the policy configuration is invalid.
    """
```

### Class Docstrings
```python
class SafeShellPlugin:
    """Base class for SafeShell plugins.

    Plugins extend SafeShell's command evaluation capabilities
    by implementing custom rules and checks.

    Attributes:
        name: The plugin's unique identifier.
        enabled: Whether the plugin is currently active.
    """
```

---

## Code Quality Tools

### Ruff (Linting + Formatting)
Primary tool for code quality. Handles:
- PEP 8 style enforcement
- Import sorting (replaces isort)
- Code formatting (replaces Black)
- Bug detection
- Security checks

```bash
ruff check .          # Check for issues
ruff check --fix .    # Auto-fix issues
ruff format .         # Format code
```

### MyPy (Type Checking)
Static type analysis with strict mode enabled.

```bash
mypy src              # Check types
```

### Bandit (Security)
Scans for common security issues.

```bash
bandit -r src         # Security scan
```

### Pylint (Comprehensive Linting)
Additional static analysis.

```bash
pylint src            # Full analysis
```

### Radon (Complexity)
Cyclomatic complexity analysis. Target: Grade A (complexity <= 5).

```bash
radon cc src -a       # Complexity report
```

### Thai-lint
Code quality patterns and best practices.

```bash
thailint .            # Quality checks
```

---

## Testing

### Test Organization
```
tests/
├── __init__.py
├── conftest.py           # Shared fixtures
├── test_cli.py           # CLI tests
├── test_core.py          # Core functionality
└── plugins/
    └── test_plugin_base.py
```

### Test Naming
```python
def test_evaluate_command_returns_allow_for_safe_commands():
    """Test that safe commands are allowed."""
    ...

def test_evaluate_command_returns_deny_for_dangerous_commands():
    """Test that dangerous commands are denied."""
    ...
```

### Fixtures
```python
@pytest.fixture
def sample_policy() -> Policy:
    """Create a sample policy for testing."""
    return Policy(rules=[...])
```

### Markers
```python
@pytest.mark.slow
def test_large_policy_evaluation():
    ...

@pytest.mark.integration
def test_end_to_end_command_execution():
    ...
```

---

## Error Handling

### Custom Exceptions
```python
class SafeShellError(Exception):
    """Base exception for SafeShell errors."""

class PolicyError(SafeShellError):
    """Raised when policy configuration is invalid."""

class EvaluationError(SafeShellError):
    """Raised when command evaluation fails."""
```

### Exception Handling
```python
try:
    result = evaluate_command(command, policy)
except PolicyError as e:
    console.print(f"[red]Policy error: {e}[/red]")
    raise typer.Exit(1)
except EvaluationError as e:
    console.print(f"[yellow]Evaluation failed: {e}[/yellow]")
    raise typer.Exit(2)
```

---

## Security Considerations

Since SafeShell is a security tool, extra care is required:

1. **Input Validation**: Always validate and sanitize inputs
2. **No Hardcoded Secrets**: Use environment variables or config files
3. **Command Parsing**: Be careful with shell metacharacters
4. **Path Handling**: Use pathlib, validate paths are within expected boundaries
5. **Logging**: Never log sensitive information

---

## Pre-Commit Hooks

Quality checks run automatically on commit:
- Ruff linting and formatting
- MyPy type checking
- Trailing whitespace removal
- YAML/TOML validation

---

## References

- [PEP 8](https://peps.python.org/pep-0008/) - Style Guide
- [PEP 484](https://peps.python.org/pep-0484/) - Type Hints
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [MyPy Documentation](https://mypy.readthedocs.io/)

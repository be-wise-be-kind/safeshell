# How to: Fix Linting Errors

**Purpose**: Step-by-step guide for fixing basic linting violations (code style, security, types)

**Scope**: Ruff, Pylint, MyPy, Bandit, thailint - mechanical fixes before architectural refactoring

**Overview**: This guide covers systematic fixing of objective linting violations - code style, formatting,
    security issues, and type checking. These are prerequisite fixes that should be completed before
    architectural refactoring (complexity and SRP). Follows an iterative fix-test cycle until all basic
    linting passes with exit code 0 and Pylint reaches exactly 10.00/10.

**Dependencies**: just lint, poetry

**Exports**: Clean code passing all basic linting checks

**Related**: ai-rules.md for quality gates

**Implementation**: Sequential priority-based fixing with validation after each phase

---

## Overview

Basic linting fixes are **objective and mechanical** - they have clear right/wrong answers and don't require architectural decisions. Fix these first before tackling complexity or SRP violations.

**The Process**:
1. Run `just lint` to see all violations
2. Fix violations in priority order (style → security → types → pylint → thailint)
3. Run `just lint` again to verify
4. Run `just test` to ensure nothing broke
5. Repeat until clean

**Success Criteria**:
- `just lint-full` exits with code 0
- Pylint score is exactly 10.00/10
- All tests pass (`just test` exits with code 0)

---

## The Iterative Cycle

### Step 1: Assess Current State

```bash
# Run full linting to see all violations
just lint-full

# Look for Pylint score
# Must show: "Your code has been rated at 10.00/10"
```

### Step 2: Fix Violations by Priority

Follow the priority order below. Don't skip ahead - each phase builds on the previous.

### Step 3: Validate After Each Priority

```bash
# After fixing each priority level, validate
just lint
just test

# Both must exit with code 0
```

### Step 4: Repeat Until Clean

Continue the cycle until:
- `just lint-full` shows no violations
- Exit code is 0
- Pylint shows 10.00/10
- Tests all pass

---

## Priority 1: Code Style & Formatting

**Tools**: Ruff (formatter + linter)

**Why First**: Style issues are easiest to fix and auto-fixable. Get them out of the way.

### Auto-Fix with Ruff

```bash
# Auto-fix most style issues
just format

# This runs:
# - ruff format (fixes formatting)
# - ruff check --fix (fixes auto-fixable linting issues)
```

### Common Ruff Violations

#### Line Too Long (E501)

**Error**:
```
src/safeshell/example.py:10:101: E501 Line too long (120 > 100 characters)
```

**Fix**: Break into multiple lines
```python
# Before
some_function(arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9)

# After
some_function(
    arg1, arg2, arg3,
    arg4, arg5, arg6,
    arg7, arg8, arg9
)
```

#### Unused Imports (F401)

**Error**:
```
src/safeshell/example.py:5:1: F401 'pathlib.Path' imported but unused
```

**Fix**: Remove the import
```python
# Before
from pathlib import Path
import sys

# After
import sys
```

---

## Priority 2: Security Issues

**Tools**: Bandit

**Why Second**: Security vulnerabilities must be fixed before moving forward.

### Running Security Checks

```bash
# Run security linting
just lint-security
```

### Common Bandit Violations

#### B602: Subprocess with Shell=True

**IMPORTANT**: SafeShell uses plumbum, NOT subprocess. This violation shouldn't occur.

**Fix**: Use plumbum for shell execution
```python
# WRONG - Never use subprocess in SafeShell
import subprocess
subprocess.run("ls -la", shell=True)

# CORRECT - Use plumbum
from plumbum import local
ls = local["ls"]
result = ls["-la"]()
```

#### B105: Hardcoded Password

**Fix**: Use environment variables
```python
# Before
password = "secret123"

# After
import os
password = os.environ.get("DB_PASSWORD")
```

### Suppressing False Positives

When Bandit flags a false positive:

```python
# Use nosec comment with justification
password_field = "password"  # nosec B105 - This is a field name, not a password
```

---

## Priority 3: Type Checking

**Tools**: MyPy (strict mode)

**Why Third**: Type checking catches potential runtime errors and improves code clarity.

### Running Type Checks

```bash
# Run type checking
just lint-all
```

### Common MyPy Violations

#### Missing Type Annotations

**Fix**: Add type hints
```python
# Before
def calculate(x, y):
    return x + y

# After
def calculate(x: int, y: int) -> int:
    return x + y
```

#### Optional Type Handling

**Fix**: Check for None before using
```python
# Before
def process(value: str | None) -> str:
    return value.upper()  # value might be None

# After
def process(value: str | None) -> str:
    if value is None:
        return ""
    return value.upper()
```

### Type Hints Quick Reference

```python
from pathlib import Path
from typing import Any

# Basic types
def func(x: int, y: str, z: bool) -> float:
    pass

# Collections
def func(items: list[str]) -> dict[str, int]:
    pass

# Optional (can be None)
def func(value: str | None) -> int | None:
    pass

# No return value
def func() -> None:
    pass
```

---

## Priority 4: Pylint Violations

**Tools**: Pylint

**Why Fourth**: Pylint is strictest and requires all previous fixes to be done first.

**Goal**: Reach exactly 10.00/10

### Running Pylint

```bash
# Run Pylint
just lint-all

# Must show: "Your code has been rated at 10.00/10"
```

### Common Pylint Violations

#### Invalid Name (C0103)

**Fix**: Use snake_case
```python
# Before
MyVariable = "test"

# After
my_variable = "test"
```

#### Unused Variable (W0612)

**Fix**: Remove or use the variable
```python
# Before
def calculate():
    result = expensive_operation()
    return 42

# After
def calculate():
    return expensive_operation()
```

---

## Priority 5: thailint Violations

**Tools**: thailint (magic-numbers, nesting, srp, dry, file-placement)

### Running thailint Checks

```bash
# Run all thailint checks
just lint-thai
```

### Common thailint Violations

#### Magic Numbers

**Fix**: Extract to named constants
```python
# Before
if retry_count > 3:
    pass

# After
MAX_RETRIES = 3
if retry_count > MAX_RETRIES:
    pass
```

#### Excessive Nesting

**Fix**: Early returns or extract functions
```python
# Before - too deep
if condition1:
    if condition2:
        if condition3:
            do_something()

# After - early returns
if not condition1:
    return
if not condition2:
    return
if not condition3:
    return
do_something()
```

---

## SafeShell-Specific Standards

### Use Rich Console (NOT print)

```python
# WRONG
print("Hello")

# CORRECT
from rich.console import Console
console = Console()
console.print("Hello")
```

### Use Loguru (NOT stdlib logging)

```python
# WRONG
import logging
logging.info("message")

# CORRECT
from loguru import logger
logger.info("message")
```

### Use Plumbum (NOT subprocess)

```python
# WRONG
import subprocess
subprocess.run(["ls", "-la"])

# CORRECT
from plumbum import local
ls = local["ls"]
result = ls["-la"]()
```

### Use Pydantic (NOT dataclass)

```python
# WRONG
from dataclasses import dataclass
@dataclass
class Config:
    name: str

# CORRECT
from pydantic import BaseModel
class Config(BaseModel):
    name: str
```

---

## Quick Reference: Common Errors

| Error | Tool | Fix |
|-------|------|-----|
| Line too long | Ruff E501 | Break into multiple lines |
| Unused import | Ruff F401 | Remove import |
| Hardcoded password | Bandit B105 | Use environment variables |
| Missing type hint | MyPy | Add type annotations |
| Invalid name | Pylint C0103 | Use snake_case |
| Unused variable | Pylint W0612 | Remove or use variable |
| Magic number | thailint | Extract to constant |

---

## Suppression Comments

**CRITICAL: NEVER add suppression comments without user permission!**

Before adding any of these:
- `# type: ignore` (MyPy)
- `# pylint: disable=rule` (Pylint)
- `# noqa` (Ruff)
- `# nosec` (Bandit)

**Required Process:**
1. Try to fix the issue properly first
2. If impossible to fix, EXPLAIN to the user
3. ASK for explicit permission
4. Only then add the suppression with detailed justification

**SafeShell Rule**: No method-level noqa comments. Use file-level or project-level suppression if needed.

---

## Success Checklist

Before committing:

- [ ] `just lint-full` exits with code 0
- [ ] Pylint score is exactly 10.00/10
- [ ] `just test` exits with code 0
- [ ] No Ruff violations
- [ ] No Bandit security issues
- [ ] No MyPy type errors
- [ ] No thailint violations
- [ ] All functions have type hints
- [ ] Using Rich console (not print)
- [ ] Using Loguru (not logging)
- [ ] Using plumbum (not subprocess)
- [ ] Using Pydantic (not dataclass)

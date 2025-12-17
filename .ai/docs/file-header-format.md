File: .ai/docs/file-header-format.md

Purpose: Specification for standardized Python file headers

Exports: Header format specification, required fields, examples

Depends: None

Overview: Defines the standardized file header format required for all Python files
    in this project. Includes required and optional fields, atemporal language rules,
    and complete examples.

# Python File Header Format

**Purpose**: Specification for standardized Python file headers in this project

---

## Required Fields

All Python files must start with a docstring containing these fields:

| Field | Required | Description |
|-------|----------|-------------|
| File | Yes | Relative path from project root |
| Purpose | Yes | Brief description (1-2 lines) |
| Exports | Yes | Main classes, functions, constants |
| Depends | Yes | Key dependencies |
| Implements | No | Key APIs or methods |
| Related | No | Related files or documentation |
| Overview | Yes | Comprehensive summary (3-5+ lines) |
| Usage | No | Example usage |
| Notes | No | Optional implementation notes |

---

## Template

```python
"""
File: <relative path from project root>

Purpose: <Brief description, 1-2 lines>

Exports: <Main classes, functions, constants>

Depends: <Key dependencies>

Implements: <Key APIs or methods>

Related: <Related files or documentation>

Overview: <Comprehensive summary, 3-5+ lines>

Usage: <Example usage>

Notes: <Optional implementation notes>
"""
```

---

## Atemporal Language

Documentation must be timeless. Never reference time, dates, or changes.

| Avoid | Use Instead |
|-------|-------------|
| "Currently supports..." | "Supports..." |
| "Recently added..." | "Provides..." |
| "Will implement..." | "Implements..." |
| "Changed from X to Y" | "Handles..." |
| "As of version X..." | "In version X..." |
| "Coming soon..." | (remove or implement first) |

---

## Example

```python
"""
File: src/safeshell/rules/evaluator.py

Purpose: Rule evaluation engine for command matching

Exports: RuleEvaluator, evaluate_command

Depends: rules/schema.py, rules/condition_types.py, models.py

Implements: Command matching, condition evaluation, decision aggregation

Related: rules/loader.py, daemon/manager.py

Overview: Implements the core rule evaluation logic for SafeShell. Takes a command
    and context, matches against loaded rules, evaluates conditions, and returns
    an aggregated decision. Uses fast-path optimization for commands not in the
    rule index. Supports structured Python conditions for performance.

Usage: evaluator = RuleEvaluator(rules); decision = evaluator.evaluate(cmd, ctx)

Notes: Decision aggregation follows DENY > REQUIRE_APPROVAL > REDIRECT > ALLOW
"""
```

---

## Markdown File Headers

Markdown files use a simplified plain-text header at the top:

```markdown
File: <relative path>

Purpose: <Brief description>

Exports: <What this document provides>

Depends: <Related documents>

Overview: <Comprehensive summary>

# Document Title

Content starts here...
```

---

## YAML File Headers

YAML files use comment-style headers:

```yaml
# File: <relative path>
# Purpose: <Brief description>
# Exports: <What this configuration provides>
# Depends: <Related configurations>
# Overview: <Comprehensive summary>

# Configuration starts here
key: value
```

---

## See Also

- [how-to-write-file-headers.md](../howtos/how-to-write-file-headers.md) - Step-by-step guide
- [file-header-python.template](../templates/file-header-python.template) - Copy-paste template

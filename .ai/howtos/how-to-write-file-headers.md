# How to: Write File Headers

**Purpose**: Step-by-step guide for writing compliant file headers for all file types

**Scope**: All code, configuration, and documentation files in SafeShell

**Overview**: This practical guide walks through the process of writing effective file headers for markdown,
    Python, TypeScript, YAML, and other file types. Covers the atemporal documentation principle, mandatory
    fields, file-type specific formatting, template usage, and common mistakes. Provides concrete examples
    and a verification checklist to ensure headers meet standards.

**Dependencies**: File header templates (.ai/templates/)

**Exports**: Practical file header creation process, examples, and verification checklist

**Related**: Python files in src/safeshell/

**Implementation**: Step-by-step process with examples and checklists

---

## Python File Header Format

All Python files must use this header format:

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

## Mandatory Fields

1. **File** - Relative path from project root
2. **Purpose** - Brief description (1-2 lines)
3. **Exports** - Main classes, functions, constants
4. **Depends** - Key dependencies
5. **Overview** - Comprehensive summary (3-5+ lines)

## Atemporal Language

**Key Rule**: Never reference time, dates, or changes.

### What to Avoid
- "Currently supports..."
- "Recently added..."
- "Will implement..."
- "Changed from X to Y"

### What to Use Instead
- "Supports..."
- "Provides..."
- "Implements..."
- "Handles..."

## Example

```python
"""
File: src/safeshell/plugins/rm_protect.py

Purpose: Plugin to protect against accidental file deletion

Exports: RmProtectPlugin class

Depends: Plugin base class, pathlib

Implements: evaluate() method for rm command interception

Related: docs/plugins.md, src/safeshell/daemon/plugin_loader.py

Overview: Implements the rm-protect plugin that intercepts rm commands and
    evaluates them against configurable rules. Supports soft-delete to trash,
    allowlisting, and human approval for protected paths. Uses glob patterns
    for path matching and integrates with the daemon's event system.

Usage: Automatically loaded by daemon when enabled in config

Notes: None
"""
```

## Markdown File Header Format

Markdown files use a simplified plain-text header:

```markdown
File: <relative path>

Purpose: <Brief description>

Exports: <What this document provides>

Depends: <Related documents>

Overview: <Comprehensive summary>

# Document Title

Content starts here...
```

## Verification Checklist

- [ ] File field present with correct path
- [ ] Purpose field present (1-2 lines)
- [ ] Exports field lists all public items
- [ ] Depends field lists key dependencies
- [ ] Overview field present (3-5+ lines)
- [ ] No temporal language used
- [ ] Header is at top of file

---

## See Also

- [file-header-format.md](../docs/file-header-format.md) - Detailed specification with all fields
- [file-header-python.template](../templates/file-header-python.template) - Copy-paste template

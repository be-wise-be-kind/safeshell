# AI Agent Guide - SafeShell

**Purpose**: Primary entry point for AI agents working on this project

**Quick Start**: Read `.ai/index.yaml` for navigation, then `.ai/ai-context.md` and `.ai/ai-rules.md` for full context.

---

## MANDATORY: First Action for Every Task

**BEFORE working on ANY task, you MUST:**

1. **READ** `.ai/index.yaml` to see what documentation exists
2. **READ** `.ai/ai-context.md` for development patterns and project structure
3. **READ** `.ai/ai-rules.md` for quality gates and rules
4. **IDENTIFY** relevant documents from index.yaml for your specific task
5. **INFORM** the user which documents you are using

**This is NOT optional.** Skipping this step leads to incomplete work and quality issues.

---

## Two Types of Requests

### Development Efforts (Making Changes to Code/Repo)

When users want to modify code, add features, fix bugs, or update the repo:

1. **Read core docs**: ai-context.md (patterns) + ai-rules.md (gates)
2. **Check for howtos**: Look in `.ai/howtos/` for task-specific guides
3. **Use templates**: Use `.ai/templates/` for new files
4. **Follow patterns**: Match existing code patterns
5. **Run quality gates**: `just lint-full` before committing

**Examples:**
- "Create a new module" → Read ai-context.md for module structure, use templates
- "Fix linting errors" → Read ai-rules.md for quality gates
- "Add a CLI command" → Read ai-context.md for CLI patterns
- "Write file headers" → Read `.ai/howtos/how-to-write-file-headers.md`

### Usage Efforts (Using the Tools)

When users want to USE the safeshell CLI to perform operations:

1. **Primary tool**: The `safeshell` CLI
2. **Navigation pattern**: Use `--help` to discover commands
   - `safeshell --help` → List all commands
   - `safeshell <command> --help` → Detailed command help
3. **Use command tables below** for common question-to-command mappings

For detailed CLI navigation, see `.ai/howtos/how-to-use-safeshell-cli.md`.

### Roadmap Work

When users want to plan features or continue roadmap work:

**Detection patterns:**
- Planning: "plan", "roadmap", "break down", "create a roadmap"
- Continuing: "continue", "resume", "what's next", "let's continue", "continue working on"

**For continuation requests, you MUST:**

1. **Check `.roadmap/in-progress/`** for active roadmaps
2. **Read `PROGRESS_TRACKER.md` FIRST** - this is the primary handoff document
3. **Find "Next PR to Implement"** section - this tells you what to do
4. **Read `PR_BREAKDOWN.md`** for detailed implementation steps
5. **Implement the PR** following the detailed steps
6. **Update `PROGRESS_TRACKER.md`** immediately after completing:
   - Change PR status: 🔴 → 🟢
   - Add commit hash to Notes column
   - Update "Next PR to Implement" to next PR
   - Update overall progress percentage
7. **Commit the progress tracker update**

**For planning requests:**
- Read `.ai/howtos/how-to-roadmap.md` for complete instructions
- Create roadmap in `.roadmap/planning/[feature-name]/`

**Resources:**
- Guide: `.ai/howtos/how-to-roadmap.md`
- Active roadmaps: `.roadmap/in-progress/`
- Planned roadmaps: `.roadmap/planning/`
- Completed roadmaps: `.roadmap/complete/`

---

## Quick Start

1. **Read documentation** - `.ai/index.yaml`, `.ai/ai-context.md`, `.ai/ai-rules.md`
2. Read the relevant module's files before making changes
3. Follow existing patterns in the codebase
4. Run quality gates before committing: `just lint-full`
5. All code must pass: Ruff, Pylint, MyPy, Bandit, thailint

---

## Question-to-Command Mapping

When users ask questions, identify the relevant command.

### Discovery Commands

```bash
safeshell --help                    # List all available commands
safeshell <command> --help          # Get detailed help for a command
```

### Core Commands

| Question | Command |
|----------|---------|
| "What version?" | `safeshell version` |
| "How do I set up SafeShell?" | `safeshell init` |
| "Is this command safe?" | `safeshell check "<command>"` |
| "Is the daemon running?" | `safeshell status` |

---

## Resources

### Documentation
- **Index**: `.ai/index.yaml` - File lookup and navigation
- **Context**: `.ai/ai-context.md` - Development patterns and conventions
- **Rules**: `.ai/ai-rules.md` - Quality gates and mandatory rules
- **How-Tos**: `.ai/howtos/` - Step-by-step guides
- **Templates**: `.ai/templates/` - File creation templates

### Getting Help

When stuck:
1. Check `.ai/index.yaml` for navigation
2. Review `.ai/howtos/` for guides
3. Check existing code for patterns
4. Review quality gate output for specific errors

---

**Remember**: Always start by reading the core documents and informing the user which documents you're using. This ensures you have the full context needed to complete the task correctly.

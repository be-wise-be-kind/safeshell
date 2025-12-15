# Phase 7: Performance Optimization - Progress Tracker

**Purpose**: Track progress on performance optimization for SafeShell (Python)

**Current Status**: PR4 Pending - Structured Python Conditions

---

## Current Status
**Current PR**: PR4 Pending (Highest Priority)
**Branch**: `feat/phase7-performance`
**Last Updated**: 2025-12-15

## Overall Progress
**Total Completion**: 33% (2/6 PRs completed)

```
[██████░░░░░░░░░░░░░░] 33% Complete
```

---

## PR Status Dashboard

| PR | Title | Status | Branch | Notes |
|----|-------|--------|--------|-------|
| PR1 | Caching Infrastructure | 🟢 Complete | `feat/phase7-performance` | Caching for evaluator, conditions, git context |
| PR2 | Python Condition DSL | 🟡 Partial | `feat/phase7-performance` | Auto-translation insufficient - see PR4-6 |
| PR3 | Profiling Infrastructure | 🔴 Not Started | - | Deferred until PR4-6 complete |
| PR4 | Structured Condition Schema | 🔴 Not Started | - | **PRIORITY** - New YAML condition format |
| PR5 | Condition Evaluators | 🔴 Not Started | - | Python evaluators for all condition types |
| PR6 | Deprecate Bash Conditions | 🔴 Not Started | - | Migration path, deprecation warnings |

---

## PR1: Caching Infrastructure ✅

**Status**: 🟢 Complete
**Branch**: `feat/phase7-performance`

### Completed Work
- [x] Add `ConditionCache` class with TTL-based expiration (5s default)
- [x] Cache `RuleEvaluator` instance when rules haven't changed
- [x] Persist condition cache across requests (was cleared per evaluate())
- [x] Pre-compile directory regex patterns at evaluator init
- [x] Add git context caching with 10-second TTL
- [x] Add 15 new tests for caching functionality
- [x] All 256 tests passing

### Files Modified
- `src/safeshell/rules/evaluator.py` - ConditionCache, regex precompilation
- `src/safeshell/daemon/manager.py` - Evaluator caching, shared condition cache
- `src/safeshell/models.py` - Git context caching
- `tests/rules/test_condition_cache.py` - New test file
- `tests/test_git_context_cache.py` - New test file

### Performance Impact
- Evaluator reuse: ~1-2ms saved per request
- Condition cache hits: ~5-20ms saved per repeated condition
- Git context cache: ~1-5ms saved per repeated directory
- **Note**: Primary bottleneck (bash subprocess spawning) still exists

---

## PR2: Python Condition DSL 🟡

**Status**: 🟡 Partial (Superseded by PR4-6)
**Achieved Impact**: Limited - only helps for recognized bash patterns

### What Was Done
- [x] Created `src/safeshell/rules/conditions.py` with Python condition classes
- [x] Auto-translation of common bash patterns to Python
- [x] Added 31 tests

### Why This Was Insufficient
The auto-translation approach has fundamental limitations:
1. **Still uses bash strings in YAML** - Users still write bash conditions
2. **Pattern matching is fragile** - Regex parsing of bash is error-prone
3. **Unrecognized patterns fall back to bash** - Still spawns subprocesses
4. **Shell integration overhead** - The `echo`/`eval` overrides in `init.bash` still call the wrapper for every command

### Lessons Learned
The real fix requires **structured Python conditions** in the rule schema itself, not auto-translation of bash strings. See PR4-6 for the correct approach.

---

## PR3: Profiling Infrastructure 🔴

**Status**: 🔴 Deferred (until PR4-6 complete)
**Depends On**: PR6

### Objectives
- [ ] Create `src/safeshell/performance.py` module
- [ ] Add `PerformanceTracker` class with timing context manager
- [ ] Instrument critical paths (manager, evaluator, conditions)
- [ ] Add `safeshell perf-stats` CLI command
- [ ] Create benchmark scripts

---

## PR4: Structured Condition Schema 🔴

**Status**: 🔴 Not Started (HIGHEST PRIORITY)
**Estimated Impact**: Eliminates bash subprocess spawning entirely

### Objectives
Replace bash condition strings with structured Python-evaluatable conditions in rules.yaml.

### New Condition Format
```yaml
# OLD (bash strings - spawns subprocess):
conditions:
  - 'echo "$CMD" | grep -qE "^git\\s+commit"'
  - 'git branch --show-current | grep -qE "^(main|master)$"'

# NEW (structured - pure Python evaluation):
conditions:
  - command_matches: "^git\\s+commit"
  - git_branch_in: ["main", "master", "develop"]
```

### Supported Condition Types
| Condition | Description | Example |
|-----------|-------------|---------|
| `command_matches` | Regex match on full command | `command_matches: "^git\\s+push"` |
| `command_contains` | Literal substring match | `command_contains: "--force"` |
| `command_startswith` | Command prefix match | `command_startswith: "rm -rf"` |
| `git_branch_in` | Current branch in list | `git_branch_in: ["main", "master"]` |
| `git_branch_matches` | Regex match on branch | `git_branch_matches: "^release/"` |
| `in_git_repo` | Is working dir a git repo | `in_git_repo: true` |
| `path_matches` | Working dir matches pattern | `path_matches: "/home/.*/projects"` |
| `file_exists` | File exists in working dir | `file_exists: ".gitignore"` |
| `env_equals` | Environment variable check | `env_equals: {SAFESHELL_CONTEXT: "ai"}` |

### Files to Modify
- `src/safeshell/rules/schema.py` - Add structured condition types
- `src/safeshell/rules/defaults.py` - Update default rules to new format

### Tasks
- [ ] Define Pydantic models for each condition type
- [ ] Add union type for conditions in Rule schema
- [ ] Support both old (string) and new (structured) formats temporarily
- [ ] Update schema validation
- [ ] Add tests for new condition schema

---

## PR5: Condition Evaluators 🔴

**Status**: 🔴 Not Started
**Depends On**: PR4

### Objectives
Implement Python evaluators for all structured condition types.

### Files to Modify
- `src/safeshell/rules/conditions.py` - Evaluator implementations
- `src/safeshell/rules/evaluator.py` - Use new evaluators

### Architecture
```python
class ConditionEvaluator(ABC):
    @abstractmethod
    def evaluate(self, context: CommandContext) -> bool: ...

class CommandMatchesEvaluator(ConditionEvaluator):
    def __init__(self, pattern: str):
        self._compiled = re.compile(pattern)

    def evaluate(self, context: CommandContext) -> bool:
        return self._compiled.search(context.raw_command) is not None

class GitBranchInEvaluator(ConditionEvaluator):
    def __init__(self, branches: list[str]):
        self._branches = set(branches)

    def evaluate(self, context: CommandContext) -> bool:
        return context.git_branch in self._branches
```

### Tasks
- [ ] Implement evaluator for each condition type
- [ ] Pre-compile regex patterns at rule load time
- [ ] Update `_check_condition()` to use structured evaluators
- [ ] Add comprehensive tests
- [ ] Benchmark: verify <0.1ms per condition

---

## PR6: Deprecate Bash Conditions 🔴

**Status**: 🔴 Not Started
**Depends On**: PR5

### Objectives
Provide migration path and deprecate bash condition strings.

### Tasks
- [ ] Add deprecation warning when bash conditions are used
- [ ] Create migration guide documentation
- [ ] Add `safeshell migrate-rules` CLI command to auto-convert
- [ ] Update all documentation to use new format
- [ ] Update default rules to new format
- [ ] Consider removing bash fallback entirely (breaking change)

### Migration Command
```bash
# Auto-convert old rules to new format
safeshell migrate-rules ~/.safeshell/rules.yaml
```

---

## Performance Targets

| Metric | Current (Est.) | Target | Status |
|--------|----------------|--------|--------|
| Command overhead | 20-50ms | < 10ms | Improved (PR2) |
| Rule evaluation | 10-30ms | < 1ms | Improved (PR2) |
| Condition check | 5-20ms | < 0.1ms | ✅ Done (PR2) |
| Git context | 1-5ms | < 0.1ms | ✅ Done (PR1) |

---

## Root Cause Analysis

### Why Simple Commands Are Still Slow
1. **Shell integration overhead** - `init.bash` overrides `echo`, `eval`, etc.
2. **Every builtin call goes through SafeShell** - Even shell hooks (Warp Precmd, etc.)
3. **Wrapper → Daemon roundtrip** - Each call requires IPC, even for fast-path allow
4. **Bash conditions still spawn subprocesses** - PR2's auto-translation only catches some patterns

### The Real Problem
The fundamental issue is that bash condition strings in `rules.yaml` require either:
- Bash subprocess spawning (slow: 5-20ms)
- Complex regex parsing to auto-translate (fragile, incomplete)

### The Correct Solution (PR4-6)
Replace bash strings with **structured Python conditions** in the rule schema:
```yaml
# Instead of this (requires bash or complex parsing):
conditions:
  - 'echo "$CMD" | grep -qE "^git\\s+commit"'

# Use this (pure Python, <0.1ms):
conditions:
  - command_matches: "^git\\s+commit"
```

This eliminates bash entirely and makes conditions:
- Fast (pure Python, no subprocess)
- Readable (clear intent)
- Type-safe (validated by Pydantic)
- Extensible (easy to add new condition types)

---

## Notes for AI Agents

### Priority
**PR4 is the highest priority** - structured condition schema is the foundation.
PR5 and PR6 build on PR4. PR3 (profiling) is deferred until conditions are fixed.

### Key Files
- `src/safeshell/rules/schema.py` - Rule schema (modify for PR4)
- `src/safeshell/rules/conditions.py` - Condition evaluators (modify for PR5)
- `src/safeshell/rules/evaluator.py` - Core evaluation logic
- `src/safeshell/rules/defaults.py` - Default rules (update format)
- `src/safeshell/shims/init.bash` - Shell integration (AI-only mode added)

### Architecture Decision
Structured conditions use a discriminated union pattern in Pydantic:
```python
Condition = Annotated[
    CommandMatches | CommandContains | GitBranchIn | ...,
    Field(discriminator="type")
]
```

Each condition type is a Pydantic model with a `type` field for discrimination
and type-specific fields for the condition parameters.

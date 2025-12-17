# Phase 6: Performance Optimization - PR Breakdown

**Purpose**: Detailed implementation breakdown of Phase 6: Performance Optimization into manageable, atomic pull requests

**Scope**: Complete performance optimization from profiling infrastructure setup through documentation and regression testing

**Overview**: Comprehensive breakdown of the Phase 6: Performance Optimization feature into 3 manageable, atomic
    pull requests. Each PR is designed to be self-contained, testable, and maintains application functionality
    while incrementally building toward production-ready performance. Includes detailed implementation steps, file
    structures, testing requirements, and success criteria for each PR.

**Dependencies**:
- Phases 1-5 complete (daemon, rules, context-awareness, monitoring)
- Rust toolchain with criterion benchmarking
- Profiling tools (flamegraph, perf)

**Exports**: PR implementation plans, file structures, testing strategies, and success criteria for each development phase

**Related**: AI_CONTEXT.md for feature overview, PROGRESS_TRACKER.md for status tracking

**Implementation**: Atomic PR approach with detailed step-by-step implementation guidance and comprehensive testing validation

---

## Overview
This document breaks down the Phase 6: Performance Optimization feature into manageable, atomic PRs. Each PR is designed to be:
- Self-contained and testable
- Maintains a working application
- Incrementally builds toward production-ready performance
- Revertible if needed

---

## PR1: Profiling Infrastructure and Benchmark Suite

**Branch**: `feature/phase6-profiling-infrastructure`
**Estimated Effort**: 2-3 days
**Complexity**: High
**Priority**: P0

### Objectives
Establish comprehensive profiling infrastructure and benchmark suite to measure performance of all critical paths, providing the foundation for data-driven optimization.

### What This PR Does
- Sets up profiling infrastructure with flamegraph support
- Creates benchmark suite for daemon startup time
- Creates benchmark suite for rule evaluation latency
- Creates benchmark suite for shim overhead per command
- Creates benchmark suite for monitor TUI responsiveness
- Documents profiling procedures and baseline measurements

### Files to Create
```
benchmarks/
├── Cargo.toml                      # Benchmark workspace configuration
├── README.md                       # Profiling and benchmarking guide
├── daemon_startup.rs               # Daemon startup time benchmarks
├── rule_evaluation.rs              # Rule evaluation latency benchmarks
├── shim_overhead.rs                # Shim command interception benchmarks
├── monitor_tui.rs                  # Monitor TUI responsiveness benchmarks
├── common/
│   ├── mod.rs                      # Shared benchmark utilities
│   ├── test_rules.rs               # Test rule configurations
│   └── fixtures.rs                 # Test fixtures and data
└── baseline/
    └── measurements.json            # Baseline performance measurements
```

### Files to Modify
```
Cargo.toml                          # Add criterion dependency, benchmark configuration
.github/workflows/benchmarks.yml    # CI for running benchmarks (optional)
README.md                           # Add performance section
```

### Implementation Steps

#### Step 1: Set Up Benchmark Infrastructure
1. Add criterion to Cargo.toml:
```toml
[dev-dependencies]
criterion = { version = "0.5", features = ["html_reports"] }

[[bench]]
name = "daemon_startup"
harness = false

[[bench]]
name = "rule_evaluation"
harness = false

[[bench]]
name = "shim_overhead"
harness = false

[[bench]]
name = "monitor_tui"
harness = false
```

2. Create benchmarks/ directory structure
3. Set up common utilities for test fixtures

#### Step 2: Daemon Startup Benchmarks
1. Benchmark cold start time (no cache)
2. Benchmark warm start time (with cache)
3. Benchmark with varying configuration sizes
4. Measure memory usage at startup
5. Test cases:
   - Empty configuration
   - Small config (10 rules)
   - Medium config (100 rules)
   - Large config (1000 rules)

#### Step 3: Rule Evaluation Benchmarks
1. Benchmark single rule evaluation
2. Benchmark ruleset evaluation (all rules)
3. Benchmark with different rule complexities:
   - Simple pattern match rules
   - Complex regex rules
   - Context-aware rules (ai_only/human_only)
4. Benchmark rule caching effectiveness
5. Test cases:
   - Best case: First rule matches
   - Average case: Middle rule matches
   - Worst case: No rule matches (all evaluated)

#### Step 4: Shim Overhead Benchmarks
1. Benchmark total command latency:
   - Command interception
   - IPC to daemon
   - Rule evaluation
   - Response back to shim
   - Command execution
2. Benchmark IPC overhead specifically
3. Compare against native command execution
4. Test with different command types:
   - Allowed commands (fast path)
   - Denied commands (should be fast)
   - Approval-required commands

#### Step 5: Monitor TUI Benchmarks
1. Benchmark event handling latency
2. Benchmark render time for different log sizes:
   - 100 entries
   - 1000 entries
   - 10000 entries
3. Benchmark scrolling performance
4. Benchmark filter application
5. Measure frame time (target: < 16ms for 60fps)

#### Step 6: Profiling Tools Integration
1. Add flamegraph support:
```bash
cargo install flamegraph
cargo flamegraph --bench daemon_startup
```

2. Document profiling procedures in benchmarks/README.md:
   - How to run benchmarks
   - How to generate flamegraphs
   - How to interpret results
   - How to compare against baselines

3. Create helper scripts:
   - `scripts/profile.sh` - Run profiling
   - `scripts/benchmark.sh` - Run all benchmarks
   - `scripts/compare-baseline.sh` - Compare against baseline

#### Step 7: Establish Baselines
1. Run all benchmarks on current implementation
2. Record baseline measurements to benchmarks/baseline/measurements.json
3. Document system specs used for baseline
4. Create comparison script for future runs

### Testing Requirements
- All benchmarks run successfully with `cargo bench`
- Benchmarks produce consistent results (low variance)
- HTML reports generated correctly
- Flamegraphs generate successfully
- Baseline measurements recorded

### Success Criteria
- [ ] Comprehensive benchmark suite covers all critical paths
- [ ] Profiling infrastructure documented and functional
- [ ] Baseline measurements established
- [ ] Benchmarks integrated into development workflow
- [ ] All benchmarks pass and produce meaningful metrics

### Documentation Requirements
- benchmarks/README.md with:
  - How to run benchmarks
  - How to profile with flamegraph
  - How to interpret results
  - Baseline measurements
  - System requirements for benchmarking

---

## PR2: Optimize Identified Hot Paths

**Branch**: `feature/phase6-optimize-hot-paths`
**Estimated Effort**: 3-5 days
**Complexity**: High
**Priority**: P0
**Blocked By**: PR1

### Objectives
Analyze profiling data from PR1, identify performance bottlenecks, and systematically optimize hot paths to meet production performance targets.

### What This PR Does
- Analyzes profiling data to identify bottlenecks
- Optimizes command interception → daemon → response path
- Optimizes rule evaluation performance
- Reduces daemon startup time
- Improves monitor TUI responsiveness
- Validates all optimizations with benchmarks

### Files to Modify (TBD based on profiling)
Common optimization targets:
```
src/daemon/server.rs                # Daemon IPC optimization
src/daemon/rules.rs                 # Rule evaluation optimization
src/shim/main.rs                    # Shim overhead reduction
src/monitor/tui.rs                  # TUI rendering optimization
src/daemon/state.rs                 # State management optimization
```

### Implementation Steps

#### Step 1: Analyze Profiling Data
1. Run all benchmarks from PR1
2. Generate flamegraphs for each critical path
3. Identify top 5 bottlenecks by time spent
4. Document findings in optimization plan
5. Prioritize optimizations by user impact

#### Step 2: Optimize Command Path Latency
Target: < 10ms overhead over native command

Potential optimizations:
1. **IPC Optimization**:
   - Use faster serialization (bincode instead of JSON if applicable)
   - Reduce syscall overhead
   - Implement connection pooling if multiple connections

2. **Shim Optimization**:
   - Minimize allocations in hot path
   - Cache daemon connection
   - Fast path for allowed commands
   - Lazy initialization of non-critical components

3. **Daemon Response Optimization**:
   - Pre-serialize common responses
   - Async response handling
   - Reduce lock contention

#### Step 3: Optimize Rule Evaluation
Target: < 1ms per command

Potential optimizations:
1. **Rule Matching**:
   - Build rule index for O(1) lookup where possible
   - Short-circuit evaluation for common cases
   - Cache regex compilation
   - Use Aho-Corasick for multiple pattern matching

2. **Context Evaluation**:
   - Cache context determination (ai_only/human_only)
   - Lazy context loading
   - Optimize context detection logic

3. **Rule Storage**:
   - Use efficient data structures (HashMap, BTreeMap)
   - Pre-process rules at load time
   - Implement rule priority ordering

#### Step 4: Optimize Daemon Startup
Target: < 100ms

Potential optimizations:
1. **Lazy Initialization**:
   - Defer non-critical initialization
   - Load rules asynchronously
   - Delay monitor connection setup

2. **Configuration Loading**:
   - Use faster TOML parser
   - Cache parsed configuration
   - Reduce file I/O

3. **Binary Size**:
   - Strip unused features
   - Optimize release profile
   - Consider link-time optimization (LTO)

#### Step 5: Optimize Monitor TUI
Target: < 16ms frame time (60fps)

Potential optimizations:
1. **Rendering**:
   - Only redraw changed regions
   - Implement virtual scrolling for large logs
   - Cache rendered lines
   - Limit render rate to 60fps

2. **Event Handling**:
   - Batch event processing
   - Debounce rapid events
   - Async event handling

3. **Data Management**:
   - Implement log rotation
   - Use circular buffer for log storage
   - Limit in-memory log entries

#### Step 6: Memory Optimization
Target: < 50MB resident

1. Identify memory-heavy operations
2. Reduce allocations in hot paths
3. Implement memory pooling where beneficial
4. Profile memory usage with valgrind/heaptrack

#### Step 7: Validate Optimizations
1. Run full benchmark suite after each optimization
2. Compare against baseline from PR1
3. Document performance improvements
4. Ensure no functionality regressions
5. Run full test suite

### Testing Requirements
- All benchmarks show improvement
- Full test suite passes (no regressions)
- Integration tests pass
- Manual testing of critical paths
- Performance regression tests added

### Success Criteria
- [ ] All performance targets met or exceeded
- [ ] Benchmarks show measurable improvements
- [ ] No functionality regressions
- [ ] All tests pass
- [ ] Performance improvements documented with metrics

### Documentation Requirements
- Document each optimization technique used
- Before/after benchmark comparisons
- Update benchmarks/README.md with new baselines
- Add code comments explaining performance-critical sections

---

## PR3: Performance Documentation and Regression Tests

**Branch**: `feature/phase6-performance-docs`
**Estimated Effort**: 1-2 days
**Complexity**: Medium
**Priority**: P0
**Blocked By**: PR2

### Objectives
Document performance characteristics comprehensively, implement performance regression testing, and establish ongoing performance monitoring to maintain optimization gains.

### What This PR Does
- Documents performance characteristics for all critical paths
- Creates performance regression test suite
- Documents performance tuning options
- Creates performance troubleshooting guide
- Adds performance section to main README
- Sets up CI performance monitoring (optional)

### Files to Create
```
docs/performance/
├── README.md                       # Performance overview
├── CHARACTERISTICS.md              # Detailed performance characteristics
├── TUNING.md                       # Performance tuning guide
├── TROUBLESHOOTING.md              # Performance troubleshooting
└── REGRESSION_TESTS.md             # Regression test documentation

tests/performance/
├── regression_suite.rs             # Performance regression tests
└── helpers.rs                      # Test utilities
```

### Files to Modify
```
README.md                           # Add performance section
.github/workflows/ci.yml            # Add performance regression tests
Cargo.toml                          # Add performance test configuration
docs/ARCHITECTURE.md                # Add performance considerations
```

### Implementation Steps

#### Step 1: Document Performance Characteristics
Create docs/performance/CHARACTERISTICS.md with:

1. **Command Path Performance**:
   - Baseline: Native command latency
   - SafeShell overhead: < 10ms
   - Breakdown by component:
     - Shim interception: X ms
     - IPC to daemon: X ms
     - Rule evaluation: X ms
     - Response time: X ms
   - Performance under load (concurrent commands)

2. **Rule Evaluation Performance**:
   - Single rule: < 1ms
   - Full ruleset (100 rules): X ms
   - Cache hit rate: X%
   - Performance by rule type

3. **Daemon Performance**:
   - Startup time: < 100ms
   - Memory usage: < 50MB
   - CPU usage: < 1% idle
   - IPC throughput: X requests/sec

4. **Monitor TUI Performance**:
   - Frame time: < 16ms (60fps)
   - Log capacity: 10,000 entries
   - Filter latency: < 50ms
   - Memory per entry: X bytes

#### Step 2: Create Performance Regression Tests
Create tests/performance/regression_suite.rs:

```rust
// Example test structure
#[test]
fn test_command_latency_regression() {
    // Setup test environment
    // Run command through SafeShell
    // Measure latency
    // Assert latency < threshold (baseline * 1.1)
    assert!(measured_latency < MAX_ACCEPTABLE_LATENCY);
}

#[test]
fn test_rule_evaluation_regression() {
    // Test rule evaluation stays under threshold
}

#[test]
fn test_daemon_startup_regression() {
    // Test daemon startup time
}

#[test]
fn test_memory_usage_regression() {
    // Test memory footprint
}
```

Regression tests should:
- Run quickly (< 10s total)
- Be deterministic
- Allow 10% variance from baseline
- Fail CI if performance degrades significantly
- Be skippable with env var for resource-constrained CI

#### Step 3: Create Performance Tuning Guide
Create docs/performance/TUNING.md with:

1. **Configuration Options**:
   - Rule cache size tuning
   - Log buffer size tuning
   - IPC timeout tuning
   - Daemon thread pool size

2. **Environment-Specific Tuning**:
   - High-load environments
   - Low-resource environments
   - Network-mounted home directories
   - Containerized environments

3. **Profiling Your Setup**:
   - How to run benchmarks
   - How to identify bottlenecks
   - When to file performance bugs

#### Step 4: Create Troubleshooting Guide
Create docs/performance/TROUBLESHOOTING.md with:

1. **Common Performance Issues**:
   - Slow command execution
     - Symptoms
     - Diagnosis steps
     - Solutions
   - High CPU usage
   - High memory usage
   - Monitor TUI lag

2. **Diagnostic Tools**:
   - Built-in profiling commands
   - External profiling tools
   - Log analysis

3. **Performance Checklist**:
   - Quick checks for performance issues
   - System requirements verification
   - Configuration validation

#### Step 5: Update Main Documentation
1. Add performance section to README.md:
   - Performance characteristics summary
   - Link to detailed docs
   - Known limitations

2. Update docs/ARCHITECTURE.md:
   - Add performance considerations section
   - Document performance-critical code paths
   - Explain optimization decisions

3. Add performance badges (optional):
   - Command overhead badge
   - Build time badge
   - Binary size badge

#### Step 6: CI Integration (Optional)
1. Add performance regression tests to CI:
```yaml
- name: Performance Regression Tests
  run: cargo test --test regression_suite --release
  env:
    SKIP_PERF_TESTS: ${{ github.event_name == 'pull_request' }}
```

2. Add benchmark comparison action:
   - Compare PR benchmarks against main
   - Comment on PR with performance changes
   - Fail if significant regressions detected

3. Track performance over time:
   - Store benchmark results
   - Generate performance trend graphs
   - Alert on degradation

#### Step 7: Final Validation
1. Review all documentation for accuracy
2. Verify regression tests catch known regressions
3. Test documentation instructions
4. Ensure all performance targets documented
5. Update CHANGELOG.md with performance improvements

### Testing Requirements
- Regression tests pass consistently
- Regression tests fail when performance degrades (validation)
- Documentation accurate and complete
- All links work
- Code examples in docs functional

### Success Criteria
- [ ] Comprehensive performance documentation
- [ ] Regression tests prevent performance degradation
- [ ] Clear troubleshooting guidance
- [ ] CI integration functional (if implemented)
- [ ] Main README updated with performance info
- [ ] All performance targets documented and validated

### Documentation Requirements
- Complete docs/performance/ directory
- Updated README.md with performance section
- Clear, actionable troubleshooting steps
- Benchmark comparison guidelines
- Performance tuning recommendations

---

---

## PR4: Structured Condition Schema

**Branch**: `feature/phase7-structured-conditions`
**Estimated Effort**: 2-3 days
**Complexity**: High
**Priority**: P0 (HIGHEST)

### Objectives
Replace bash condition strings with structured, Python-evaluatable conditions in the rule schema. This is the foundational change that enables PR5 and PR6.

### What This PR Does
- Defines Pydantic models for each condition type
- Updates Rule schema to accept structured conditions
- Maintains backward compatibility with bash strings (temporarily)
- Updates schema validation

### Files to Create
```
src/safeshell/rules/condition_types.py    # Pydantic models for conditions
```

### Files to Modify
```
src/safeshell/rules/schema.py             # Update Rule.conditions type
tests/rules/test_schema.py                # Tests for new condition types
```

### Implementation Steps

#### Step 1: Define Condition Type Models
Create Pydantic models for each condition type:

```python
# src/safeshell/rules/condition_types.py
from pydantic import BaseModel, Field
from typing import Literal

class CommandMatches(BaseModel):
    """Match command against regex pattern."""
    type: Literal["command_matches"] = "command_matches"
    pattern: str = Field(..., description="Regex pattern to match against full command")

class CommandContains(BaseModel):
    """Check if command contains literal substring."""
    type: Literal["command_contains"] = "command_contains"
    substring: str = Field(..., description="Literal string to search for")

class CommandStartswith(BaseModel):
    """Check if command starts with prefix."""
    type: Literal["command_startswith"] = "command_startswith"
    prefix: str = Field(..., description="Prefix to match")

class GitBranchIn(BaseModel):
    """Check if current git branch is in list."""
    type: Literal["git_branch_in"] = "git_branch_in"
    branches: list[str] = Field(..., description="List of branch names")

class GitBranchMatches(BaseModel):
    """Match git branch against regex pattern."""
    type: Literal["git_branch_matches"] = "git_branch_matches"
    pattern: str = Field(..., description="Regex pattern for branch name")

class InGitRepo(BaseModel):
    """Check if working directory is in a git repo."""
    type: Literal["in_git_repo"] = "in_git_repo"
    value: bool = Field(True, description="Expected value")

class PathMatches(BaseModel):
    """Match working directory against regex pattern."""
    type: Literal["path_matches"] = "path_matches"
    pattern: str = Field(..., description="Regex pattern for working directory")

class FileExists(BaseModel):
    """Check if file exists in working directory."""
    type: Literal["file_exists"] = "file_exists"
    path: str = Field(..., description="Relative path to check")

class EnvEquals(BaseModel):
    """Check environment variable value."""
    type: Literal["env_equals"] = "env_equals"
    variable: str = Field(..., description="Environment variable name")
    value: str = Field(..., description="Expected value")

# Union type for all conditions
StructuredCondition = (
    CommandMatches | CommandContains | CommandStartswith |
    GitBranchIn | GitBranchMatches | InGitRepo |
    PathMatches | FileExists | EnvEquals
)

# Allow both old (string) and new (structured) formats
Condition = str | StructuredCondition
```

#### Step 2: Update Rule Schema
```python
# In schema.py
from safeshell.rules.condition_types import Condition

class Rule(BaseModel):
    # ... existing fields ...
    conditions: list[Condition] = Field(default_factory=list)
```

#### Step 3: Add Schema Tests
Test that both formats are accepted:
```python
def test_structured_condition_command_matches():
    rule = Rule(
        name="test",
        commands=["git"],
        conditions=[{"type": "command_matches", "pattern": "^git\\s+commit"}],
        action=RuleAction.DENY,
    )
    assert len(rule.conditions) == 1

def test_legacy_bash_condition():
    rule = Rule(
        name="test",
        commands=["git"],
        conditions=['echo "$CMD" | grep -q "commit"'],
        action=RuleAction.DENY,
    )
    assert len(rule.conditions) == 1
```

### Testing Requirements
- All existing tests pass (backward compatibility)
- New tests for each condition type
- Schema validation tests
- YAML parsing tests

### Success Criteria
- [ ] All condition types defined as Pydantic models
- [ ] Rule schema accepts both string and structured conditions
- [ ] Schema validation works correctly
- [ ] All tests pass

---

## PR5: Condition Evaluators

**Branch**: `feature/phase7-condition-evaluators`
**Estimated Effort**: 2-3 days
**Complexity**: Medium
**Priority**: P0
**Blocked By**: PR4

### Objectives
Implement Python evaluators for all structured condition types. Update the rule evaluator to use these instead of bash subprocess calls.

### What This PR Does
- Implements evaluator class for each condition type
- Updates `_check_condition()` to use structured evaluators
- Pre-compiles regex patterns at rule load time
- Eliminates bash subprocess calls for structured conditions

### Files to Modify
```
src/safeshell/rules/conditions.py         # Evaluator implementations
src/safeshell/rules/evaluator.py          # Use new evaluators
tests/rules/test_conditions.py            # Tests for evaluators
```

### Implementation Steps

#### Step 1: Create Evaluator Protocol
```python
from typing import Protocol

class ConditionEvaluator(Protocol):
    def evaluate(self, context: CommandContext) -> bool: ...
```

#### Step 2: Implement Evaluators
```python
class CommandMatchesEvaluator:
    def __init__(self, condition: CommandMatches):
        self._pattern = re.compile(condition.pattern)

    def evaluate(self, context: CommandContext) -> bool:
        return self._pattern.search(context.raw_command) is not None

class GitBranchInEvaluator:
    def __init__(self, condition: GitBranchIn):
        self._branches = frozenset(condition.branches)

    def evaluate(self, context: CommandContext) -> bool:
        return context.git_branch in self._branches

# ... etc for each condition type
```

#### Step 3: Create Evaluator Factory
```python
def create_evaluator(condition: Condition) -> ConditionEvaluator:
    """Create evaluator for a condition."""
    if isinstance(condition, str):
        # Legacy bash condition - use bash evaluator or auto-translate
        return BashConditionEvaluator(condition)
    elif isinstance(condition, CommandMatches):
        return CommandMatchesEvaluator(condition)
    elif isinstance(condition, GitBranchIn):
        return GitBranchInEvaluator(condition)
    # ... etc
```

#### Step 4: Update RuleEvaluator
Pre-compile evaluators at init time:
```python
class RuleEvaluator:
    def __init__(self, rules: list[Rule], ...):
        # Pre-compile condition evaluators for each rule
        self._rule_evaluators: dict[str, list[ConditionEvaluator]] = {}
        for rule in rules:
            self._rule_evaluators[rule.name] = [
                create_evaluator(cond) for cond in rule.conditions
            ]
```

#### Step 5: Update `_check_condition()`
```python
async def _check_condition(self, evaluator: ConditionEvaluator, context: CommandContext) -> bool:
    # Direct Python evaluation - no subprocess
    return evaluator.evaluate(context)
```

### Testing Requirements
- Unit tests for each evaluator
- Integration tests with RuleEvaluator
- Performance tests (verify <0.1ms per condition)
- Backward compatibility tests for bash conditions

### Success Criteria
- [ ] All condition types have working evaluators
- [ ] Pre-compilation at rule load time
- [ ] No subprocess calls for structured conditions
- [ ] <0.1ms per condition evaluation
- [ ] All tests pass

---

## PR6: Deprecate Bash Conditions

**Branch**: `feature/phase7-deprecate-bash`
**Estimated Effort**: 1-2 days
**Complexity**: Low
**Priority**: P1
**Blocked By**: PR5

### Objectives
Provide migration path for users with bash conditions. Add deprecation warnings and migration tooling.

### What This PR Does
- Adds deprecation warning when bash conditions are loaded
- Creates `safeshell migrate-rules` CLI command
- Updates default rules to structured format
- Updates documentation

### Files to Create
```
src/safeshell/cli/migrate.py              # Migration CLI command
```

### Files to Modify
```
src/safeshell/rules/loader.py             # Add deprecation warning
src/safeshell/rules/defaults.py           # Update to structured format
src/safeshell/cli/__init__.py             # Register migrate command
docs/rules.md                             # Update documentation
```

### Implementation Steps

#### Step 1: Add Deprecation Warning
```python
# In loader.py
def load_rules(path: Path) -> list[Rule]:
    rules = _parse_yaml(path)
    for rule in rules:
        for condition in rule.conditions:
            if isinstance(condition, str):
                logger.warning(
                    f"Rule '{rule.name}' uses deprecated bash condition. "
                    f"Run 'safeshell migrate-rules' to convert to structured format."
                )
    return rules
```

#### Step 2: Create Migration Command
```python
# src/safeshell/cli/migrate.py
def migrate_rules(input_path: Path, output_path: Path | None = None):
    """Convert bash conditions to structured format."""
    rules = load_rules(input_path)
    migrated = []
    for rule in rules:
        new_conditions = []
        for cond in rule.conditions:
            if isinstance(cond, str):
                structured = convert_bash_to_structured(cond)
                if structured:
                    new_conditions.append(structured)
                else:
                    # Can't convert - keep as-is with warning
                    logger.warning(f"Cannot auto-convert: {cond}")
                    new_conditions.append(cond)
            else:
                new_conditions.append(cond)
        rule.conditions = new_conditions
        migrated.append(rule)
    # Write output
    ...
```

#### Step 3: Update Default Rules
```python
# defaults.py - BEFORE:
Rule(
    name="block-commit-protected-branch",
    commands=["git"],
    conditions=[
        'echo "$CMD" | grep -qE "^git\\s+commit"',
        'git branch --show-current | grep -qE "^(main|master|develop)$"',
    ],
    ...
)

# defaults.py - AFTER:
Rule(
    name="block-commit-protected-branch",
    commands=["git"],
    conditions=[
        CommandMatches(pattern=r"^git\s+commit"),
        GitBranchIn(branches=["main", "master", "develop"]),
    ],
    ...
)
```

### Testing Requirements
- Migration command tests
- Deprecation warning tests
- Default rules load correctly

### Success Criteria
- [ ] Deprecation warning shown for bash conditions
- [ ] Migration command works correctly
- [ ] Default rules use structured format
- [ ] Documentation updated

---

## Implementation Guidelines

### Code Standards
- Follow existing Python code style (ruff)
- Add performance-critical comments where optimizations applied
- Use type hints throughout
- Profile before and after optimizations
- Keep code maintainable - clarity over micro-optimizations

### Testing Requirements
- All optimizations must have benchmark validation
- No functionality regressions allowed
- Full test suite must pass after each PR
- Performance regression tests for critical paths
- Integration tests for optimized components

### Documentation Standards
- Document all performance characteristics with metrics
- Explain optimization techniques used
- Include before/after comparisons
- Update relevant documentation (README, ARCHITECTURE)
- Use atemporal language (no "will", "going to")

### Security Considerations
- Optimizations must not compromise security
- No shortcuts in approval/denial logic
- Maintain full audit trail
- Rule evaluation must remain accurate
- No security-relevant timing differences

### Performance Targets
- **Command latency**: < 10ms overhead
- **Rule evaluation**: < 1ms per command
- **Daemon startup**: < 100ms
- **Monitor TUI**: < 16ms frame time (60fps)
- **Memory usage**: < 50MB resident
- **Binary size**: < 10MB stripped release

## Rollout Strategy

### Phase 1: PR1 - Caching (Complete)
- Caching infrastructure merged
- Incremental improvement
- Risk: Low

### Phase 2: PR2 - Auto-Translation (Partial)
- Auto-translation of bash conditions
- Limited success - superseded by PR4-6
- Risk: Low

### Phase 3: PR4 - Structured Schema (Priority)
- Define structured condition types
- Update rule schema
- Backward compatible
- Risk: Medium (schema changes)

### Phase 4: PR5 - Evaluators
- Implement Python evaluators
- Eliminate subprocess calls
- Risk: Medium

### Phase 5: PR6 - Migration
- Deprecation warnings
- Migration tooling
- Update defaults
- Risk: Low

### Phase 6: PR3 - Profiling (Deferred)
- Profiling infrastructure
- Validate performance gains
- Risk: Low

## Success Metrics

### Launch Metrics
- All 6 PRs merged successfully
- Performance targets met (<0.1ms per condition)
- Zero subprocess calls for structured conditions
- Migration path documented
- Backward compatibility maintained

### Ongoing Metrics
- Performance regression test pass rate: 100%
- Benchmark stability (low variance between runs)
- No performance-related bug reports
- Bash condition usage declining (migration working)
- CI catches performance regressions before merge

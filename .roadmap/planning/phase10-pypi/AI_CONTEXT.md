# Phase 9: PyPI Distribution - AI Context

**Purpose**: AI agent context document for implementing PyPI distribution for safeshell

**Scope**: Complete PyPI publishing setup from metadata configuration through automated releases

**Overview**: Comprehensive context document for AI agents working on the Phase 9: PyPI Distribution feature.
    This phase enables safeshell to be distributed via PyPI (Python Package Index) with proper metadata,
    automated publishing workflows using PyPI Trusted Publishing (OIDC), and professional release management
    with changelog extraction. Enables users to install safeshell via `pip install safeshell` and ensures
    a professional, automated release process.

**Dependencies**: Poetry (build/publish), GitHub Actions (CI/CD), PyPI account, Trusted Publishing setup

**Exports**: PyPI package metadata, publish workflow, changelog format, release documentation

**Related**: PR_BREAKDOWN.md for implementation tasks, PROGRESS_TRACKER.md for current status

**Implementation**: Three-phase approach: metadata → workflow → documentation, following thai-lint reference implementation

---

## Overview

Phase 9 focuses on establishing a professional PyPI distribution pipeline for safeshell. This enables
the package to be installed via standard Python tools (`pip install safeshell`) and provides automated
publishing triggered by version tags. The implementation follows the proven patterns from the thai-lint
project, adapted to safeshell's specific needs.

## Project Background

**Current State:**
- safeshell is a command-line safety layer for AI coding assistants
- Uses Poetry for dependency management (pyproject.toml)
- Has CLI entry points: `safeshell` and `safeshell-wrapper`
- Package structure: `src/safeshell/` with modules for CLI, wrapper, rules, models
- Version: 0.1.0 (initial development version)
- No public distribution mechanism currently exists

**Gap:**
- No PyPI metadata for package discovery and classification
- No automated publishing workflow
- No changelog for tracking version history
- No release documentation or processes

**Goal:**
Enable professional PyPI distribution with:
- Rich package metadata for discoverability
- Automated, secure publishing via OIDC
- Professional changelog following Keep a Changelog format
- Clear release process documentation

## Feature Vision

1. **Discoverable Package**: Complete PyPI metadata enables users to find safeshell via search
   - Keywords: shell, safety, ai, command-line, security, wrapper
   - Classifiers: Development Status, Intended Audience, License, Python versions
   - URLs: Homepage, repository, documentation, issue tracker
   - Professional description and README

2. **Automated Publishing**: Triggered on version tags (v*.*.*)
   - Full test suite validation before publish
   - PyPI Trusted Publishing (OIDC) for secure, tokenless authentication
   - Build verification and artifact inspection
   - Automatic GitHub Release creation with changelog

3. **Professional Release Management**: Clear processes and documentation
   - CHANGELOG.md following Keep a Changelog format
   - Version bump workflow documentation
   - Pre-release checklist
   - TestPyPI validation before production

4. **User-Friendly Installation**: Standard Python tooling
   - `pip install safeshell` (production)
   - `pip install --upgrade safeshell` (upgrades)
   - Version pinning support for reproducible installs

## Current Application Context

**Package Structure:**
```
safeshell/
├── src/safeshell/          # Main package
│   ├── cli.py              # Typer CLI with rich output
│   ├── wrapper/            # Shell wrapper and command filtering
│   ├── rules/              # Rule engine and validators
│   └── models/             # Pydantic data models
├── pyproject.toml          # Poetry config (needs PyPI metadata)
├── README.md               # Package readme (included in distribution)
└── tests/                  # Test suite (excluded from distribution)
```

**Dependencies:**
- Runtime: typer, rich, pydantic, loguru, pyyaml, plumbum, textual
- Dev: pytest, ruff, pylint, mypy, bandit, thailint, radon

**Current pyproject.toml Metadata:**
- Basic: name, version, description, authors, readme
- CLI scripts: safeshell, safeshell-wrapper
- Missing: keywords, classifiers, URLs, license, package includes/excludes

## Target Architecture

### Core Components

**1. PyPI Metadata (pyproject.toml)**
```yaml
[tool.poetry]
name = "safeshell"
version = "0.1.0"
description = "A command-line safety layer for AI coding assistants"
authors = ["Steve Jackson"]
license = "MIT"  # NEW
readme = "README.md"
homepage = "https://github.com/be-wise-be-kind/safeshell"  # NEW
repository = "https://github.com/be-wise-be-kind/safeshell"  # NEW
documentation = "https://safeshell.readthedocs.io/"  # NEW (or GitHub README)
keywords = [  # NEW
    "shell", "safety", "ai", "command-line", "security",
    "wrapper", "cli", "governance", "python"
]
classifiers = [  # NEW
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Topic :: Software Development :: Quality Assurance",
    "Topic :: System :: Shells",
    "Environment :: Console",
]
packages = [{include = "safeshell", from = "src"}]
include = [  # NEW
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
]
exclude = [  # NEW
    "tests",
    ".github",
    ".ai",
    "docs",
    "examples",
]
```

**2. Publish Workflow (.github/workflows/publish-pypi.yml)**
```yaml
name: Publish to PyPI
on:
  push:
    tags: ['v*.*.*']

permissions:
  contents: write  # GitHub releases
  id-token: write  # PyPI OIDC

jobs:
  test:           # Full quality gate
  build:          # Poetry build + verification
  publish-pypi:   # PyPI OIDC publish
  create-release: # GitHub release with changelog
```

**3. CHANGELOG.md (Keep a Changelog format)**
```markdown
# Changelog

## [Unreleased]
### Added
- New features

## [0.1.0] - 2025-12-09
### Added
- Initial release
```

**4. Release Documentation (docs/releasing.md)**
- Version bump process
- TestPyPI validation steps
- Publishing checklist
- Troubleshooting guide

### User Journey

**Installation Journey:**
1. User discovers safeshell on PyPI or GitHub
2. Runs `pip install safeshell`
3. Poetry builds isolated venv, installs dependencies
4. CLI commands available: `safeshell`, `safeshell-wrapper`
5. User can verify version: `safeshell --version`

**Developer Release Journey:**
1. Developer completes feature work on branch
2. Updates CHANGELOG.md with changes
3. Bumps version in pyproject.toml
4. Commits changes, creates PR, merges to main
5. Creates version tag: `git tag v0.2.0 && git push origin v0.2.0`
6. GitHub Actions triggers publish workflow
7. Tests run (quality gate)
8. Package builds and publishes to PyPI
9. GitHub Release created with changelog
10. Users can install new version: `pip install --upgrade safeshell`

**Publish Workflow Stages:**
1. **Test Stage**: Run full test suite, linting, type checking
   - Ensures only validated code is published
   - Blocks publish on test failures
2. **Build Stage**: Poetry build, verify package contents
   - Creates wheel and source distribution
   - Inspects contents for correctness
3. **Publish Stage**: PyPI OIDC publish
   - Tokenless authentication via Trusted Publishing
   - Publishes to https://pypi.org/project/safeshell/
4. **Release Stage**: GitHub Release creation
   - Extracts changelog for version
   - Attaches build artifacts
   - Creates release with notes

### PyPI Trusted Publishing (OIDC)

**Configuration Required:**
1. Go to https://pypi.org/manage/account/publishing/
2. Add new publisher:
   - PyPI Project Name: `safeshell`
   - Owner: `be-wise-be-kind`
   - Repository: `safeshell`
   - Workflow name: `publish-pypi.yml`
   - Environment: `pypi`

**Benefits:**
- No API tokens to manage or rotate
- No secrets to store in GitHub
- Automatic authentication via OIDC
- More secure than token-based auth

## Key Decisions Made

### 1. PyPI Metadata Strategy

**Decision**: Use comprehensive metadata following thai-lint patterns

**Rationale:**
- Keywords improve discoverability via PyPI search
- Classifiers help users filter packages by status, audience, topic
- URLs provide clear navigation to docs, issues, source
- Professional metadata signals quality and maintainability

**Implementation:**
- Add keywords focusing on shell safety, AI, command-line
- Use "Alpha" development status (honest about maturity)
- Include LICENSE file in distribution
- Exclude test/development files from distribution

### 2. Publishing Workflow Design

**Decision**: Multi-stage workflow with quality gate and OIDC

**Rationale:**
- Quality gate (test stage) prevents publishing broken code
- Build verification catches packaging issues early
- OIDC eliminates token management and improves security
- GitHub Release automation provides professional release notes

**Implementation:**
- Four jobs: test → build → publish-pypi → create-release
- Sequential execution with needs dependencies
- OIDC authentication (no tokens)
- Changelog extraction for release notes

### 3. Changelog Format

**Decision**: Keep a Changelog 1.1.0 format with semantic versioning

**Rationale:**
- Industry standard format, human-readable
- Clear categories: Added, Changed, Fixed, etc.
- Supports automated extraction for releases
- Follows semver for version numbering

**Implementation:**
- CHANGELOG.md in project root
- Included in package distribution
- Extracted by workflow for GitHub releases
- Manual maintenance (not auto-generated)

### 4. Release Process

**Decision**: Tag-triggered automated publishing

**Rationale:**
- Git tags are immutable and traceable
- v*.*.* pattern clearly indicates release versions
- Automated workflow reduces human error
- TestPyPI validation before production

**Implementation:**
- Developer creates version tag: `git tag v0.2.0`
- Push tag triggers workflow: `git push origin v0.2.0`
- Workflow handles all publish steps
- Documentation covers manual validation steps

## Integration Points

### With Existing Features

**1. Poetry Build System**
- Uses existing `[build-system]` and `[tool.poetry]` sections
- Adds metadata fields to existing configuration
- No changes to package structure or scripts
- Compatible with current Poetry workflow

**2. GitHub Actions CI**
- New workflow file: `.github/workflows/publish-pypi.yml`
- Reuses existing test/lint infrastructure
- Integrates with existing permissions model
- Follows patterns from test.yml workflow

**3. Documentation**
- CHANGELOG.md provides user-facing version history
- docs/releasing.md guides maintainer workflow
- README.md updated to mention PyPI availability
- Supports existing .ai/ documentation structure

### With PyPI Ecosystem

**1. Package Index**
- Project page: https://pypi.org/project/safeshell/
- Search/discovery via keywords and classifiers
- Version history and release notes
- Download statistics tracking

**2. Installation Tools**
- pip: `pip install safeshell`
- poetry: `poetry add safeshell`
- pipx: `pipx install safeshell` (recommended for CLI tools)
- requirements.txt: `safeshell==0.1.0`

**3. Trusted Publishing**
- OIDC authentication with PyPI
- GitHub Actions integration
- No token management required
- Environment-based deployment protection

## Success Metrics

### Technical Metrics
- Package successfully published to PyPI
- Workflow completes in <5 minutes
- All tests pass before publish (100% success rate)
- Zero manual token management
- Build artifacts include expected files

### Feature Metrics
- Users can install via `pip install safeshell`
- Package appears in PyPI search results
- GitHub releases created automatically with changelog
- Clear upgrade path: `pip install --upgrade safeshell`
- TestPyPI validation successful before production

### Quality Metrics
- No publish failures due to missing metadata
- No security issues with token management
- CHANGELOG.md kept up to date
- Release documentation clear and accurate

## Technical Constraints

### PyPI Requirements
- Unique package name (safeshell available)
- Valid semver versions (e.g., 0.1.0, 1.2.3)
- Complete package metadata (name, version, author, etc.)
- Trusted Publishing configured at pypi.org
- Source distribution and wheel builds

### GitHub Actions Requirements
- Workflow triggered on version tags (v*.*.*)
- Permissions: contents:write, id-token:write
- Environment: pypi (for Trusted Publishing)
- Artifacts uploaded for GitHub releases
- Changelog extraction logic

### Poetry Requirements
- Valid pyproject.toml with [tool.poetry] section
- Build backend: poetry-core
- Package structure matches packages config
- Include/exclude patterns for distribution

## AI Agent Guidance

### When implementing PR1 (PyPI Metadata)

1. Read current pyproject.toml to understand structure
2. Reference thai-lint pyproject.toml for metadata examples
3. Add fields: license, homepage, repository, documentation, keywords, classifiers
4. Configure includes/excludes for distribution
5. Verify package structure matches includes
6. Test locally: `poetry build` and inspect dist/ contents
7. Update README.md to mention PyPI availability

### When implementing PR2 (Publish Workflow)

1. Read thai-lint publish-pypi.yml workflow
2. Adapt to safeshell specifics:
   - Update URLs from thailint to safeshell
   - Adjust test commands if needed
   - Keep workflow structure and jobs
3. Create workflow file: `.github/workflows/publish-pypi.yml`
4. Add OIDC environment: pypi
5. Document Trusted Publishing setup steps
6. Test workflow logic (without actual publish)

### When implementing PR3 (Changelog and Docs)

1. Read thai-lint CHANGELOG.md for format reference
2. Create CHANGELOG.md with Keep a Changelog format
3. Add version 0.1.0 section documenting existing features
4. Create [Unreleased] section for future changes
5. Write docs/releasing.md covering:
   - Version bump process
   - TestPyPI validation
   - Tag creation and push
   - Troubleshooting common issues
6. Update README.md with installation instructions

### Common Patterns

**Metadata Pattern:**
```toml
[tool.poetry]
# Basic fields (existing)
name = "package-name"
version = "0.1.0"

# Distribution metadata (add)
license = "MIT"
homepage = "https://github.com/..."
repository = "https://github.com/..."
keywords = ["key1", "key2"]
classifiers = ["Classifier :: Value"]

# Package control (add)
include = ["README.md", "LICENSE", "CHANGELOG.md"]
exclude = ["tests", ".github", ".ai"]
```

**Workflow Job Pattern:**
```yaml
job-name:
  name: Human-Readable Name
  needs: previous-job  # Sequential execution
  runs-on: ubuntu-latest
  steps:
    - name: Checkout code
      uses: actions/checkout@v4
    - name: Setup Python
      uses: actions/setup-python@v5
    - name: Install Poetry
      run: |
        curl -sSL https://install.python-poetry.org | python3 -
    - name: Do work
      run: poetry run command
```

**Changelog Pattern:**
```markdown
## [Version] - YYYY-MM-DD
### Added
- New feature descriptions
### Changed
- Modification descriptions
### Fixed
- Bug fix descriptions
```

## Risk Mitigation

### Risk: Publishing Broken Package
**Mitigation:**
- Full test suite runs before publish (quality gate)
- Build verification inspects package contents
- TestPyPI validation before production release
- Can yank/delete bad releases from PyPI if needed

### Risk: Token Security Issues
**Mitigation:**
- Use PyPI Trusted Publishing (OIDC) - no tokens
- No secrets stored in GitHub repository
- OIDC tied to specific workflow and environment
- Automatic authentication via GitHub Actions

### Risk: Missing or Incorrect Metadata
**Mitigation:**
- Reference thai-lint as proven example
- Test package build locally before PR
- Verify dist/ contents include expected files
- Use Poetry validation: `poetry check`

### Risk: Changelog Maintenance
**Mitigation:**
- Document process in releasing.md
- Include CHANGELOG.md in PR checklists
- Automated extraction for GitHub releases
- Keep a Changelog format is simple and clear

### Risk: Version Tag Errors
**Mitigation:**
- Document tag format: v*.*.* (e.g., v0.1.0)
- Workflow only triggers on matching tags
- Can delete tags if created incorrectly
- TestPyPI practice before production

## Future Enhancements

### Post-Phase 9 Improvements

1. **Automated Version Bumping**
   - GitHub Action to bump version on merge
   - Automated changelog updates from PR labels
   - Release notes generation from commits

2. **Documentation Hosting**
   - ReadTheDocs or GitHub Pages setup
   - API documentation with Sphinx
   - User guides and tutorials
   - Link from PyPI package page

3. **Package Badges**
   - PyPI version badge
   - Download statistics
   - Test coverage badge
   - Quality gate status

4. **Distribution Channels**
   - Conda-forge package
   - Homebrew formula (macOS)
   - APT/YUM packages (Linux)
   - Snap/Flatpak packages

5. **Release Automation**
   - Release drafter for GitHub releases
   - Automated CHANGELOG.md updates
   - Semantic release integration
   - PR labeling for change categorization

### Package Improvements

1. **Installation Verification**
   - Post-install checks
   - Smoke tests for CLI commands
   - Configuration validation
   - Helpful setup wizard

2. **Upgrade Path**
   - Migration scripts for config changes
   - Deprecation warnings
   - Breaking change documentation
   - Compatibility matrix

3. **Analytics**
   - Download statistics tracking
   - User feedback collection
   - Error telemetry (opt-in)
   - Usage patterns analysis

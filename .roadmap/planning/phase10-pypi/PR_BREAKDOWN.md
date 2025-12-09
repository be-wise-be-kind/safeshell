# Phase 9: PyPI Distribution - PR Breakdown

**Purpose**: Detailed implementation breakdown of Phase 9: PyPI Distribution into manageable, atomic pull requests

**Scope**: Complete PyPI publishing setup from metadata configuration through automated releases and documentation

**Overview**: Comprehensive breakdown of the PyPI Distribution phase into 3 manageable, atomic
    pull requests. Each PR is designed to be self-contained, testable, and maintains application functionality
    while incrementally building toward complete PyPI distribution capability. Follows proven patterns from
    thai-lint project with adaptations for safeshell specifics.

**Dependencies**: Poetry (build/publish), GitHub Actions (CI/CD), PyPI account with Trusted Publishing

**Exports**: PR implementation plans, file structures, testing strategies, and success criteria for each development phase

**Related**: AI_CONTEXT.md for feature overview, PROGRESS_TRACKER.md for status tracking

**Implementation**: Atomic PR approach with detailed step-by-step implementation guidance and comprehensive validation

---

## Overview
This document breaks down the Phase 9: PyPI Distribution feature into 3 manageable, atomic PRs. Each PR is designed to be:
- Self-contained and testable
- Maintains a working application
- Incrementally builds toward the complete feature
- Revertible if needed

**Implementation Order**: PR1 (Metadata) → PR2 (Workflow) → PR3 (Documentation)

---

## PR1: PyPI Package Metadata

### Goal
Configure complete PyPI metadata in pyproject.toml to enable professional package distribution with proper classification, URLs, and file inclusion/exclusion.

### Motivation
PyPI metadata enables package discoverability, provides users with helpful information, and ensures the correct files are included/excluded from the distribution. This is the foundation for PyPI publishing.

### Scope
- Add PyPI metadata fields to pyproject.toml
- Configure package includes/excludes
- Create LICENSE file if missing
- Update README.md with installation instructions
- Test package build locally

### Files Changed
```
pyproject.toml          # Add metadata fields
LICENSE                 # Create if missing (MIT license)
README.md               # Add PyPI installation section
```

### Implementation Steps

1. **Read Current Configuration**
   - Read `/home/stevejackson/Projects/safeshell/pyproject.toml`
   - Identify existing fields under `[tool.poetry]`
   - Note current version, package structure, scripts

2. **Reference Implementation**
   - Read `/home/stevejackson/Projects/thai-lint/pyproject.toml`
   - Study metadata fields: license, homepage, repository, documentation, keywords, classifiers
   - Review include/exclude patterns

3. **Add License Field**
   ```toml
   [tool.poetry]
   license = "MIT"
   ```

4. **Add URL Fields**
   ```toml
   homepage = "https://github.com/be-wise-be-kind/safeshell"
   repository = "https://github.com/be-wise-be-kind/safeshell"
   documentation = "https://github.com/be-wise-be-kind/safeshell#readme"
   ```

5. **Add Keywords**
   ```toml
   keywords = [
       "shell",
       "safety",
       "ai",
       "command-line",
       "security",
       "wrapper",
       "cli",
       "governance",
       "python",
   ]
   ```

6. **Add Classifiers**
   ```toml
   classifiers = [
       "Development Status :: 3 - Alpha",
       "Intended Audience :: Developers",
       "License :: OSI Approved :: MIT License",
       "Programming Language :: Python :: 3",
       "Programming Language :: Python :: 3.11",
       "Programming Language :: Python :: 3 :: Only",
       "Topic :: Software Development :: Quality Assurance",
       "Topic :: System :: Shells",
       "Topic :: Utilities",
       "Environment :: Console",
       "Operating System :: OS Independent",
       "Typing :: Typed",
   ]
   ```

7. **Add Include/Exclude Patterns**
   ```toml
   include = [
       "README.md",
       "LICENSE",
       "CHANGELOG.md",
   ]
   exclude = [
       "tests",
       "tests/*",
       ".github",
       ".ai",
       ".roadmap",
       "docs",
       "examples",
   ]
   ```

8. **Create LICENSE File**
   - If `/home/stevejackson/Projects/safeshell/LICENSE` doesn't exist, create MIT license
   - Use standard MIT license text with current year and author name

9. **Update README.md**
   - Add "Installation" section near the top
   - Include installation command: `pip install safeshell`
   - Add note about current alpha status
   - Example:
     ```markdown
     ## Installation

     Install safeshell from PyPI:

     ```bash
     pip install safeshell
     ```

     **Note**: safeshell is currently in alpha. The API and configuration format may change.
     ```

10. **Test Build Locally**
    ```bash
    cd /home/stevejackson/Projects/safeshell
    poetry build
    ls -lh dist/
    tar -tzf dist/safeshell-*.tar.gz | head -20
    unzip -l dist/safeshell-*.whl | head -20
    ```

11. **Verify Package Contents**
    - Source distribution (.tar.gz) includes: src/, README.md, LICENSE, pyproject.toml
    - Wheel (.whl) includes: safeshell package, metadata
    - Excludes: tests/, .github/, .ai/, .roadmap/

12. **Validate Configuration**
    ```bash
    poetry check
    ```

### Testing Strategy

**Manual Testing:**
1. Build package: `poetry build`
2. Inspect dist/ directory contents
3. Extract source distribution, verify file list
4. Extract wheel, verify package structure
5. Verify no test files or dev directories included

**Validation Commands:**
```bash
# Build package
poetry build

# List build artifacts
ls -lh dist/

# Inspect source distribution
tar -tzf dist/safeshell-0.1.0.tar.gz

# Inspect wheel
unzip -l dist/safeshell-0.1.0-py3-none-any.whl

# Validate pyproject.toml
poetry check
```

**Success Criteria:**
- `poetry build` succeeds without errors
- dist/ contains both .tar.gz and .whl files
- Source distribution includes README, LICENSE, src/
- Wheel includes safeshell package
- No test, .github, .ai, or .roadmap files in distributions
- `poetry check` validates configuration

### Documentation Updates
- README.md: Add Installation section with pip command
- pyproject.toml: Complete metadata for PyPI discovery

### Deployment Notes
- No deployment in this PR
- Changes are configuration-only
- Package not published to PyPI yet

### Rollback Plan
If issues arise, revert to previous pyproject.toml:
```bash
git revert <commit-hash>
```

---

## PR2: Automated PyPI Publishing Workflow

### Goal
Create GitHub Actions workflow to automatically publish safeshell to PyPI when version tags are pushed, using PyPI Trusted Publishing (OIDC) for secure authentication.

### Motivation
Automates the release process, ensuring only tested code is published to PyPI. Eliminates manual token management through OIDC. Creates professional GitHub releases with changelog extraction.

### Scope
- Create publish-pypi.yml workflow file
- Configure multi-stage workflow: test → build → publish → release
- Use PyPI Trusted Publishing (OIDC)
- Extract changelog for GitHub releases
- Document Trusted Publishing setup

### Files Changed
```
.github/workflows/publish-pypi.yml    # New workflow file
docs/pypi-setup.md                    # Trusted Publishing setup guide (new)
```

### Implementation Steps

1. **Read Reference Workflow**
   - Read `/home/stevejackson/Projects/thai-lint/.github/workflows/publish-pypi.yml`
   - Understand workflow structure: test → build → publish-pypi → create-release
   - Note permissions, triggers, environment configuration

2. **Create Workflow File**
   - Create `.github/workflows/publish-pypi.yml`
   - Use multi-stage job structure

3. **Configure Workflow Trigger**
   ```yaml
   name: Publish to PyPI

   on:
     push:
       tags:
         - 'v*.*.*'  # Trigger on version tags like v0.1.0, v0.2.0
   ```

4. **Set Permissions**
   ```yaml
   permissions:
     contents: write  # For creating GitHub releases
     id-token: write  # For PyPI Trusted Publishing (OIDC)
   ```

5. **Create Test Job**
   ```yaml
   jobs:
     test:
       name: Run Tests and Quality Checks
       runs-on: ubuntu-latest
       steps:
         - Checkout code (full history for changelog)
         - Setup Python 3.11
         - Install Poetry
         - Install dependencies: poetry install --with dev
         - Run linting: ruff check src/
         - Run type checking: mypy src/
         - Run tests: pytest --cov=src --cov-report=term-missing
   ```

6. **Create Build Job**
   ```yaml
   build:
     name: Build Package
     needs: test
     runs-on: ubuntu-latest
     steps:
       - Checkout code
       - Setup Python 3.11
       - Install Poetry
       - Build package: poetry build
       - Verify package contents (tar -tzf, unzip -l)
       - Upload build artifacts
   ```

7. **Create Publish Job**
   ```yaml
   publish-pypi:
     name: Publish to PyPI
     needs: build
     runs-on: ubuntu-latest
     environment:
       name: pypi
       url: https://pypi.org/project/safeshell/
     steps:
       - Download build artifacts
       - Publish to PyPI using pypa/gh-action-pypi-publish@release/v1
         (uses OIDC - no token needed)
   ```

8. **Create Release Job**
   ```yaml
   create-release:
     name: Create GitHub Release
     needs: publish-pypi
     runs-on: ubuntu-latest
     steps:
       - Checkout code (full history)
       - Extract version from tag (GITHUB_REF)
       - Extract changelog for version from CHANGELOG.md
       - Download build artifacts
       - Create GitHub Release using softprops/action-gh-release@v1
       - Attach dist/*.tar.gz and dist/*.whl files
       - Post-release notification with URLs
   ```

9. **Adapt URLs and Commands**
   - Change all `thailint` references to `safeshell`
   - Update PyPI URL: https://pypi.org/project/safeshell/
   - Verify test commands match safeshell's setup
   - Adjust coverage paths if needed

10. **Create Trusted Publishing Setup Guide**
    - Create `docs/pypi-setup.md`
    - Document PyPI Trusted Publishing configuration steps:
      1. Go to https://pypi.org/manage/account/publishing/
      2. Add new publisher
      3. PyPI Project Name: `safeshell`
      4. Owner: `be-wise-be-kind`
      5. Repository: `safeshell`
      6. Workflow name: `publish-pypi.yml`
      7. Environment: `pypi`
    - Include screenshots or step-by-step instructions
    - Document first-time setup requirements

11. **Add Workflow Comments**
    - Add purpose/scope/overview comments at top of workflow
    - Comment each job's purpose
    - Document OIDC authentication method
    - Note changelog extraction logic

### Testing Strategy

**Pre-Merge Testing:**
1. Validate workflow syntax:
   ```bash
   # GitHub CLI or workflow validator
   gh workflow view publish-pypi.yml
   ```

2. Test locally (without actual publish):
   - Run test commands manually
   - Test build process: `poetry build`
   - Verify changelog extraction logic
   - Test version extraction from tag name

3. Code review checks:
   - All jobs have `needs` dependencies for correct ordering
   - Permissions are minimal and explicit
   - OIDC configuration correct (no token usage)
   - URLs point to safeshell, not thailint
   - Artifact upload/download matches

**Post-Merge Testing:**
1. **TestPyPI Practice Run** (after PR3 with CHANGELOG.md):
   - Create test tag: `v0.1.0-test`
   - Temporarily modify workflow to publish to TestPyPI
   - Verify workflow execution
   - Install from TestPyPI: `pip install --index-url https://test.pypi.org/simple/ safeshell`
   - Test CLI commands work

2. **Production Release** (after TestPyPI validation):
   - Revert TestPyPI changes
   - Create production tag: `v0.1.0`
   - Push tag: `git push origin v0.1.0`
   - Monitor workflow execution
   - Verify package on PyPI
   - Test installation: `pip install safeshell`

**Workflow Validation:**
- All jobs complete successfully
- Tests pass before build
- Build succeeds and artifacts uploaded
- Publish succeeds with OIDC
- GitHub release created with changelog
- Package appears on PyPI

### Documentation Updates
- docs/pypi-setup.md: Complete Trusted Publishing setup guide
- .github/workflows/publish-pypi.yml: Well-commented workflow

### Deployment Notes

**Prerequisites:**
1. Maintainer has PyPI account
2. Trusted Publishing configured at pypi.org (follow docs/pypi-setup.md)
3. GitHub repository has `pypi` environment configured
4. CHANGELOG.md exists (created in PR3, but workflow should handle missing file gracefully)

**Deployment Process:**
1. Merge PR to main
2. No immediate deployment (triggered by tags)
3. Workflow activates when version tags pushed

**First Release:**
1. After PR3 merged (CHANGELOG.md exists)
2. Configure Trusted Publishing at pypi.org
3. Test on TestPyPI first
4. Create production tag: `git tag v0.1.0 && git push origin v0.1.0`
5. Monitor workflow: https://github.com/be-wise-be-kind/safeshell/actions
6. Verify package: https://pypi.org/project/safeshell/

### Rollback Plan

If workflow issues arise:
1. Delete problematic tag: `git push origin :refs/tags/v0.1.0`
2. Fix workflow issues
3. Recreate tag after fixes

If bad package published:
1. Yank release from PyPI (doesn't delete, marks as unavailable)
2. Fix issues
3. Publish new patch version

### Security Considerations
- No API tokens stored (OIDC authentication)
- Minimal permissions (contents:write, id-token:write)
- Environment protection (pypi environment)
- Test gate prevents publishing broken code

---

## PR3: Changelog and Release Documentation

### Goal
Create professional changelog following Keep a Changelog format and comprehensive release documentation to guide maintainers through version bumps and publishing.

### Motivation
Professional changelog provides users with clear version history and upgrade guidance. Release documentation ensures consistent, error-free release process for maintainers.

### Scope
- Create CHANGELOG.md with Keep a Changelog format
- Document version 0.1.0 (initial release)
- Create docs/releasing.md with version bump and publishing procedures
- Update README.md with PyPI badge and version references

### Files Changed
```
CHANGELOG.md          # New changelog file (Keep a Changelog format)
docs/releasing.md     # New release process documentation
README.md             # Add PyPI badge, update references
```

### Implementation Steps

1. **Read Reference Changelog**
   - Read `/home/stevejackson/Projects/thai-lint/CHANGELOG.md`
   - Understand Keep a Changelog format
   - Note section structure: Added, Changed, Fixed, etc.
   - Review version history format

2. **Create CHANGELOG.md**
   - Create `/home/stevejackson/Projects/safeshell/CHANGELOG.md`
   - Add header with purpose/scope/overview comments
   - Add Keep a Changelog reference
   - Add Semantic Versioning reference

3. **Add Changelog Header**
   ```markdown
   # Changelog

   **Purpose**: Version history and release notes for all safeshell package versions

   **Scope**: All public releases, API changes, features, bug fixes, and breaking changes

   **Overview**: Maintains comprehensive version history following Keep a Changelog format. Documents
       all notable changes in each release including new features, bug fixes, breaking changes,
       deprecations, and security updates. Organized by version with release dates. Supports
       automated changelog extraction for GitHub releases and user upgrade planning.

   **Dependencies**: Semantic versioning (semver.org), Keep a Changelog format (keepachangelog.com)

   **Exports**: Release history, upgrade guides, breaking change documentation

   **Related**: pyproject.toml (version configuration), GitHub releases, docs/releasing.md

   **Implementation**: Keep a Changelog 1.1.0 format with semantic versioning and organized change categories

   All notable changes to this project will be documented in this file.

   The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
   and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
   ```

4. **Add [Unreleased] Section**
   ```markdown
   ## [Unreleased]

   ### Added
   - Future features will be listed here

   ### Changed
   - Future changes will be listed here

   ### Fixed
   - Future fixes will be listed here
   ```

5. **Document Version 0.1.0**
   - Research safeshell features from README.md and codebase
   - List all major features in [0.1.0] section
   - Use date format: YYYY-MM-DD
   - Example structure:
   ```markdown
   ## [0.1.0] - 2025-12-09

   **Initial Alpha Release** - Command-line safety layer for AI coding assistants

   ### Added
   - **Core Safety Layer**: Command filtering and approval system
     - Interactive approval prompts for dangerous commands
     - Configurable rule engine with YAML rules
     - Context-aware rules (ai_only, human_only)

   - **Shell Wrapper**: Transparent command execution with safety checks
     - safeshell-wrapper for interactive sessions
     - Command history integration
     - Rich terminal UI with typer and rich

   - **Rule System**: Flexible rule configuration
     - YAML-based rule definitions
     - Pattern matching for commands
     - Severity levels and approval logic
     - AI-only and human-only filtering

   - **CLI Commands**
     - safeshell: Main CLI for configuration and management
     - safeshell-wrapper: Shell wrapper for safe command execution

   - **Development Tools**
     - Comprehensive test suite with pytest
     - Pre-commit hooks for quality gates
     - Ruff, mypy, pylint integration
     - Development documentation in .ai/

   ### Documentation
   - README.md with usage examples
   - .ai/ directory with agent guides and architecture docs
   - Demo guide and testing progress tracker
   ```

6. **Add Version History Section**
   ```markdown
   ## Version History

   - **0.1.0** (2025-12-09): Initial alpha release with core safety layer
   ```

7. **Add Upgrade Guide Section**
   ```markdown
   ## Upgrade Guide

   ### Upgrading to 0.1.0 (Initial Release)

   This is the first release. Install with:
   ```
   pip install safeshell
   ```

   No migration needed for new installations.
   ```

8. **Add Contributing Section**
   ```markdown
   ## Contributing

   When adding entries to this changelog:

   1. Add changes to `[Unreleased]` section during development
   2. Move to versioned section when releasing
   3. Use categories: Added, Changed, Deprecated, Removed, Fixed, Security
   4. Include user-facing changes only (not internal refactors)
   5. Link to issues/PRs when relevant
   6. Follow Keep a Changelog format
   ```

9. **Add Links Section**
   ```markdown
   ## Links

   - [PyPI Package](https://pypi.org/project/safeshell/)
   - [GitHub Repository](https://github.com/be-wise-be-kind/safeshell)
   - [Issue Tracker](https://github.com/be-wise-be-kind/safeshell/issues)
   - [Keep a Changelog](https://keepachangelog.com/)
   - [Semantic Versioning](https://semver.org/)
   ```

10. **Create docs/releasing.md**
    - Create comprehensive release process documentation
    - Cover version bumping, testing, tagging, publishing
    - Include troubleshooting section
    - Document TestPyPI validation steps

11. **docs/releasing.md Structure**
    ```markdown
    # Release Process

    ## Overview
    Guide for maintainers on releasing new versions of safeshell to PyPI.

    ## Pre-Release Checklist
    - [ ] All tests passing
    - [ ] CHANGELOG.md updated
    - [ ] Version bumped in pyproject.toml
    - [ ] README.md updated if needed
    - [ ] Documentation current

    ## Version Bumping
    1. Determine version type (major.minor.patch)
    2. Update pyproject.toml version
    3. Update CHANGELOG.md [Unreleased] → [Version]
    4. Commit changes

    ## TestPyPI Validation
    1. Temporarily modify workflow for TestPyPI
    2. Create test tag: git tag v0.X.Y-test
    3. Push tag: git push origin v0.X.Y-test
    4. Verify TestPyPI: https://test.pypi.org/project/safeshell/
    5. Test install: pip install --index-url https://test.pypi.org/simple/ safeshell
    6. Revert workflow changes

    ## Production Release
    1. Ensure Trusted Publishing configured (docs/pypi-setup.md)
    2. Create tag: git tag v0.X.Y
    3. Push tag: git push origin v0.X.Y
    4. Monitor workflow: GitHub Actions
    5. Verify PyPI: https://pypi.org/project/safeshell/
    6. Test install: pip install safeshell
    7. Verify GitHub release created

    ## Post-Release
    - Announce release (if applicable)
    - Monitor for issues
    - Update documentation sites if needed

    ## Troubleshooting
    (Common issues and solutions)
    ```

12. **Update README.md**
    - Add PyPI badge at top:
      ```markdown
      [![PyPI version](https://badge.fury.io/py/safeshell.svg)](https://badge.fury.io/py/safeshell)
      [![Python Versions](https://img.shields.io/pypi/pyversions/safeshell.svg)](https://pypi.org/project/safeshell/)
      ```
    - Verify Installation section exists (from PR1)
    - Add upgrade instructions: `pip install --upgrade safeshell`

13. **Verify Include Configuration**
    - Ensure CHANGELOG.md in pyproject.toml includes (from PR1)
    - If not, update pyproject.toml to include it

### Testing Strategy

**Manual Testing:**
1. Read CHANGELOG.md for clarity and completeness
2. Verify Keep a Changelog format compliance
3. Check version 0.1.0 accurately reflects features
4. Review docs/releasing.md for completeness
5. Test changelog extraction logic manually:
   ```bash
   VERSION=0.1.0
   sed -n "/## \[$VERSION\]/,/## \[/p" CHANGELOG.md | sed '$d' | tail -n +2
   ```

**Content Validation:**
- CHANGELOG.md includes all major features from README
- Version 0.1.0 date is current release date
- [Unreleased] section present for future changes
- docs/releasing.md covers all release steps
- README.md has PyPI badge

**Build Validation:**
```bash
# Verify CHANGELOG.md included in build
poetry build
tar -tzf dist/safeshell-*.tar.gz | grep CHANGELOG.md
```

### Documentation Updates
- CHANGELOG.md: Complete version history
- docs/releasing.md: Comprehensive release guide
- README.md: PyPI badge and upgrade instructions

### Deployment Notes
- No deployment in this PR
- Documentation-only changes
- Prepares for first PyPI release after merge

### Rollback Plan
If issues with documentation:
```bash
git revert <commit-hash>
```

No risk to application functionality (documentation only).

---

## Implementation Guidelines

### Code Standards
- Follow existing code style (ruff, pylint, mypy)
- Use Poetry for all package operations
- Follow Keep a Changelog format for CHANGELOG.md
- Document all workflow steps with comments
- Use semantic versioning (semver.org)

### Testing Requirements

**PR1 Testing:**
- Manual: `poetry build` and inspect dist/
- Validation: `poetry check`
- Verify includes/excludes correct

**PR2 Testing:**
- Manual workflow validation (syntax)
- TestPyPI practice run
- Production release monitoring
- Installation verification

**PR3 Testing:**
- CHANGELOG.md format validation
- Changelog extraction logic testing
- Build includes CHANGELOG.md
- Release documentation completeness

### Documentation Standards
- All files include purpose/scope/overview headers
- CHANGELOG.md follows Keep a Changelog 1.1.0
- Release documentation clear and comprehensive
- Workflow comments explain purpose of each job

### Security Considerations
- Use PyPI Trusted Publishing (OIDC) - no tokens
- Minimal workflow permissions
- Quality gate prevents publishing broken code
- TestPyPI validation before production

### Performance Targets
- Workflow completes in <5 minutes
- Build time <1 minute
- Publish time <1 minute

## Rollout Strategy

### Phase 1: Metadata (PR1)
1. Merge PR1 to main
2. Validate with `poetry build`
3. No public release yet

### Phase 2: Workflow (PR2)
1. Merge PR2 to main
2. Configure Trusted Publishing at pypi.org
3. No automatic publish (requires tag)

### Phase 3: Documentation and First Release (PR3)
1. Merge PR3 to main
2. Validate TestPyPI with test tag
3. Create production tag v0.1.0
4. Monitor first publish
5. Verify installation: `pip install safeshell`

## Success Metrics

### Launch Metrics
- Package published to PyPI: https://pypi.org/project/safeshell/
- Installation works: `pip install safeshell`
- GitHub release created with changelog
- All workflow jobs complete successfully
- Zero manual token management

### Ongoing Metrics
- Workflow success rate >95%
- Average workflow time <5 minutes
- CHANGELOG.md kept current
- Clear release process followed
- Users can upgrade easily: `pip install --upgrade safeshell`

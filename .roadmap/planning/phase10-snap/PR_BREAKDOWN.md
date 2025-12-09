# Phase 10: Snap Store Distribution - PR Breakdown

**Purpose**: Detailed implementation breakdown of Snap Store Distribution into manageable, atomic pull requests

**Scope**: Complete feature implementation from initial snapcraft configuration through automated Snap Store publishing

**Overview**: Comprehensive breakdown of the Snap Store Distribution feature into 2 manageable, atomic
    pull requests. Each PR is designed to be self-contained, testable, and maintains application functionality
    while incrementally building toward the complete feature. Includes detailed implementation steps, file
    structures, testing requirements, and success criteria for each PR.

**Dependencies**: PyPI distribution (Phase 9), Poetry build system, GitHub Actions infrastructure, Snap Store account

**Exports**: PR implementation plans, file structures, testing strategies, and success criteria for each development phase

**Related**: AI_CONTEXT.md for feature overview, PROGRESS_TRACKER.md for status tracking

**Implementation**: Atomic PR approach with detailed step-by-step implementation guidance and comprehensive testing validation

---

## Overview
This document breaks down the Snap Store Distribution feature into manageable, atomic PRs. Each PR is designed to be:
- Self-contained and testable
- Maintains a working application
- Incrementally builds toward the complete feature
- Revertible if needed

---

## PR #1: Snapcraft Configuration and Local Build

### Summary
Establish Snap packaging configuration with snapcraft.yaml, enabling local snap building and testing. This PR creates the foundation for Snap Store distribution without requiring external infrastructure or credentials.

### Goals
- Create working snapcraft.yaml configuration
- Enable local snap building and installation
- Validate safeshell functionality within snap environment
- Document snap installation process for users

### Implementation Steps

#### Step 1: Research Snap Packaging Requirements
1. Review Snap packaging documentation for Python/Poetry projects
2. Identify appropriate snap base (core22 vs core24)
3. Research Python plugin configuration for Poetry integration
4. Understand classic confinement requirements and implications
5. Review entry point configuration patterns

#### Step 2: Create snapcraft.yaml Configuration
1. Create `snap/` directory in project root
2. Create `snap/snapcraft.yaml` with the following structure:

```yaml
name: safeshell
version: git
summary: Safety wrapper for shell commands requiring approval
description: |
  Safeshell intercepts shell commands and requires explicit approval before
  execution, providing an additional safety layer when working with AI coding
  assistants or running untrusted scripts.

base: core22
confinement: classic
grade: stable

apps:
  safeshell:
    command: bin/safeshell

  safeshell-shim:
    command: bin/safeshell-shim

parts:
  safeshell:
    plugin: python
    source: .
    build-packages:
      - python3-dev
    stage-packages:
      - python3-venv
    python-requirements:
      - requirements.txt
    override-build: |
      # Install Poetry
      pip install poetry
      # Export dependencies to requirements.txt for snap
      poetry export -f requirements.txt --output requirements.txt --without-hashes
      # Build and install with Poetry
      poetry build
      pip install dist/*.whl
```

3. Adjust configuration based on project structure
4. Configure environment variables if needed
5. Add any required snap hooks for post-install configuration

#### Step 3: Test Local Snap Build
1. Install snapcraft: `sudo snap install snapcraft --classic`
2. Build snap locally: `snapcraft`
3. Verify snap file created: `safeshell_*.snap`
4. Check snap file size (should be reasonable, under 50MB)
5. Troubleshoot any build errors

#### Step 4: Test Snap Installation and Functionality
1. Install snap locally: `sudo snap install --dangerous --classic safeshell_*.snap`
2. Verify commands available:
   - `safeshell --version`
   - `safeshell --help`
   - `safeshell-shim --help`
3. Test basic interception: `safeshell rm -rf test_file`
4. Test configuration file access
5. Test rule file functionality
6. Test approval workflow
7. Test CLAUDECODE bypass
8. Verify log file creation and access

#### Step 5: Update Documentation
1. Update `README.md` installation section:
   - Add "Install via Snap" subsection
   - Include `sudo snap install safeshell --classic` command
   - Note classic confinement requirement
   - Add alternative local snap install instructions

2. Update `docs/installation.md`:
   - Add detailed snap installation instructions
   - Document snap-specific considerations
   - Include troubleshooting section for snap issues

3. Update `CONTRIBUTING.md`:
   - Add "Building Snap Locally" section
   - Document snap testing procedures
   - Include snap build requirements

#### Step 6: Clean Up and Validation
1. Add `*.snap` to `.gitignore`
2. Add snap build artifacts to `.gitignore` if needed
3. Test clean build from scratch
4. Verify no unnecessary files in snap package
5. Document any known limitations or issues

### Files to Create
```
snap/
└── snapcraft.yaml
```

### Files to Modify
```
.gitignore
README.md
docs/installation.md
CONTRIBUTING.md
```

### Testing Checklist
- [ ] Snap builds successfully with `snapcraft`
- [ ] Snap file size is reasonable (under 50MB)
- [ ] Snap installs without errors
- [ ] `safeshell --version` displays correct version
- [ ] Command interception works correctly
- [ ] Configuration file can be created and modified
- [ ] Rule files load and apply correctly
- [ ] Approval prompts display properly
- [ ] CLAUDECODE bypass functions as expected
- [ ] Log files are created and accessible
- [ ] Snap uninstalls cleanly: `sudo snap remove safeshell`
- [ ] Re-installation works without issues
- [ ] Test on Ubuntu 22.04 LTS
- [ ] Test on Ubuntu 24.04 LTS (if available)

### Success Criteria
- [ ] snapcraft.yaml configuration is complete and functional
- [ ] Snap builds successfully without errors or warnings
- [ ] All safeshell functionality works in snap-installed version
- [ ] Documentation clearly explains snap installation
- [ ] No regressions compared to pip-installed version
- [ ] Snap package passes local testing on supported Ubuntu versions

### Branch Name
`feat/snap-packaging-config`

### Commit Message Template
```
feat: Add Snap packaging configuration for Linux distribution

- Create snap/snapcraft.yaml with classic confinement
- Configure Python plugin for Poetry-based build
- Define entry points for safeshell and safeshell-shim
- Add snap installation documentation
- Update .gitignore for snap build artifacts

Enables local snap building and installation, providing an
alternative installation method for Linux users.
```

### PR Description Template
```markdown
## Summary
Adds Snap packaging configuration to enable distribution via Snap Store. This PR establishes the foundation for snap building and testing locally before implementing automated publishing in a future PR.

## Changes
- Created `snap/snapcraft.yaml` with classic confinement configuration
- Configured Python plugin for Poetry-based project
- Defined CLI entry points for safeshell commands
- Updated installation documentation in README.md
- Added snap build instructions to CONTRIBUTING.md

## Testing
- [x] Built snap locally with `snapcraft`
- [x] Installed snap with `snap install --dangerous --classic`
- [x] Verified all CLI commands functional
- [x] Tested command interception and approval workflow
- [x] Validated configuration and rule file access
- [x] Tested on Ubuntu 22.04 LTS
- [x] Tested on Ubuntu 24.04 LTS

## Installation
Users can now install via snap (after Snap Store publishing):
```bash
sudo snap install safeshell --classic
```

Or build and install locally:
```bash
snapcraft
sudo snap install --dangerous --classic safeshell_*.snap
```

## Notes
- Classic confinement is required for shell interception functionality
- Snap Store publishing will be handled in a separate PR
- This PR focuses on establishing working snap configuration
```

---

## PR #2: Automated Snap Publishing Workflow

### Summary
Implement GitHub Actions workflow for automated snap building and publishing to Snap Store. This PR enables continuous delivery of snap packages synchronized with PyPI releases.

### Goals
- Automate snap building via GitHub Actions
- Publish snaps to Snap Store automatically on releases
- Enable testing snap builds on PRs
- Document Snap Store publishing process

### Implementation Steps

#### Step 1: Snap Store Account Setup (Manual Prerequisite)
1. Create Snap Store developer account at https://snapcraft.io/
2. Register "safeshell" application name
3. Generate Snap Store credentials:
   - Login to Snap Store
   - Navigate to account settings
   - Generate new credentials/token for CI/CD
4. Save credentials securely (needed for GitHub Secrets)

#### Step 2: Configure GitHub Secrets
1. Navigate to GitHub repository settings
2. Go to Secrets and Variables > Actions
3. Add new repository secret:
   - Name: `SNAP_STORE_TOKEN`
   - Value: [Snap Store credentials from Step 1]
4. Verify secret is properly saved

#### Step 3: Create Snap Build Workflow
1. Create `.github/workflows/snap.yml`
2. Configure workflow structure:

```yaml
name: Snap Build and Publish

on:
  push:
    tags:
      - 'v*'
  pull_request:
    paths:
      - 'snap/**'
      - 'safeshell/**'
      - 'pyproject.toml'
      - '.github/workflows/snap.yml'

jobs:
  build-snap:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Build snap
        uses: snapcore/action-build@v1
        id: build

      - name: Upload snap artifact
        uses: actions/upload-artifact@v4
        with:
          name: safeshell-snap
          path: ${{ steps.build.outputs.snap }}

      - name: Test snap installation
        run: |
          sudo snap install --dangerous --classic ${{ steps.build.outputs.snap }}
          safeshell --version
          sudo snap remove safeshell

  publish-snap:
    needs: build-snap
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/v')
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Build and publish to Snap Store
        uses: snapcore/action-publish@v1
        env:
          SNAPCRAFT_STORE_CREDENTIALS: ${{ secrets.SNAP_STORE_TOKEN }}
        with:
          snap: ${{ needs.build-snap.outputs.snap }}
          release: stable
```

3. Refine workflow based on project needs
4. Add conditional logic for beta vs stable channel
5. Configure proper artifact handling

#### Step 4: Test Workflow with Beta Release
1. Create test tag: `git tag v0.0.0-beta.1`
2. Push tag: `git push origin v0.0.0-beta.1`
3. Monitor GitHub Actions workflow execution
4. Verify snap builds successfully
5. Check Snap Store for published package in beta channel
6. Test installation from Snap Store: `snap install safeshell --beta --classic`
7. Validate functionality of store-installed snap
8. Delete test tag after validation

#### Step 5: Update Documentation
1. Update `README.md`:
   - Add snap build status badge
   - Update installation instructions to prefer Snap Store
   - Remove local snap build instructions from main section

2. Update `CONTRIBUTING.md`:
   - Document snap release process
   - Explain beta vs stable channel strategy
   - Add troubleshooting for snap publishing issues
   - Document credential management

3. Create/update `docs/release-process.md`:
   - Include snap publishing in release checklist
   - Document channel promotion workflow
   - Add snap-specific release notes requirements

#### Step 6: Validation and Cleanup
1. Verify workflow runs on PR (build only)
2. Verify workflow publishes on release tags
3. Test stable channel promotion
4. Confirm badge displays correctly in README
5. Review and clean up any test artifacts

### Files to Create
```
.github/workflows/snap.yml
```

### Files to Modify
```
README.md
CONTRIBUTING.md
docs/release-process.md (or create if doesn't exist)
```

### Testing Checklist
- [ ] GitHub Actions workflow triggers on push to main
- [ ] Workflow builds snap successfully in CI
- [ ] Snap artifact uploads correctly
- [ ] Workflow tests snap installation in CI
- [ ] Workflow publishes to Snap Store on release tags
- [ ] Beta channel publication works correctly
- [ ] Snap installs from Snap Store: `snap install safeshell --beta --classic`
- [ ] Store-installed snap functions identically to local build
- [ ] Stable channel promotion workflow functions
- [ ] Build status badge displays correctly in README
- [ ] Workflow fails gracefully on errors
- [ ] Secrets are properly secured and not exposed in logs

### Success Criteria
- [ ] Automated snap building works in GitHub Actions
- [ ] Snap publishes to Snap Store automatically on releases
- [ ] Users can install via `snap install safeshell --classic`
- [ ] Beta and stable channel strategy implemented
- [ ] Documentation covers snap publishing process
- [ ] Build status badge added to README
- [ ] Zero manual steps required for snap publishing

### Branch Name
`feat/snap-automated-publishing`

### Commit Message Template
```
feat: Add automated Snap Store publishing workflow

- Create .github/workflows/snap.yml for automated builds
- Configure Snap Store publishing on releases
- Add snap build testing on pull requests
- Update documentation with Snap Store installation
- Add snap build status badge to README

Enables continuous delivery of snap packages to Snap Store,
synchronized with PyPI releases.
```

### PR Description Template
```markdown
## Summary
Implements automated snap building and publishing via GitHub Actions. Snap packages now publish automatically to Snap Store when new releases are tagged, providing streamlined Linux installation.

## Changes
- Created `.github/workflows/snap.yml` for automated snap operations
- Configured Snap Store publishing using GitHub Secrets
- Added snap build testing on PRs (without publishing)
- Updated README.md with Snap Store installation instructions
- Added snap build status badge
- Documented snap release process in CONTRIBUTING.md

## Prerequisites
- [x] Snap Store developer account created
- [x] "safeshell" application name registered in Snap Store
- [x] Snap Store credentials added to GitHub Secrets
- [x] PR #1 (snapcraft configuration) merged

## Workflow Behavior
- **On Pull Requests**: Builds snap and tests installation (does not publish)
- **On Release Tags**: Builds snap and publishes to Snap Store stable channel

## Testing
- [x] Workflow builds snap successfully in CI
- [x] Snap installation test passes in CI
- [x] Beta channel publication tested with test tag
- [x] Snap installs from Snap Store
- [x] Store-installed snap functions correctly
- [x] Build status badge displays properly

## Installation
Users can now install safeshell from Snap Store:
```bash
sudo snap install safeshell --classic
```

## Release Process
1. Create and push release tag: `git tag v1.0.0 && git push origin v1.0.0`
2. GitHub Actions automatically builds and publishes snap
3. Snap available in Snap Store within minutes
4. Verify installation: `snap install safeshell --classic`

## Notes
- Classic confinement required for shell interception
- Snap versions stay synchronized with PyPI releases
- Beta channel available for testing pre-releases
```

---

## Implementation Guidelines

### Code Standards
- Follow snapcraft.yaml best practices and conventions
- Use explicit versions for snap base and build dependencies
- Comment complex snap configuration sections
- Keep snapcraft.yaml readable and well-organized
- Use consistent indentation (2 spaces) in YAML files

### Testing Requirements
- Test snap builds on multiple Ubuntu versions (22.04, 24.04)
- Validate all CLI functionality in snap environment
- Test configuration file persistence across snap updates
- Verify rule file loading and application
- Test approval workflow end-to-end
- Validate CLAUDECODE bypass functionality
- Test snap refresh/update scenarios
- Verify clean uninstallation

### Documentation Standards
- Clearly explain classic confinement requirement
- Provide troubleshooting guidance for snap installation
- Document differences between pip and snap installation
- Include snap-specific configuration considerations
- Maintain consistency with existing documentation style
- Use atemporal language (avoid "will", "going to", etc.)

### Security Considerations
- Protect Snap Store credentials using GitHub Secrets
- Never commit credentials to repository
- Use classic confinement (required for functionality)
- Document security implications of classic confinement
- Validate snap package integrity in CI
- Review snap permissions and access requirements

### Performance Targets
- Snap build time under 10 minutes in CI
- Snap package size under 50MB
- Installation time under 2 minutes on standard connection
- No performance degradation vs pip-installed version
- Snap refresh/update completes quickly

## Rollout Strategy

### Phase 1: Beta Testing (After PR #1)
- Local snap building available for testing
- Manual distribution for early adopters
- Gather feedback on snap packaging
- Identify snap-specific issues

### Phase 2: Automated Publishing (After PR #2)
- GitHub Actions workflow active
- Publish initial version to beta channel
- Monitor Snap Store metrics and feedback
- Promote to stable channel after validation

### Phase 3: Primary Distribution Method
- Feature snap installation prominently in README
- Recommend snap as preferred Linux installation method
- Maintain pip installation as alternative
- Monitor adoption metrics

## Success Metrics

### Launch Metrics
- Snap builds successfully in CI (100% success rate)
- Zero critical issues in first stable release
- Snap installation success rate >95%
- Documentation completeness score >90%

### Ongoing Metrics
- Snap Store download counts
- Snap installation success rate
- Snap Store ratings and reviews
- Issue reports specific to snap installation
- Snap refresh/update success rate
- Community feedback on snap packaging

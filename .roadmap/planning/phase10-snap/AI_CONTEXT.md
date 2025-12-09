# Phase 10: Snap Store Distribution - AI Context

**Purpose**: AI agent context document for implementing Snap Store Distribution

**Scope**: Enable safeshell distribution via Snap Store for easy Linux installation across multiple distributions

**Overview**: Comprehensive context document for AI agents working on the Snap Store Distribution feature.
    This feature extends safeshell's distribution capabilities by packaging the application for Snap Store,
    providing users with a streamlined installation experience on Ubuntu and other Linux distributions.
    The implementation involves creating snapcraft configuration, establishing local build processes,
    and automating snap publishing through GitHub Actions.

**Dependencies**: PyPI distribution (Phase 9), Poetry build system, GitHub Actions infrastructure, Snap Store developer account

**Exports**: Snap package configuration, automated publishing workflow, snap-based installation method

**Related**: PR_BREAKDOWN.md for implementation tasks, PROGRESS_TRACKER.md for current status

**Implementation**: Two-phase approach starting with local snap configuration, followed by automated publishing via GitHub Actions

---

## Overview

Snap Store Distribution extends safeshell's reach by providing native snap packages for Linux users. Snap packaging offers several advantages for safeshell's distribution:

1. **Simplified Installation**: Single command installation across Ubuntu and Snap-enabled distributions
2. **Automatic Updates**: Users receive updates automatically through snap refresh
3. **Dependency Management**: Snap bundles all dependencies, eliminating conflicts
4. **Wide Compatibility**: Works across multiple Ubuntu versions and Snap-enabled distributions
5. **Trusted Distribution**: Snap Store provides secure, verified distribution channel

The implementation follows a progressive approach: first establishing working snap configuration with local build testing, then automating the build and publish process through GitHub Actions.

## Project Background

Safeshell is a safety wrapper for shell commands that intercepts and requires approval before execution. The tool is particularly valuable when working with AI coding assistants or running potentially dangerous scripts. Currently distributed via pip/PyPI, adding Snap Store distribution provides an alternative installation method that may be more familiar and convenient for Linux desktop users.

The snap package must maintain full functionality including:
- Shell command interception through safeshell-shim
- Configuration file management (~/.config/safeshell/)
- Rule file processing and application
- Interactive approval prompts
- CLAUDECODE bypass mechanism
- Comprehensive logging

## Feature Vision

### Distribution Goals
- Provide seamless snap-based installation for Linux users
- Maintain feature parity with pip-installed version
- Automate snap publishing synchronized with PyPI releases
- Establish Snap Store as a recommended installation method for Ubuntu users
- Enable automatic updates through snap refresh mechanism

### User Experience Goals
- One-command installation: `sudo snap install safeshell --classic`
- Immediate availability of CLI commands after installation
- Transparent operation identical to pip-installed version
- Clear documentation of snap-specific considerations
- Easy uninstallation and cleanup

### Maintenance Goals
- Zero manual steps for snap publishing on releases
- Automated testing of snap builds in CI
- Clear documentation for maintainers on snap processes
- Monitoring capability for snap adoption and issues

## Current Application Context

### Existing Distribution
- **Primary**: PyPI via pip install (Phase 9)
- **Build System**: Poetry for dependency management and packaging
- **CLI Entry Points**: safeshell and safeshell-shim defined in pyproject.toml
- **Installation Locations**:
  - Binaries: System Python site-packages
  - Config: ~/.config/safeshell/
  - Logs: ~/.local/state/safeshell/logs/

### Technical Characteristics
- **Language**: Python 3.8+
- **Dependencies**: Managed via Poetry, specified in pyproject.toml
- **Shell Integration**: Requires shell profile modification for interception
- **Configuration**: YAML-based configuration files
- **Rule System**: Context-aware rules with pattern matching

### Packaging Requirements
- Classic confinement needed for shell interception functionality
- Must access user's home directory for configuration
- Requires ability to modify shell environment variables
- Needs access to execute arbitrary shell commands (after approval)
- Should preserve all CLI functionality without modification

## Target Architecture

### Core Components

#### Snap Package Structure
```
safeshell.snap
├── bin/
│   ├── safeshell           # Main CLI command
│   └── safeshell-shim      # Shell interception wrapper
├── lib/
│   └── python3.x/
│       └── site-packages/
│           └── safeshell/  # Application code and dependencies
└── meta/
    ├── snap.yaml           # Snap metadata (auto-generated)
    └── hooks/              # Optional post-install hooks
```

#### Configuration Files
- **snapcraft.yaml**: Defines snap build configuration
- **GitHub Actions Workflow**: Automates building and publishing
- **Documentation Updates**: Installation and maintenance guides

### User Journey

#### Installation Flow
1. User discovers safeshell via documentation or Snap Store
2. User executes: `sudo snap install safeshell --classic`
3. Snap installs safeshell with all dependencies
4. CLI commands immediately available in PATH
5. User follows setup instructions to configure shell interception
6. Safeshell operates identically to pip-installed version

#### Update Flow
1. New safeshell version released with git tag
2. GitHub Actions builds and publishes snap automatically
3. User's system automatically detects snap update
4. Snap refresh installs new version seamlessly
5. User continues using safeshell without interruption

#### Uninstallation Flow
1. User executes: `sudo snap remove safeshell`
2. Snap removes binaries and bundled dependencies
3. User's configuration files remain in ~/.config/safeshell/ (optional cleanup)
4. Shell profile modifications remain (user removes manually if desired)

### Snap Configuration Strategy

#### Confinement Mode
- **Choice**: Classic confinement
- **Rationale**: Safeshell requires full shell access for command interception, configuration file access, and executing approved commands. Strict confinement would prevent core functionality.
- **Security Note**: Classic confinement requires manual review from Snap Store team before first publication

#### Build Plugin
- **Choice**: Python plugin with Poetry integration
- **Approach**: Export Poetry dependencies to requirements.txt during build, then use standard Python snap building
- **Benefit**: Leverages existing Poetry configuration while conforming to snap build expectations

#### Base Selection
- **Choice**: core22 (Ubuntu 22.04 LTS base)
- **Rationale**: Balance between stability, modern Python availability, and wide Ubuntu LTS adoption
- **Future**: Consider core24 when Ubuntu 24.04 LTS gains wider adoption

## Key Decisions Made

### Decision: Classic Confinement Required
**Context**: Snap offers multiple confinement modes (strict, classic, devmode).

**Options Considered**:
1. Strict confinement with interfaces for required access
2. Classic confinement for unrestricted system access
3. Devmode for development with plan to move to strict

**Decision**: Use classic confinement

**Rationale**:
- Safeshell's core functionality requires intercepting and executing shell commands
- Shell interception needs modification of environment variables (SHELL)
- Configuration files stored in user's home directory
- Approved commands must execute in user's actual environment
- Strict confinement interfaces insufficient for these requirements

**Trade-offs**:
- Classic snaps require manual Snap Store review (one-time delay)
- Users may be more cautious about classic snap installation
- Documentation must explain classic confinement requirement
- Security model relies on safeshell's own approval mechanism rather than snap confinement

### Decision: Poetry Export Approach for Dependencies
**Context**: Snap's Python plugin expects requirements.txt, while safeshell uses Poetry.

**Options Considered**:
1. Convert project to use requirements.txt instead of Poetry
2. Export Poetry dependencies to requirements.txt during snap build
3. Install Poetry in snap and use it for dependency management

**Decision**: Export Poetry dependencies to requirements.txt during snap build

**Rationale**:
- Maintains Poetry as primary dependency management tool
- Integrates cleanly with snap's Python plugin
- `poetry export` command provides exact dependency versions
- No runtime Poetry dependency in final snap

**Implementation**:
```yaml
override-build: |
  pip install poetry
  poetry export -f requirements.txt --output requirements.txt --without-hashes
  poetry build
  pip install dist/*.whl
```

### Decision: Two-Phase Implementation
**Context**: Snap packaging could be implemented all at once or incrementally.

**Options Considered**:
1. Single PR implementing everything including automation
2. Two PRs: configuration first, automation second
3. Three PRs: config, manual publishing, automation

**Decision**: Two PRs - configuration with local building, then automation

**Rationale**:
- PR #1 allows testing snap packaging without external dependencies
- Snap Store account setup can happen between PRs
- Local testing validates configuration before automation
- Easier to debug issues in smaller increments
- PR #1 provides value even if PR #2 delayed

### Decision: Mirror PyPI Release Cadence
**Context**: Snap releases could follow independent schedule or match PyPI.

**Options Considered**:
1. Independent snap release schedule
2. Mirror PyPI releases with automated publishing
3. Manual snap releases on demand

**Decision**: Mirror PyPI releases with automated publishing

**Rationale**:
- Maintains version consistency across distribution methods
- Automated workflow eliminates manual maintenance burden
- Users get updates simultaneously regardless of installation method
- Simplifies version management and documentation
- Reduces confusion about feature availability

## Integration Points

### With Existing Features

#### PyPI Distribution (Phase 9)
- Snap packaging depends on working Poetry build system
- Version numbers synchronized between pip and snap
- Release process triggers both PyPI and Snap Store publishing
- Documentation presents both installation methods equally

#### Configuration System
- Snap must access ~/.config/safeshell/ for configuration files
- Classic confinement enables normal file access
- Configuration file behavior identical to pip-installed version
- Snap updates preserve user configuration

#### Shell Integration
- Snap-installed binaries must be available in PATH
- Shell profile modifications work identically
- CLAUDECODE bypass mechanism functions unchanged
- Shell interception operates transparently

#### Logging System
- Snap must access ~/.local/state/safeshell/logs/
- Log file permissions and access unchanged
- Log rotation and management work identically

### With Development Workflow

#### Version Management
- Git tags trigger both PyPI and snap publishing
- Version number extracted from git tag
- snapcraft.yaml uses `version: git` for automatic versioning

#### CI/CD Pipeline
- Snap workflow runs alongside existing test and publish workflows
- Snap builds test application functionality
- Failed snap builds block releases
- Separate workflow allows independent snap-specific configuration

#### Testing Strategy
- Snap installation tested in GitHub Actions
- Basic functionality validation in CI
- Manual testing on Ubuntu LTS versions before stable promotion
- Beta channel enables pre-release testing

## Success Metrics

### Adoption Metrics
- Snap Store download counts
- Snap vs pip installation ratio
- Geographic distribution of snap installs
- Snap Store search ranking for "safeshell"

### Quality Metrics
- Snap build success rate in CI (target: 100%)
- Snap installation success rate (target: >95%)
- Issue reports specific to snap installation (target: <5% of total issues)
- Snap Store ratings and reviews

### Operational Metrics
- Automated publishing success rate (target: 100%)
- Time from release tag to snap availability (target: <15 minutes)
- Snap build time in CI (target: <10 minutes)
- Snap package size (target: <50MB)

### User Experience Metrics
- Installation time from snap command to usable CLI (target: <2 minutes)
- Configuration migration success rate for pip-to-snap users
- User-reported setup complexity (qualitative feedback)

## Technical Constraints

### Snap Store Requirements
- Classic confinement requires manual review for first publication
- Snap name must be available and claimed in Snap Store
- Snap Store credentials required for automated publishing
- Publishing requires verified developer account

### Classic Confinement Limitations
- Some users/organizations may restrict classic snap installation
- Security-conscious users may prefer pip installation
- Documentation must explain classic confinement implications
- Classic snaps undergo stricter Snap Store review process

### Platform Constraints
- Snap primarily targets Ubuntu and Snap-enabled distributions
- Limited adoption outside Ubuntu ecosystem
- Some Linux distributions don't support snapd
- Enterprise environments may have snap restrictions

### Build System Constraints
- Snap builds must be reproducible in CI environment
- Build environment must support Poetry
- Python version must be compatible with snap base
- All dependencies must be available in snap build environment

### Compatibility Requirements
- Maintain feature parity with pip-installed version
- CLI behavior must be identical
- Configuration file format and location unchanged
- No snap-specific code changes to safeshell core

## AI Agent Guidance

### When Implementing PR #1 (Snapcraft Configuration)

1. **Start with Research**
   - Review official Snap documentation for Python applications
   - Study Python plugin documentation thoroughly
   - Examine example snaps using Poetry (if available)
   - Understand classic confinement implications

2. **Create snapcraft.yaml Incrementally**
   - Start with minimal configuration that builds
   - Add components progressively: base, confinement, apps, parts
   - Test build after each significant addition
   - Document any deviation from standard patterns

3. **Test Thoroughly Locally**
   - Build snap multiple times to ensure reproducibility
   - Test installation in clean environment
   - Validate every CLI command and option
   - Test configuration file creation and modification
   - Verify rule file loading and application
   - Test approval workflow end-to-end

4. **Document Snap-Specific Considerations**
   - Note any differences from pip installation
   - Document classic confinement requirement clearly
   - Provide troubleshooting guidance
   - Include local build instructions for contributors

### When Implementing PR #2 (Automated Publishing)

1. **Verify Prerequisites**
   - Confirm Snap Store account created
   - Verify application name registered
   - Ensure credentials generated and tested manually
   - Validate PR #1 merged and stable

2. **Configure Secrets Securely**
   - Add Snap Store token to GitHub Secrets
   - Document secret naming convention
   - Provide instructions for credential rotation
   - Never log or expose credentials

3. **Build Workflow Incrementally**
   - Start with basic build-only workflow
   - Add testing step to validate snap
   - Add conditional publishing logic
   - Implement beta channel testing
   - Add stable channel promotion

4. **Test Workflow Thoroughly**
   - Test with non-release commits (build only)
   - Test with test tag (beta channel)
   - Validate snap installs from Snap Store
   - Test stable channel publication
   - Verify badge displays correctly

### Common Patterns

#### Snap Build Testing Pattern
```yaml
- name: Build snap
  uses: snapcore/action-build@v1
  id: build

- name: Test snap installation
  run: |
    sudo snap install --dangerous --classic ${{ steps.build.outputs.snap }}
    safeshell --version
    sudo snap remove safeshell
```

#### Conditional Publishing Pattern
```yaml
- name: Publish to Snap Store
  if: startsWith(github.ref, 'refs/tags/v')
  uses: snapcore/action-publish@v1
  env:
    SNAPCRAFT_STORE_CREDENTIALS: ${{ secrets.SNAP_STORE_TOKEN }}
```

#### Poetry Export Pattern in snapcraft.yaml
```yaml
override-build: |
  pip install poetry
  poetry export -f requirements.txt --output requirements.txt --without-hashes
  poetry build
  pip install dist/*.whl
```

## Risk Mitigation

### Risk: Classic Confinement Review Delay
**Mitigation**:
- Submit snap early for review (even in beta)
- Clearly document classic confinement necessity
- Prepare detailed explanation for reviewers
- Have fallback plan to use pip installation if review blocked

### Risk: Snap Package Too Large
**Mitigation**:
- Monitor snap size during development
- Exclude unnecessary dependencies
- Use `--without dev` when exporting requirements
- Test on constrained bandwidth connections

### Risk: Poetry Integration Failure in Snap Build
**Mitigation**:
- Test Poetry export extensively locally
- Pin Poetry version in snap build
- Have fallback to manual requirements.txt if needed
- Document any Poetry-specific build issues

### Risk: GitHub Actions Publishing Failure
**Mitigation**:
- Test publishing workflow with beta tags first
- Implement comprehensive error handling
- Add Slack/email notifications for publishing failures
- Document manual publishing procedure as backup

### Risk: Snap Store Credentials Compromise
**Mitigation**:
- Use GitHub Secrets for credential storage
- Limit credential scope to publishing only
- Enable Snap Store account 2FA
- Document credential rotation procedure
- Monitor Snap Store account for unauthorized activity

### Risk: User Confusion Between Installation Methods
**Mitigation**:
- Document both methods clearly with use case guidance
- Recommend snap for Ubuntu desktop users
- Recommend pip for servers and non-Ubuntu systems
- Explain feature parity between methods
- Provide migration guidance between methods

## Future Enhancements

### Multi-Architecture Support
- Extend snap builds to support ARM architectures
- Test on Raspberry Pi and ARM-based servers
- Configure multi-arch builds in GitHub Actions

### Desktop Integration
- Add .desktop file for GUI launcher (if GUI features added)
- Integrate with system menus and search
- Add snap metadata for better Snap Store presentation

### Snap-Specific Features
- Leverage snap hooks for automatic shell profile configuration
- Use snap settings for configuration management
- Implement snap health checks
- Add snap-specific telemetry (opt-in)

### Alternative Snap Channels
- Use edge channel for development builds
- Use beta channel for release candidates
- Use candidate channel for pre-release testing
- Implement channel promotion workflow

### Snap Store Presence
- Create compelling Snap Store listing with screenshots
- Gather and showcase user reviews
- Optimize Snap Store search ranking
- Create video demo for Snap Store page

### Distribution Expansion
- Investigate Flatpak packaging as alternative
- Consider AppImage for universal Linux support
- Explore Debian/Ubuntu PPA as additional option
- Research Arch User Repository (AUR) submission

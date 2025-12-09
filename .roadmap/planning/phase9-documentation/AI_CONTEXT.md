# Documentation Site - AI Context

**Purpose**: AI agent context document for implementing Documentation Site

**Scope**: Comprehensive Read the Docs site with MkDocs Material theme, complete documentation coverage, and Mermaid architecture diagrams

**Overview**: Comprehensive context document for AI agents working on the Documentation Site feature.
    Establishes a professional documentation site using MkDocs Material theme, matching the quality and
    structure of the thai-lint project. Includes infrastructure setup, 14+ documentation pages covering
    all aspects of SafeShell, and 4 Mermaid architecture diagrams explaining system design and workflows.

**Dependencies**: Phase 1 (README), existing .ai/docs/ and .ai/howtos/ documentation, thai-lint docs as reference

**Exports**: Complete documentation site on Read the Docs, comprehensive user and developer guides, architecture diagrams

**Related**: PR_BREAKDOWN.md for implementation tasks, PROGRESS_TRACKER.md for current status

**Implementation**: MkDocs Material with Read the Docs hosting, progressive enhancement from infrastructure through advanced content

---

## Overview

The Documentation Site feature creates a comprehensive, professional documentation site for SafeShell using
MkDocs Material theme and Read the Docs hosting. This establishes SafeShell as a production-ready project
with documentation quality matching thai-lint standards.

The documentation site serves multiple audiences:
- **New Users**: Quick-start guide and installation instructions
- **Regular Users**: Configuration, CLI reference, rules guide
- **Developers**: Architecture, contributing guide, security model
- **AI Tools**: Integration guides for Claude Code and future tools

## Project Background

SafeShell currently has:
- A comprehensive README (Phase 1)
- Internal documentation in .ai/docs/ (PROJECT_CONTEXT.md, etc.)
- Internal howtos in .ai/howtos/ (CLI usage, rule writing, integrations)
- No public documentation site

The project is ready for a documentation site because:
- Core functionality is implemented and stable
- Claude Code integration is working
- Rule-based security model is mature
- Community usage is growing

## Feature Vision

The Documentation Site feature provides:

1. **Professional Documentation Platform**
   - MkDocs Material theme with modern design
   - Read the Docs hosting with automatic builds
   - Search functionality for easy discovery
   - Dark/light mode for user preference

2. **Comprehensive Content Coverage**
   - Getting started guide (5-minute setup)
   - Installation for all methods (pipx, pip, source)
   - Configuration reference with examples
   - CLI command documentation
   - Rules writing guide
   - Architecture documentation with diagrams

3. **Visual Architecture Documentation**
   - Command flow diagrams (human commands)
   - AI tool flow diagrams (Claude Code integration)
   - Approval workflow sequences
   - Component architecture overview

4. **Integration Documentation**
   - Claude Code setup and usage
   - Future AI tool integration patterns
   - Troubleshooting guides
   - Contributing guidelines

## Current Application Context

### Existing Documentation
- **README.md**: High-level overview, quick examples, basic setup
- **.ai/docs/PROJECT_CONTEXT.md**: Deep technical context for AI agents
- **.ai/howtos/**: Step-by-step guides for specific tasks
  - how-to-use-safeshell-cli.md
  - how-to-write-rules.md
  - how-to-integrate-with-claude-code.md

### Reference Implementation
The thai-lint project provides excellent patterns:
- **mkdocs.yml**: Material theme configuration
- **.readthedocs.yaml**: RTD build configuration
- **docs/**: Comprehensive documentation pages
- **Navigation structure**: Logical organization

### Documentation Gaps
- No searchable documentation site
- Content scattered across .ai/ directory
- No architecture diagrams
- No comprehensive CLI reference
- No troubleshooting guide
- No contributing guide

## Target Architecture

### Core Components

1. **MkDocs Infrastructure**
   - mkdocs.yml: Site configuration, theme, navigation
   - .readthedocs.yaml: RTD build configuration
   - docs/requirements.txt: Python dependencies
   - Material theme with customization

2. **Documentation Pages**
   - **Getting Started**: index.md, quick-start.md, installation.md
   - **Configuration**: configuration.md with complete reference
   - **Reference**: cli-reference.md, rules-guide.md, architecture.md
   - **Security**: security.md, performance.md
   - **Integration**: integrations/claude-code.md, integrations/future-tools.md
   - **Advanced**: troubleshooting.md, contributing.md
   - **Meta**: changelog.md

3. **Architecture Diagrams (Mermaid)**
   - Command flow: Human → Wrapper → Daemon → Rules → Shell
   - AI tool flow: Claude Code → Hook → Daemon → Rules → Shell
   - Approval workflow: State diagram of approval process
   - Component architecture: System component relationships

4. **Theme Features**
   - Navigation: tabs, sections, expand, top
   - Search: suggest, highlight
   - Code: copy, syntax highlighting
   - Content: admonitions, tabbed sections
   - Color: deep-orange theme (security/safety)
   - Modes: light/dark toggle

### User Journey

#### New User Journey
1. **Discovery**: Land on index.md, understand value proposition
2. **Quick Start**: Follow quick-start.md for 5-minute setup
3. **Configuration**: Review configuration.md for basic rules
4. **Usage**: Check CLI reference for commands
5. **Advanced**: Write custom rules using rules-guide.md

#### Developer Journey
1. **Understanding**: Read architecture.md with diagrams
2. **Setup**: Follow contributing.md for development setup
3. **Integration**: Review integrations/ for tool integration
4. **Security**: Study security.md for security model
5. **Contributing**: Submit PRs following contributing.md

#### AI Tool User Journey
1. **Integration**: Follow integrations/claude-code.md
2. **Configuration**: Set up rules for AI tool context
3. **Testing**: Verify integration with test commands
4. **Usage**: Use SafeShell with Claude Code
5. **Troubleshooting**: Check troubleshooting.md for issues

## Key Decisions Made

### Decision 1: MkDocs Material Theme
**Choice**: Use MkDocs Material theme matching thai-lint

**Rationale**:
- Proven success in thai-lint project
- Modern, professional design
- Excellent search functionality
- Built-in Mermaid support
- Easy to maintain and customize
- Great mobile experience

**Alternatives Considered**:
- Sphinx: More complex, Python-focused
- Docusaurus: React-based, unnecessary complexity
- GitBook: Commercial, less flexible

### Decision 2: Read the Docs Hosting
**Choice**: Host on Read the Docs (readthedocs.io)

**Rationale**:
- Free for open source projects
- Automatic builds from GitHub
- Version management built-in
- Search indexing included
- SSL certificates automatic
- Proven reliability

**Alternatives Considered**:
- GitHub Pages: Less features, no automatic builds
- Self-hosted: Unnecessary maintenance burden
- GitLab Pages: Project on GitHub

### Decision 3: Mermaid for Diagrams
**Choice**: Use Mermaid for architecture diagrams

**Rationale**:
- Text-based, version-controllable
- Renders in both GitHub and MkDocs
- Easy to update and maintain
- No external tools needed
- Good-looking output

**Alternatives Considered**:
- Draw.io: Binary files, harder to maintain
- PlantUML: Additional dependency
- Manual images: Not version-controllable

### Decision 4: Deep Orange Color Theme
**Choice**: Use deep-orange as primary/accent color

**Rationale**:
- Represents security and safety
- Distinct from thai-lint (indigo)
- High contrast and readable
- Warm, approachable tone

### Decision 5: 4-PR Breakdown
**Choice**: Split documentation into 4 PRs

**Rationale**:
- PR1 (Infrastructure): Get foundation working
- PR2 (Core Pages): Essential user documentation
- PR3 (Reference): Technical depth with diagrams
- PR4 (Integration): Advanced topics and integrations
- Each PR is reviewable and testable independently

## Integration Points

### With Existing Features

1. **README.md Integration**
   - index.md links to README for GitHub visitors
   - Quick-start expands on README examples
   - Maintains consistency in messaging

2. **.ai/docs/ Integration**
   - Consolidate PROJECT_CONTEXT.md into architecture.md
   - Extract security model to security.md
   - Reference .ai/docs/ for AI agent context

3. **.ai/howtos/ Integration**
   - Expand how-to-use-safeshell-cli.md into cli-reference.md
   - Expand how-to-write-rules.md into rules-guide.md
   - Expand how-to-integrate-with-claude-code.md into integrations/claude-code.md

### With Documentation Tools

1. **MkDocs Integration**
   - Use mkdocs.yml for configuration
   - Use Material theme extensions
   - Enable all useful features

2. **Read the Docs Integration**
   - Use .readthedocs.yaml for builds
   - Configure Python version and dependencies
   - Enable version management

3. **GitHub Integration**
   - Edit links point to GitHub source
   - Repository links in theme
   - Automatic builds on commits

## Success Metrics

### Technical Success
- Documentation builds without errors on RTD
- All Mermaid diagrams render correctly
- All code examples are valid and tested
- Search functionality works well
- Mobile experience is good
- Load time is fast (<3s)

### Content Success
- Quick-start enables 5-minute setup
- Users can write custom rules from rules-guide
- Architecture is clear from diagrams
- Claude Code integration is straightforward
- Troubleshooting covers common issues

### User Success
- New users can get started quickly
- Developers can contribute easily
- AI tools can integrate successfully
- Community provides positive feedback
- Documentation stays up-to-date

## Technical Constraints

### MkDocs Constraints
- Must use Python 3.11+ for RTD
- Limited to MkDocs Material features
- Mermaid diagrams must be in superfences
- Navigation depth limited to 2-3 levels

### Read the Docs Constraints
- Build time limits (10 minutes)
- Public repository required for free tier
- Limited concurrent builds
- Version limit (5 active versions)

### Content Constraints
- Must use atemporal language
- All examples must be tested
- All links must be valid
- No unreleased features documented
- Diagrams must be accurate

### Performance Constraints
- Page load time <3 seconds
- Search response time <500ms
- Build time <30 seconds
- Image sizes optimized

## AI Agent Guidance

### When Setting Up Infrastructure (PR1)
1. **Start with Reference**: Copy thai-lint configurations as starting point
2. **Customize**: Update site name, description, colors to SafeShell
3. **Test Locally**: Run `mkdocs serve` to verify configuration
4. **Verify Extensions**: Ensure all markdown extensions work
5. **Check Theme Features**: Test navigation, search, code copy

### When Writing Documentation Pages (PR2, PR3, PR4)
1. **Read Existing Content**: Review .ai/docs/ and .ai/howtos/
2. **Expand and Enhance**: Add examples, explanations, context
3. **Test Examples**: Run all code examples to verify they work
4. **Use Atemporal Language**: No "will", "coming soon", "future"
5. **Add Navigation**: Update mkdocs.yml nav for new pages

### When Creating Diagrams (PR3)
1. **Use Mermaid**: Text-based diagrams in code blocks
2. **Test Rendering**: Verify diagrams render in `mkdocs serve`
3. **Keep Simple**: Clear, focused diagrams
4. **Add Context**: Explain diagrams in surrounding text
5. **Verify Accuracy**: Ensure diagrams match actual implementation

### Common Patterns

#### Page Structure Pattern
```markdown
# Page Title

**Brief description of what this page covers**

## Overview
High-level introduction and context

## [Main Content Sections]
Detailed content with examples

## Examples
Practical examples with code blocks

## See Also
Links to related pages
```

#### Code Example Pattern
```markdown
Example description:

​```bash
# Command with explanation
safeshell install --config ~/.config/safeshell/rules.yaml
​```

Expected output:
​```
[Output example]
​```
```

#### Admonition Pattern
```markdown
!!! note "Important Note"
    Key information that users should know

!!! warning "Warning"
    Something that could go wrong

!!! tip "Pro Tip"
    Best practice or optimization
```

## Risk Mitigation

### Risk: Documentation Becomes Stale
**Mitigation**:
- Document in sync with code changes
- Include documentation updates in PR requirements
- Periodic documentation review
- Community feedback mechanism

### Risk: Diagrams Become Inaccurate
**Mitigation**:
- Review diagrams when architecture changes
- Keep diagrams simple and high-level
- Use Mermaid for easy updates
- Version control all diagrams

### Risk: Examples Stop Working
**Mitigation**:
- Test all examples before documenting
- Include examples in test suite
- Regular validation of documented commands
- CI check for broken examples

### Risk: Poor Discoverability
**Mitigation**:
- Logical navigation structure
- Comprehensive search coverage
- Cross-linking between related pages
- Clear page hierarchy

### Risk: RTD Build Failures
**Mitigation**:
- Pin dependency versions
- Test builds locally first
- Monitor RTD build status
- Keep configuration simple

## Future Enhancements

### Version Documentation
- Support multiple versions (stable, latest, specific)
- Version switcher in theme
- Separate docs for each major version
- Migration guides between versions

### Interactive Examples
- Embedded terminal examples
- Interactive configuration builder
- Live rule testing
- Example repository

### Video Content
- Quick-start video walkthrough
- Architecture explanation video
- Integration setup videos
- Troubleshooting screencasts

### API Documentation
- Auto-generated API reference
- Python API documentation
- Module documentation
- Code examples from docstrings

### Internationalization
- Multi-language support
- Translation workflow
- Language switcher
- Community translations

### Analytics
- Page view tracking
- Search analytics
- User journey analysis
- Popular content identification

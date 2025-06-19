# System Documentation & Maintenance Rules

## Core Documentation Principles

### 1. Documentation Completeness

**All system components must be fully documented in this folder (`AI LATEST OVERVIEW`).**

- **Agents**: Every agent must be listed with its purpose, capabilities, and communication patterns
- **Workflows**: All process flows must be documented with clear diagrams
- **Interfaces**: All communication interfaces must be specified with message formats
- **Dependencies**: All dependencies between components must be explicitly documented

### 2. Documentation Accuracy

**Documentation must reflect the current state of the system at all times.**

- Documentation must be updated BEFORE implementing changes
- Outdated documentation is considered a critical bug
- Regular documentation reviews should be conducted to ensure accuracy
- Version numbers should be included in documentation headers

### 3. Documentation Clarity

**Documentation must be clear, organized, and accessible to both humans and AI.**

- Use consistent formatting and terminology across all documents
- Include diagrams and visual aids for complex systems
- Organize information hierarchically with clear section headers
- Provide cross-references between related documents

## Specific Documentation Requirements

### For System Architecture Changes

1. **Update WORKFLOW.md** with any changes to the system flow, component interactions, or architecture
2. **Update the architecture diagram** to reflect the current system structure
3. **Document any new dependencies** between components
4. **Update startup sequence information** if component dependencies change

### For Agent Changes

1. **Update AGENTS.md** when adding, removing, or modifying agents
   - Keep the agent list current and accurate
   - Document agent dependencies and requirements
   - Specify hardware requirements (GPU, memory, etc.)

2. **Update CAPABILITIES.md** with detailed information about agent capabilities
   - Document all API endpoints and message formats
   - Specify performance characteristics and limitations
   - Include examples of typical usage patterns

### For Communication Changes

1. **Update ROUTING.md** when changing communication patterns
   - Document all port assignments and network topology
   - Specify message formats and protocols
   - Detail error handling and recovery mechanisms

2. **Update distributed_config.json** to reflect current network configuration
   - Keep port assignments consistent across documentation
   - Document any changes to timeout or retry settings

## Change Management Process

### Before Making Changes

1. **Review current documentation** to understand the existing system
2. **Plan documentation updates** alongside code changes
3. **Consider impact** on other system components

### When Implementing Changes

1. **Update documentation first** before implementing code changes
2. **Follow the dependency order** when updating components
3. **Test documentation accuracy** by following procedures

### After Implementing Changes

1. **Verify documentation completeness** across all affected files
2. **Test system behavior** against documented expectations
3. **Review cross-references** between documentation files

## Critical Rules

1. **Any undocumented change is considered a bug** and must be fixed immediately
2. **Documentation must be bilingual** (English and Filipino) where appropriate
3. **AI assistants must always check this folder first** before making system recommendations
4. **Port assignments must be consistent** across all documentation and configuration files
5. **Agent dependencies must be explicitly documented** to ensure proper startup sequence

---

## Documentation Structure

### Core Files

- **WORKFLOW.md**: Overall system architecture and process flows
- **CAPABILITIES.md**: Detailed agent capabilities and technical implementations
- **ROUTING.md**: Communication patterns, protocols, and network topology
- **AGENTS.md**: Comprehensive list of PC2 agents with specifications
- **RULES.md**: This file - documentation standards and maintenance rules

### Supporting Files

- **distributed_config.json**: Network configuration and agent assignments
- **AUTO_FIX_CAPABILITIES.md**: Details of the auto-fixing system
- **MEMORY_OPTIMIZATION_GUIDE.md**: Memory management best practices

---

**Purpose:**
To ensure that anyone (human or AI) can quickly understand the complete structure, agents, and flow of the distributed voice assistant system. Proper documentation enables efficient maintenance, troubleshooting, and enhancement of the system.

**Layunin:**
Para mabilis maintindihan ng kahit sino (AI o tao) ang buong structure, agents, at flow ng distributed voice assistant system. Ang tamang dokumentasyon ay nagbibigay-daan sa mabisang pagpapanatili, pag-troubleshoot, at pagpapahusay ng system.

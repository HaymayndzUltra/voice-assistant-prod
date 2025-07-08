# Agent Discovery and Source of Truth Management

This document explains how to use the agent discovery tools to maintain an accurate source of truth for your AI system.

## Overview

The source of truth for your AI system has gone missing, but you can rebuild it using the agent discovery tools. These tools scan your codebase to identify all agents, their dependencies, and their configurations, allowing you to recreate a comprehensive source of truth file.

## Available Tools

The following scripts have been created to help you discover and document your active agents:

1. **discover_active_agents.py** - Scans the codebase to identify all agents
2. **generate_agents_report.py** - Creates a markdown report of all discovered agents
3. **rebuild_source_of_truth.py** - Rebuilds the source of truth YAML file
4. **run_agent_discovery.sh** - Shell script that runs all the above scripts in sequence

## How to Use

### Running the Discovery Process

The simplest way to run the entire discovery process is to use the shell script:

```bash
chmod +x scripts/run_agent_discovery.sh
./scripts/run_agent_discovery.sh
```

This will:
1. Scan your codebase for agents
2. Generate a JSON report of all discovered agents
3. Create a markdown report with visualizations
4. Rebuild the source of truth YAML file
5. Create a backup of your existing source of truth file (if one exists)

All outputs will be saved to the `analysis_output` directory.

### Manual Process

If you prefer to run the scripts individually:

1. **Discover agents**:
   ```bash
   python scripts/discover_active_agents.py --output active_agents_report.json
   ```

2. **Generate markdown report**:
   ```bash
   python scripts/generate_agents_report.py --input active_agents_report.json --output active_agents_report.md
   ```

3. **Rebuild source of truth**:
   ```bash
   python scripts/rebuild_source_of_truth.py --input active_agents_report.json --output source_of_truth.yaml
   ```

## Understanding the Output

### JSON Report

The JSON report (`active_agents_report.json`) contains detailed information about all discovered agents, including:
- Agent names
- File paths
- Ports
- Health check ports
- Error bus integration status
- Dependencies
- Machine assignments

### Markdown Report

The markdown report (`active_agents_report.md`) provides a human-readable overview of all agents, including:
- Summary statistics
- Dependency graph visualization
- Tables of agents by machine
- Detailed information about each agent
- Recommendations for improvements

### Source of Truth YAML

The rebuilt source of truth file (`source_of_truth.yaml`) contains a structured configuration for your AI system:
- Lists of agents for each machine
- Network configuration
- Error management settings
- Health monitoring settings

## Applying the New Source of Truth

After reviewing the generated source of truth file, you can apply it to your system:

```bash
# Make a backup of the current file (if it exists)
cp pc2_code/_pc2mainpcSOT.yaml pc2_code/_pc2mainpcSOT.yaml.bak

# Copy the new source of truth file
cp analysis_output/source_of_truth.yaml pc2_code/_pc2mainpcSOT.yaml
```

## Maintaining the Source of Truth

To keep your source of truth up to date:

1. Run the discovery process regularly, especially after adding or removing agents
2. Review the generated reports to ensure all agents are properly configured
3. Make manual adjustments to the source of truth file as needed
4. Keep backups of previous versions

## Troubleshooting

### Missing Agents

If some agents are not being discovered:
- Check if they follow the expected naming conventions
- Ensure they inherit from BaseAgent or have "Agent" in their class name
- Verify they are located in one of the scanned directories

### Incorrect Dependencies

If dependencies are not correctly identified:
- Check if they are declared in a standard format (e.g., `dependencies = ["AgentA", "AgentB"]`)
- Manually add missing dependencies to the source of truth file

### Port Conflicts

If multiple agents are using the same ports:
- Review the markdown report to identify conflicts
- Modify agent configurations to use unique ports
- Update the source of truth file accordingly

## Conclusion

These agent discovery tools provide a reliable way to maintain an accurate source of truth for your AI system. By regularly running the discovery process and reviewing the outputs, you can ensure that your system configuration remains up to date and consistent. 
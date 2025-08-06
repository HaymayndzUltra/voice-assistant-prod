#!/usr/bin/env python3
"""
Add HEALTHCHECK directives to Dockerfiles missing them
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent

def get_agent_port(dockerfile_path: pathlib.Path) -> str:
    """Extract the port number from Dockerfile or agent configuration"""
    content = dockerfile_path.read_text()
    
    # Look for EXPOSE directive
    expose_match = re.search(r'EXPOSE\s+(\d+)', content)
    if expose_match:
        return expose_match.group(1)
    
    # Default health check port for agents
    return "8080"

def has_healthcheck(dockerfile_path: pathlib.Path) -> bool:
    """Check if Dockerfile already has a HEALTHCHECK directive"""
    content = dockerfile_path.read_text()
    return "HEALTHCHECK" in content

def add_healthcheck_to_dockerfile(dockerfile_path: pathlib.Path) -> bool:
    """Add HEALTHCHECK directive to a Dockerfile"""
    if has_healthcheck(dockerfile_path):
        return False
    
    content = dockerfile_path.read_text()
    lines = content.split('\n')
    
    # Find the best place to insert HEALTHCHECK (before CMD/ENTRYPOINT)
    insert_idx = len(lines)
    for i, line in enumerate(lines):
        if line.strip().startswith(('CMD', 'ENTRYPOINT')):
            insert_idx = i
            break
    
    # Get the appropriate port for health check
    port = get_agent_port(dockerfile_path)
    
    # Create health check directive
    healthcheck_lines = [
        "",
        "# Health check",
        f"HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \\",
        f"  CMD curl -f http://localhost:{port}/health || exit 1"
    ]
    
    # Insert health check before CMD/ENTRYPOINT
    for i, line in enumerate(healthcheck_lines):
        lines.insert(insert_idx + i, line)
    
    # Write back to file
    dockerfile_path.write_text('\n'.join(lines))
    return True

def main():
    """Main function to add health checks to all Dockerfiles"""
    print("Adding HEALTHCHECK directives to Dockerfiles...")
    
    docker_dir = ROOT / "docker"
    added_count = 0
    skipped_count = 0
    
    for agent_dir in docker_dir.iterdir():
        if not agent_dir.is_dir() or agent_dir.name.startswith('.'):
            continue
        
        dockerfile = agent_dir / "Dockerfile"
        if not dockerfile.exists():
            continue
        
        print(f"Checking {agent_dir.name}...")
        
        if add_healthcheck_to_dockerfile(dockerfile):
            print(f"  ✓ Added HEALTHCHECK to {agent_dir.name}")
            added_count += 1
        else:
            print(f"  - {agent_dir.name} already has HEALTHCHECK")
            skipped_count += 1
    
    print(f"\n=== Summary ===")
    print(f"Added HEALTHCHECK to {added_count} Dockerfiles")
    print(f"Skipped {skipped_count} Dockerfiles (already had HEALTHCHECK)")
    print(f"Total processed: {added_count + skipped_count}")

if __name__ == "__main__":
    main()
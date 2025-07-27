#!/usr/bin/env python3
"""
Unified System Main Entry Point
"""

import os
import sys
import click
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('UnifiedSystem')

@click.group()
@click.version_option(version='1.0.0')
def cli():
    """Unified AI System - Production Ready"""
    pass

@cli.command()
@click.option('--profile', default='core', 
              type=click.Choice(['core', 'vision', 'learning', 'tutoring', 'full']),
              help='Deployment profile to use')
@click.option('--config', default='config/startup_config.yaml',
              help='Path to configuration file')
@click.option('--dry-run', is_flag=True,
              help='Validate configuration without starting')
def start(profile, config, dry_run):
    """Start the unified system with specified profile"""
    
    # Set profile environment variable
    os.environ['PROFILE'] = profile
    
    logger.info(f"Starting Unified System with profile: {profile}")
    
    if dry_run:
        logger.info("Running in dry-run mode - validating configuration only")
        from scripts.maintenance.validate_config import main as validate_main
        sys.argv = ['validate_config.py', config]
        return validate_main()
    
    # Launch the system
    from scripts.deployment.launch import ProfileBasedLauncher
    launcher = ProfileBasedLauncher()
    sys.exit(launcher.run())

@cli.command()
def test():
    """Run system tests"""
    logger.info("Running system tests...")
    
    # Run integration tests
    import subprocess
    result = subprocess.run([
        sys.executable, 'tests/integration/test_phase2_integration.py'
    ])
    
    if result.returncode != 0:
        logger.error("Tests failed!")
        sys.exit(1)
    
    logger.info("All tests passed!")

@cli.command()
def chaos():
    """Run chaos testing"""
    logger.info("Running chaos tests...")
    
    from scripts.testing.chaos_test import main
    sys.exit(main())

@cli.command()
def benchmark():
    """Run routing benchmark"""
    logger.info("Running routing benchmark...")
    
    from scripts.testing.routing_benchmark_simple import run_benchmark
    success = run_benchmark()
    sys.exit(0 if success else 1)

@cli.command()
@click.option('--agent', required=True, help='Agent name to check')
def health(agent):
    """Check health of specific agent"""
    import requests
    
    # Get agent port from config
    # This is simplified - in production would read from config
    base_port = 7200
    health_port = base_port + 1000
    
    try:
        response = requests.get(f"http://localhost:{health_port}/health", timeout=5)
        if response.status_code == 200:
            logger.info(f"{agent} is healthy")
            click.echo(response.json())
        else:
            logger.error(f"{agent} health check failed: {response.status_code}")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to check {agent} health: {e}")
        sys.exit(1)

@cli.command()
def status():
    """Show system status"""
    logger.info("Checking system status...")
    
    # Check ObservabilityHub
    import requests
    try:
        response = requests.get("http://localhost:9000/health/summary", timeout=5)
        if response.status_code == 200:
            data = response.json()
            click.echo("\nSystem Status:")
            click.echo(f"  Profile: {os.getenv('PROFILE', 'unknown')}")
            click.echo(f"  Agents Running: {data.get('agents_running', 0)}")
            click.echo(f"  System Health: {data.get('health_score', 0):.2%}")
            click.echo(f"  Memory Usage: {data.get('memory_mb', 0)} MB")
        else:
            logger.warning("ObservabilityHub not responding")
    except:
        logger.error("System appears to be offline")
        sys.exit(1)

@cli.command()
def stop():
    """Stop the unified system"""
    logger.info("Stopping unified system...")
    
    import subprocess
    subprocess.run(['pkill', '-f', 'launch.py'])
    subprocess.run(['pkill', '-f', 'unified'])
    
    logger.info("System stopped")

if __name__ == '__main__':
    cli()
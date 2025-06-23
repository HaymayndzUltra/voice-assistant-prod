#!/usr/bin/env python3
"""
ZMQ CURVE Certificate Generator
------------------------------
Generates CURVE certificate keypairs for ZMQ secure authentication
between client and server components.
"""

import os
import sys
import zmq.auth
from pathlib import Path
import logging
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("ZMQCertGenerator")

def generate_certificates(certificates_dir: Path, force: bool = False) -> None:
    """
    Generate server and client CURVE certificate files.
    
    Args:
        certificates_dir: Directory to store certificates
        force: If True, will overwrite existing certificates
    """
    # Create certificates directory
    certificates_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if certificates already exist
    server_public_key_file = certificates_dir / "server.key"
    client_public_key_file = certificates_dir / "client.key"
    
    if not force and (server_public_key_file.exists() or client_public_key_file.exists()):
        logger.warning(f"Certificates already exist in {certificates_dir}.")
        logger.warning("Use --force to overwrite existing certificates.")
        return
    
    logger.info(f"Generating new certificates in {certificates_dir}")
    
    # Generate server key pair
    server_public_file, server_secret_file = zmq.auth.create_certificates(
        str(certificates_dir), "server"
    )
    logger.info(f"Created server certificates: {server_public_file}, {server_secret_file}")
    
    # Generate client key pair
    client_public_file, client_secret_file = zmq.auth.create_certificates(
        str(certificates_dir), "client"
    )
    logger.info(f"Created client certificates: {client_public_file}, {client_secret_file}")
    
    # Set appropriate permissions - secret keys should be readable only by owner
    os.chmod(server_secret_file, 0o600)
    os.chmod(client_secret_file, 0o600)
    
    logger.info("Certificate generation complete.")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate ZMQ CURVE certificates")
    parser.add_argument(
        "--dir", 
        type=Path, 
        default=Path(__file__).resolve().parent.parent / "certificates",
        help="Directory to store certificates (default: project_root/certificates)"
    )
    parser.add_argument(
        "--force", 
        action="store_true",
        help="Overwrite existing certificates"
    )
    
    args = parser.parse_args()
    
    print(f"Generating ZMQ certificates in: {args.dir}")
    generate_certificates(args.dir, args.force)
    print(f"Certificate generation {'completed' if args.dir.exists() else 'failed'}")
    
    # Display next steps
    print("\n--- Next Steps ---")
    print("1. Set environment variable to enable secure ZMQ:")
    print("   export SECURE_ZMQ=1")
    print("2. Make sure both client and server have access to these certificates")
    print("3. Restart all agents and services") 
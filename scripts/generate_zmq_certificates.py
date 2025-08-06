#!/usr/bin/env python3
"""
Generate ZMQ CURVE Certificates
------------------------------
This script generates ZMQ CURVE certificates for secure communication.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from common.utils.log_setup import configure_logging

# Add project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging
logger = configure_logging(__name__)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("CertGenerator")

def generate_certificates(cert_dir: str, server_name: str = "server", client_name: str = "client") -> bool:
    """
    Generate ZMQ CURVE certificates.
    
    Args:
        cert_dir: Directory to store certificates
        server_name: Name for server certificate
        client_name: Name for client certificate
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        import zmq.auth
        
        # Create directory if it doesn't exist
        cert_dir_path = Path(cert_dir)
        cert_dir_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Generating certificates in {cert_dir_path.absolute()}")
        
        # Generate server certificates
        server_public_file, server_secret_file = zmq.auth.create_certificates(
            cert_dir, server_name
        )
        logger.info(f"Server certificates generated: {server_public_file}, {server_secret_file}")
        
        # Generate client certificates
        client_public_file, client_secret_file = zmq.auth.create_certificates(
            cert_dir, client_name
        )
        logger.info(f"Client certificates generated: {client_public_file}, {client_secret_file}")
        
        # Set permissions
        try:
            os.chmod(server_secret_file, 0o600)
            os.chmod(client_secret_file, 0o600)
            logger.info("Certificate permissions set to 0600")
        except Exception as e:
            logger.warning(f"Failed to set certificate permissions: {e}")
        
        return True
        
    except ImportError:
        logger.error("PyZMQ not installed or doesn't support auth. Install with 'pip install pyzmq'")
        return False
    except Exception as e:
        logger.error(f"Error generating certificates: {e}")
        return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Generate ZMQ CURVE certificates")
    parser.add_argument("--dir", "-d", default="certificates", help="Directory to store certificates")
    parser.add_argument("--server", "-s", default="server", help="Server certificate name")
    parser.add_argument("--client", "-c", default="client", help="Client certificate name")
    args = parser.parse_args()
    
    if generate_certificates(args.dir, args.server, args.client):
        logger.info("Certificate generation successful")
        return 0
    else:
        logger.error("Certificate generation failed")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
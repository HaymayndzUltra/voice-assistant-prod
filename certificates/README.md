# Certificates Directory

## Security Notice
🚨 **NEVER commit actual certificates or private keys to git!**

## Required Files (Not in Git)
Create these files locally:

```bash
# Generate ZeroMQ CURVE certificates
python -c "
import zmq.auth
zmq.auth.create_certificates('.', 'server')
zmq.auth.create_certificates('.', 'client')
"
```

## Environment Variables
Set these in your environment:
```bash
export ZMQ_SERVER_SECRET_KEY="path/to/server.key_secret"
export ZMQ_CLIENT_SECRET_KEY="path/to/client.key_secret"
export ZMQ_SERVER_PUBLIC_KEY="path/to/server.key"
export ZMQ_CLIENT_PUBLIC_KEY="path/to/client.key"
```

## Files Created:
- `server.key_secret` - Server private key (NEVER commit)
- `server.key` - Server public key 
- `client.key_secret` - Client private key (NEVER commit)
- `client.key` - Client public key 
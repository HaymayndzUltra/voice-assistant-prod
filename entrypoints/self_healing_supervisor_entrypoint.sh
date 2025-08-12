#!/bin/bash
# Entrypoint for Self Healing Supervisor
set -e

# Load machine profile
if [ -f /etc/machine-profile.json ]; then
    export $(cat /etc/machine-profile.json | jq -r 'to_entries[] | "\(.key)=\(.value)"')
fi

# Start service
exec python -m self_healing_supervisor.app

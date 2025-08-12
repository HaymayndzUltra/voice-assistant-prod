#!/bin/bash
# Entrypoint for Real Time Audio Pipeline
set -e

# Load machine profile
if [ -f /etc/machine-profile.json ]; then
    export $(cat /etc/machine-profile.json | jq -r 'to_entries[] | "\(.key)=\(.value)"')
fi

# Start service
exec python -m real_time_audio_pipeline.app

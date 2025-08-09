#!/usr/bin/env bash
set -euo pipefail

log() { echo "[$(date --iso-8601=seconds)] $*"; }

# Enable mock mode if no audio device present
if [ ! -d "/dev/snd" ] || [ -z "$(ls -A /dev/snd 2>/dev/null)" ]; then
  log "🎯 Running in audio mock mode (no hardware devices)"
  export RTAP_AUDIO_MOCK=true
fi

# Signal to the system that RTAP is authoritative; legacy agents must be gated by RTAP_ENABLED
export RTAP_AUTHORITY=true

exec python3 -m real_time_audio_pipeline.app

#!/bin/bash
# Scheduled Network Scanner Service
# Runs every 10 minutes

cd "$(dirname "$0")"
source venv/bin/activate
python3 -m app.services.scheduled_network_scan "$@"

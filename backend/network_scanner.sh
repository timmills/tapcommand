#!/bin/bash
# Standalone Network Scanner Service
# Scans network and updates database with discovered devices

cd "$(dirname "$0")"
source venv/bin/activate

# Run the Python scanner
python3 -m app.services.standalone_network_scanner "$@"

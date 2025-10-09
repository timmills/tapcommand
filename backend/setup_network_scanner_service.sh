#!/bin/bash
# Setup script for network scanner service on local machine

set -e

echo "🔧 Setting up network scanner service..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (use sudo)"
    exit 1
fi

# Install nmap if not present
if ! command -v nmap &> /dev/null; then
    echo "📦 Installing nmap..."
    apt-get update
    apt-get install -y nmap
fi

# Variables
INSTALL_DIR="/home/coastal/smartvenue"
VENV_PATH="$INSTALL_DIR/venv"
APP_USER="coastal"
SUBNET="192.168.101"

echo "📝 Creating systemd service..."

# Create systemd service file
cat > /etc/systemd/system/smartvenue-scanner.service << EOF
[Unit]
Description=SmartVenue Network Scanner
After=network.target smartvenue-backend.service

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$INSTALL_DIR/backend
Environment="PATH=$VENV_PATH/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$VENV_PATH/bin/python -m app.services.scheduled_network_scan --subnet $SUBNET --interval 10
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

echo "🔄 Reloading systemd..."
systemctl daemon-reload

echo "▶️  Starting service..."
systemctl enable smartvenue-scanner.service
systemctl start smartvenue-scanner.service

echo "📊 Service status:"
systemctl status smartvenue-scanner.service --no-pager

echo ""
echo "✅ Network scanner service installed and started!"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status smartvenue-scanner   - Check service status"
echo "  sudo systemctl stop smartvenue-scanner     - Stop service"
echo "  sudo systemctl start smartvenue-scanner    - Start service"
echo "  sudo systemctl restart smartvenue-scanner  - Restart service"
echo "  sudo journalctl -u smartvenue-scanner -f   - View live logs"

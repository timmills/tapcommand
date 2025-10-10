#!/bin/bash
# Install TapCommand Network Scanner as a systemd service

echo "Installing TapCommand Network Scanner Service..."

# Copy service file to systemd
sudo cp tapcommand-network-scanner.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable tapcommand-network-scanner.service

# Start the service
sudo systemctl start tapcommand-network-scanner.service

# Check status
echo ""
echo "Service installed and started!"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status tapcommand-network-scanner   # Check status"
echo "  sudo systemctl stop tapcommand-network-scanner     # Stop service"
echo "  sudo systemctl start tapcommand-network-scanner    # Start service"
echo "  sudo systemctl restart tapcommand-network-scanner  # Restart service"
echo "  sudo journalctl -u tapcommand-network-scanner -f   # View logs"
echo ""
sudo systemctl status tapcommand-network-scanner

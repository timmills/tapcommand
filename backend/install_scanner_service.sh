#!/bin/bash
# Install SmartVenue Network Scanner as a systemd service

echo "Installing SmartVenue Network Scanner Service..."

# Copy service file to systemd
sudo cp smartvenue-network-scanner.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable smartvenue-network-scanner.service

# Start the service
sudo systemctl start smartvenue-network-scanner.service

# Check status
echo ""
echo "Service installed and started!"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status smartvenue-network-scanner   # Check status"
echo "  sudo systemctl stop smartvenue-network-scanner     # Stop service"
echo "  sudo systemctl start smartvenue-network-scanner    # Start service"
echo "  sudo systemctl restart smartvenue-network-scanner  # Restart service"
echo "  sudo journalctl -u smartvenue-network-scanner -f   # View logs"
echo ""
sudo systemctl status smartvenue-network-scanner

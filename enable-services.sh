#!/bin/bash

echo "Installing TapCommand systemd services..."

# Copy service files
echo "Copying service files to /etc/systemd/system/..."
cp /home/coastal/tapcommand/deploy/systemd/tapcommand-backend.service /etc/systemd/system/
cp /home/coastal/tapcommand/deploy/systemd/tapcommand-scanner.service /etc/systemd/system/

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable services
echo "Enabling services to start on boot..."
systemctl enable tapcommand-backend.service
systemctl enable tapcommand-scanner.service

# Start services
echo "Starting services..."
systemctl start tapcommand-backend.service
systemctl start tapcommand-scanner.service

# Wait a moment for services to start
sleep 2

# Check status
echo ""
echo "=== Backend Service Status ==="
systemctl status tapcommand-backend.service --no-pager

echo ""
echo "=== Scanner Service Status ==="
systemctl status tapcommand-scanner.service --no-pager

echo ""
echo "Services installed and started!"
echo ""
echo "Useful commands:"
echo "  View backend logs:  journalctl -u tapcommand-backend.service -f"
echo "  View scanner logs:  journalctl -u tapcommand-scanner.service -f"
echo "  Restart backend:    systemctl restart tapcommand-backend.service"
echo "  Restart scanner:    systemctl restart tapcommand-scanner.service"

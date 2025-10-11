#!/bin/bash

echo "Updating TapCommand services..."

# Stop services
echo "Stopping services..."
systemctl stop tapcommand-scanner.service
systemctl stop tapcommand-backend.service

# Copy updated service files
echo "Copying updated service files..."
cp /home/coastal/tapcommand/deploy/systemd/tapcommand-backend.service /etc/systemd/system/
cp /home/coastal/tapcommand/deploy/systemd/tapcommand-scanner.service /etc/systemd/system/

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload

# Start services
echo "Starting services..."
systemctl start tapcommand-backend.service
systemctl start tapcommand-scanner.service

# Wait for services to start
sleep 3

# Show status
echo ""
echo "=== Backend Service Status ==="
systemctl status tapcommand-backend.service --no-pager -l

echo ""
echo "=== Scanner Service Status ==="
systemctl status tapcommand-scanner.service --no-pager -l

echo ""
echo "Done! Services updated and restarted."

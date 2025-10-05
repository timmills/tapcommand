#!/bin/bash

#######################################################################
# SmartVenue Bootstrap Script
# Minimal script to prepare a fresh Ubuntu 24 server for installation
# Run this FIRST, then clone the repo and run install.sh
#######################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

echo ""
echo "======================================="
echo " SmartVenue Bootstrap"
echo "======================================="
echo ""

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    print_error "Don't run as root. Run as normal user with sudo."
    exit 1
fi

# Check sudo
if ! sudo -v; then
    print_error "This script requires sudo privileges"
    exit 1
fi

print_info "Installing minimal prerequisites..."

# Update package lists
sudo apt-get update -qq

# Install git (needed to clone repo)
sudo apt-get install -y git curl

print_success "Bootstrap complete!"
echo ""
print_info "Next steps:"
echo "  1. Clone the repository:"
echo "     git clone -b release <your-repo-url> /opt/smartvenue"
echo ""
echo "  2. Run the full installer:"
echo "     cd /opt/smartvenue"
echo "     ./install.sh"
echo ""

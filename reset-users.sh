#!/bin/bash
#
# User Database Reset Helper Script
#
# This script resets ALL users in the database and creates fresh default accounts.
#
# DANGER: This will DELETE all user accounts!
#
# Usage:
#   ./reset-users.sh
#
# After running, you can log in with:
#   admin / admin (Super Admin)
#   staff / staff (Operator)
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      TapCommand User Database Reset           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo

# Check if virtual environment exists
if [ ! -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    echo -e "${RED}❌ Virtual environment not found at $SCRIPT_DIR/venv${NC}"
    echo "Please ensure the virtual environment is set up correctly."
    exit 1
fi

# Check if reset script exists
if [ ! -f "$SCRIPT_DIR/backend/reset_database_users.py" ]; then
    echo -e "${RED}❌ Reset script not found at $SCRIPT_DIR/backend/reset_database_users.py${NC}"
    exit 1
fi

# Activate virtual environment and run the reset script
cd "$SCRIPT_DIR/backend"
source "$SCRIPT_DIR/venv/bin/activate"

echo -e "${BLUE}Running user database reset...${NC}"
echo

python3 reset_database_users.py

RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo
    echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║         User Database Reset Complete! ✓       ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${GREEN}You can now log in with:${NC}"
    echo
    echo -e "${GREEN}  👤 Admin account:${NC}"
    echo -e "${GREEN}     Username: admin${NC}"
    echo -e "${GREEN}     Password: admin${NC}"
    echo -e "${GREEN}     Role: Super Admin${NC}"
    echo
    echo -e "${GREEN}  👤 Staff account:${NC}"
    echo -e "${GREEN}     Username: staff${NC}"
    echo -e "${GREEN}     Password: staff${NC}"
    echo -e "${GREEN}     Role: Operator${NC}"
else
    echo
    echo -e "${RED}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║           User Database Reset Failed ✗         ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════╝${NC}"
fi

exit $RESULT

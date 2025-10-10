#!/bin/bash
#
# Emergency Password Reset Helper Script
#
# This script makes it easy to reset a locked account password.
# It automatically activates the virtual environment and runs the reset script.
#
# Usage:
#   ./reset-password.sh <username> <new_password>
#
# Example:
#   ./reset-password.sh admin MyNewPassword123!
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
echo -e "${BLUE}║      TapCommand Emergency Password Reset      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo

# Check if we have the right number of arguments
if [ "$#" -ne 2 ]; then
    echo -e "${YELLOW}Usage:${NC}"
    echo "  $0 <username> <new_password>"
    echo
    echo -e "${YELLOW}Example:${NC}"
    echo "  $0 admin MyNewPassword123!"
    echo
    echo -e "${YELLOW}Password requirements:${NC}"
    echo "  - At least 8 characters"
    echo "  - At least one uppercase letter"
    echo "  - At least one lowercase letter"
    echo "  - At least one number"
    echo "  - At least one special character (!@#\$%^&*)"
    echo
    exit 1
fi

USERNAME="$1"
PASSWORD="$2"

# Check if virtual environment exists
if [ ! -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    echo -e "${RED}❌ Virtual environment not found at $SCRIPT_DIR/venv${NC}"
    echo "Please ensure the virtual environment is set up correctly."
    exit 1
fi

# Check if reset script exists
if [ ! -f "$SCRIPT_DIR/backend/reset_password.py" ]; then
    echo -e "${RED}❌ Reset script not found at $SCRIPT_DIR/backend/reset_password.py${NC}"
    exit 1
fi

# Activate virtual environment and run the reset script
cd "$SCRIPT_DIR/backend"
source "$SCRIPT_DIR/venv/bin/activate"

echo -e "${BLUE}Running password reset...${NC}"
echo

python3 reset_password.py "$USERNAME" "$PASSWORD"

RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo
    echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║         Password Reset Successful! ✓          ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
else
    echo
    echo -e "${RED}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║           Password Reset Failed ✗              ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════╝${NC}"
fi

exit $RESULT

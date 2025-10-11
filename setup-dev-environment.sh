#!/bin/bash

#######################################################################
# TapCommand Development Environment Setup Script
#
# This script sets up a complete development environment from a fresh
# clone of the TapCommand repository.
#
# Usage: ./setup-dev-environment.sh
#######################################################################

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_USER="${SUDO_USER:-$USER}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}  ✓ $1${NC}"
}

print_error() {
    echo -e "${RED}  ✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}  ⚠ $1${NC}"
}

print_info() {
    echo -e "  $1"
}

#######################################################################
# Main Setup Functions
#######################################################################

check_dependencies() {
    print_header "Checking System Dependencies"

    local missing_deps=()

    for cmd in python3 node npm git; do
        if command -v $cmd &> /dev/null; then
            print_success "$cmd installed"
        else
            print_error "$cmd not found"
            missing_deps+=($cmd)
        fi
    done

    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        echo ""
        echo "Install them with:"
        echo "  sudo apt-get install python3 python3-pip python3-venv nodejs npm git"
        exit 1
    fi
}

setup_backend_venv() {
    print_header "Setting Up Backend Virtual Environment"

    cd "$SCRIPT_DIR"

    if [ -d "venv" ]; then
        print_warning "Virtual environment already exists"
        read -p "Remove and recreate? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf venv
            print_info "Removed existing venv"
        else
            print_info "Using existing venv"
            return
        fi
    fi

    print_info "Creating Python virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"

    print_info "Activating virtual environment..."
    source venv/bin/activate

    print_info "Upgrading pip..."
    pip install --upgrade pip -q

    print_info "Installing backend dependencies (this may take a few minutes)..."
    cd backend
    pip install -r requirements.txt -q
    cd ..

    deactivate
    print_success "Backend dependencies installed"
}

install_frontend_deps() {
    print_header "Installing Frontend Dependencies"

    cd "$SCRIPT_DIR/frontend-v2"

    if [ -d "node_modules" ]; then
        print_warning "node_modules already exists"
        read -p "Remove and reinstall? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf node_modules package-lock.json
            print_info "Removed existing node_modules"
        else
            print_info "Using existing node_modules"
            cd "$SCRIPT_DIR"
            return
        fi
    fi

    print_info "Installing npm packages..."
    npm install --silent

    cd "$SCRIPT_DIR"
    print_success "Frontend dependencies installed"
}

setup_backend_env() {
    print_header "Configuring Backend Environment"

    cd "$SCRIPT_DIR/backend"

    if [ -f ".env" ]; then
        print_warning "Backend .env already exists"
        read -p "Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Keeping existing .env"
            cd "$SCRIPT_DIR"
            return
        fi
    fi

    # Get local and Tailscale IPs
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    TAILSCALE_IP=$(ip addr show tailscale0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d'/' -f1 || echo "")

    # Build CORS origins list
    CORS_LIST="[\"http://localhost:5173\",\"http://localhost:3000\",\"http://$LOCAL_IP\""
    if [[ -n "$TAILSCALE_IP" ]]; then
        CORS_LIST="$CORS_LIST,\"http://$TAILSCALE_IP\""
        print_info "Detected Tailscale IP: $TAILSCALE_IP"
    fi
    CORS_LIST="$CORS_LIST]"

    print_info "Creating .env file..."
    cat > .env << EOF
# Database
DATABASE_URL=sqlite:///./tapcommand.db

# CORS Configuration (JSON array format)
CORS_ORIGINS=$CORS_LIST
CORS_ALLOW_CREDENTIALS=false

# ESPHome API (optional - set if using encrypted API)
# ESPHOME_API_KEY=your_key_here

# WiFi Network
WIFI_SSID=TV

# Scheduling
SCHEDULER_TIMEZONE=Australia/Sydney
EOF

    print_success "Backend .env created"
    print_info "Local IP: $LOCAL_IP"
    if [[ -n "$TAILSCALE_IP" ]]; then
        print_info "Tailscale IP: $TAILSCALE_IP"
    fi

    cd "$SCRIPT_DIR"
}

setup_frontend_env() {
    print_header "Configuring Frontend Environment"

    cd "$SCRIPT_DIR/frontend-v2"

    if [ -f ".env.local" ]; then
        print_warning "Frontend .env.local already exists"
        read -p "Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Keeping existing .env.local"
            cd "$SCRIPT_DIR"
            return
        fi
    fi

    print_info "Creating .env.local file..."
    cat > .env.local << 'EOF'
# Set to 'auto' to enable automatic network detection
# Or set to specific URL like http://192.168.101.153:8000
VITE_API_BASE_URL=auto
EOF

    print_success "Frontend .env.local created (auto-detection enabled)"

    cd "$SCRIPT_DIR"
}

check_database() {
    print_header "Checking Database"

    if [ -f "$SCRIPT_DIR/backend/tapcommand.db" ]; then
        DB_SIZE=$(du -h "$SCRIPT_DIR/backend/tapcommand.db" | cut -f1)
        print_success "Database exists ($DB_SIZE)"
        print_info "Database will be used as-is from repository"
    else
        print_warning "No database found"
        print_info "Database will be created on first backend start"
    fi
}

setup_systemd_services() {
    print_header "Setting Up Systemd Services"

    if [ "$EUID" -ne 0 ]; then
        print_warning "Not running as root - skipping systemd service setup"
        print_info "To install services later, run as root:"
        echo ""
        echo "  sudo $SCRIPT_DIR/enable-services.sh"
        echo ""
        return
    fi

    # Check if services need timezone fix
    if ! grep -q "TZ=" "$SCRIPT_DIR/deploy/systemd/tapcommand-backend.service" 2>/dev/null; then
        print_warning "Service files need timezone configuration"
        print_info "Updating service files..."

        # The service files should already be correct from the repo
        # but this is a fallback
    fi

    print_info "Installing systemd services..."
    cp "$SCRIPT_DIR/deploy/systemd/tapcommand-backend.service" /etc/systemd/system/
    cp "$SCRIPT_DIR/deploy/systemd/tapcommand-scanner.service" /etc/systemd/system/

    systemctl daemon-reload

    print_info "Enabling services to start on boot..."
    systemctl enable tapcommand-backend.service
    systemctl enable tapcommand-scanner.service

    print_info "Starting services..."
    systemctl start tapcommand-backend.service
    systemctl start tapcommand-scanner.service

    sleep 2

    if systemctl is-active --quiet tapcommand-backend.service; then
        print_success "Backend service started"
    else
        print_error "Backend service failed to start"
        print_info "Check logs: journalctl -u tapcommand-backend.service -n 50"
    fi

    if systemctl is-active --quiet tapcommand-scanner.service; then
        print_success "Scanner service started"
    else
        print_warning "Scanner service failed to start (check logs)"
    fi
}

start_dev_servers() {
    print_header "Development Server Options"

    echo ""
    echo "Backend service is running via systemd on port 8000"
    echo ""
    read -p "Start frontend dev server now? (Y/n): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        print_info "Starting Vite dev server..."
        cd "$SCRIPT_DIR/frontend-v2"

        # Check if already running
        if lsof -i :5173 &> /dev/null; then
            print_warning "Port 5173 already in use"
            print_info "Dev server may already be running"
        else
            # Start in background
            nohup npm run dev > "$SCRIPT_DIR/vite-dev.out" 2>&1 &
            VITE_PID=$!

            sleep 3

            if ps -p $VITE_PID > /dev/null; then
                print_success "Frontend dev server started (PID: $VITE_PID)"
            else
                print_error "Failed to start dev server"
                print_info "Check logs: cat $SCRIPT_DIR/vite-dev.out"
            fi
        fi

        cd "$SCRIPT_DIR"
    else
        print_info "To start frontend dev server later:"
        echo ""
        echo "  cd $SCRIPT_DIR/frontend-v2"
        echo "  npm run dev"
        echo ""
    fi
}

print_summary() {
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    TAILSCALE_IP=$(ip addr show tailscale0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d'/' -f1 || echo "")

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║       🎉 Development Environment Setup Complete!          ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo -e "${GREEN}Access Points:${NC}"
    echo "  📊 Backend API:  http://$LOCAL_IP:8000"
    echo "  📚 API Docs:     http://$LOCAL_IP:8000/docs"

    if lsof -i :5173 &> /dev/null; then
        echo "  🎨 Frontend Dev: http://$LOCAL_IP:5173"
        if [[ -n "$TAILSCALE_IP" ]]; then
            echo "  🔐 Tailscale:    http://$TAILSCALE_IP:5173"
        fi
    fi

    echo ""
    echo -e "${YELLOW}Useful Commands:${NC}"
    echo "  Backend logs:    journalctl -u tapcommand-backend.service -f"
    echo "  Scanner logs:    journalctl -u tapcommand-scanner.service -f"
    echo "  Health check:    ./health-check.sh"
    echo "  Restart backend: sudo systemctl restart tapcommand-backend.service"
    echo ""
    echo "  Start frontend dev server:"
    echo "    cd frontend-v2 && npm run dev"
    echo ""
    echo -e "${BLUE}Development Workflow:${NC}"
    echo "  1. Backend runs as systemd service (auto-restarts on code changes with --reload)"
    echo "  2. Frontend runs via 'npm run dev' (hot reload enabled)"
    echo "  3. Edit code and changes will be reflected automatically"
    echo ""
    echo "  Database: $SCRIPT_DIR/backend/tapcommand.db"
    echo ""
}

#######################################################################
# Main Execution
#######################################################################

main() {
    clear

    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║     🏗️  TapCommand Development Environment Setup          ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "This will set up a complete development environment at:"
    echo "  $SCRIPT_DIR"
    echo ""
    read -p "Continue? (Y/n): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Nn]$ ]]; then
        echo "Setup cancelled"
        exit 0
    fi

    check_dependencies
    setup_backend_venv
    install_frontend_deps
    setup_backend_env
    setup_frontend_env
    check_database

    # Only setup systemd if running as root
    if [ "$EUID" -eq 0 ]; then
        setup_systemd_services
        start_dev_servers
    else
        print_warning "Not running as root - systemd services not installed"
        echo ""
        echo "To install and start services, run:"
        echo "  sudo $SCRIPT_DIR/enable-services.sh"
        echo ""
        echo "Then manually start frontend dev server:"
        echo "  cd $SCRIPT_DIR/frontend-v2 && npm run dev"
        echo ""
    fi

    print_summary
}

# Run main function
main

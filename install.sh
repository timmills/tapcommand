#!/bin/bash

#######################################################################
# SmartVenue Installation Script for Ubuntu 24 Server
# This script installs and configures SmartVenue on a fresh system
#######################################################################

set -e  # Exit on any error

# Remove this script after execution (self-cleanup)
trap 'rm -f "$0"' EXIT

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${SCRIPT_DIR}/smartvenue"
APP_USER="${SUDO_USER:-$USER}"
PYTHON_VERSION="3.12"
NODE_VERSION="22"
BACKEND_PORT="8000"
FRONTEND_PORT="5173"
REPO_URL="https://github.com/timmills/smartvenue-device-management.git"
REPO_BRANCH="release"

#######################################################################
# Helper Functions
#######################################################################

print_header() {
    echo -e "\n${BLUE}===================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should NOT be run as root directly"
        print_info "Run it as a normal user with sudo privileges: ./install.sh"
        exit 1
    fi

    if ! sudo -v; then
        print_error "This script requires sudo privileges"
        exit 1
    fi
}

check_ubuntu() {
    if [[ ! -f /etc/os-release ]]; then
        print_error "Cannot detect OS version"
        exit 1
    fi

    . /etc/os-release
    if [[ "$ID" != "ubuntu" ]]; then
        print_warning "This script is designed for Ubuntu 24. You are running: $ID"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

#######################################################################
# Repository Clone
#######################################################################

clone_repository() {
    print_header "Cloning SmartVenue Repository"

    # Check if git is available
    if ! command -v git &> /dev/null; then
        print_error "git is not installed or not in PATH"
        exit 1
    fi

    print_info "Target directory: $INSTALL_DIR"

    if [[ -d "$INSTALL_DIR" ]]; then
        print_warning "Directory $INSTALL_DIR already exists"
        read -p "Remove and re-clone? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Removing existing directory..."
            rm -rf "$INSTALL_DIR"
        else
            print_info "Using existing directory"
            return
        fi
    fi

    print_info "Cloning repository from $REPO_URL (branch: $REPO_BRANCH)..."
    if ! git clone -b "$REPO_BRANCH" "$REPO_URL" "$INSTALL_DIR"; then
        print_error "Failed to clone repository"
        print_info "Repository: $REPO_URL"
        print_info "Branch: $REPO_BRANCH"
        print_info "Target: $INSTALL_DIR"
        exit 1
    fi

    print_success "Repository cloned successfully to $INSTALL_DIR"

    # Verify the clone
    if [[ ! -d "$INSTALL_DIR/backend" ]]; then
        print_error "Clone succeeded but backend directory not found!"
        print_info "Contents of $INSTALL_DIR:"
        ls -la "$INSTALL_DIR"
        exit 1
    fi
}

#######################################################################
# System Dependency Installation
#######################################################################

install_system_deps() {
    print_header "Installing System Dependencies"

    print_info "Updating package lists..."
    sudo apt-get update -qq

    print_info "Installing core dependencies..."
    sudo apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        build-essential \
        curl \
        git \
        nginx \
        sqlite3 \
        avahi-utils \
        libavahi-compat-libdnssd-dev \
        nmap \
        net-tools \
        bc \
        libssl-dev \
        libffi-dev \
        iputils-ping \
        iproute2 \
        || { print_error "Failed to install system dependencies"; exit 1; }

    print_success "System dependencies installed"
}

check_python_version() {
    print_header "Checking Python Version"

    PYTHON_VER=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    print_info "Detected Python version: $PYTHON_VER"

    if [[ $(echo "$PYTHON_VER >= $PYTHON_VERSION" | bc) -ne 1 ]]; then
        print_error "Python $PYTHON_VERSION or higher is required (found $PYTHON_VER)"
        exit 1
    fi

    print_success "Python version OK"
}

install_node() {
    print_header "Installing Node.js"

    if command -v node &> /dev/null; then
        NODE_VER=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
        if [[ $NODE_VER -ge $NODE_VERSION ]]; then
            print_success "Node.js $NODE_VER already installed"
            return
        fi
    fi

    print_info "Installing Node.js $NODE_VERSION via NodeSource..."
    curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | sudo -E bash -
    sudo apt-get install -y nodejs

    print_success "Node.js $(node --version) installed"
    print_success "npm $(npm --version) installed"
}

#######################################################################
# Application Setup
#######################################################################

setup_backend() {
    print_header "Setting Up Backend"

    print_info "Creating Python virtual environment in $INSTALL_DIR..."
    cd "$INSTALL_DIR"
    python3 -m venv venv

    print_info "Activating virtual environment..."
    source venv/bin/activate

    print_info "Upgrading pip..."
    pip install --upgrade pip

    print_info "Installing Python dependencies (this may take several minutes)..."
    cd backend
    pip install -r requirements.txt

    print_success "Backend dependencies installed"

    deactivate
}

setup_frontend() {
    print_header "Setting Up Frontend"

    cd "$INSTALL_DIR/frontend-v2"

    print_info "Installing npm dependencies (this may take a few minutes)..."
    npm install --silent

    print_info "Building frontend for production..."
    # Skip TypeScript type checking during build for faster installation
    # Vite will still bundle correctly
    if ! npx vite build --mode production 2>&1 | tee /tmp/frontend-build.log; then
        print_error "Frontend build failed"
        print_info "Check /tmp/frontend-build.log for details"
        exit 1
    fi

    print_info "Setting permissions for nginx..."
    # Make home directory executable so nginx can traverse to dist
    chmod o+x "$HOME"
    # Make dist directory readable by nginx
    chmod -R o+rX dist/

    print_success "Frontend built successfully"
}

setup_database() {
    print_header "Setting Up Database"

    cd "$INSTALL_DIR/backend"

    # Database should be included in the release branch
    if [[ -f "smartvenue.db" ]]; then
        print_success "Database found in repository"
        chmod 664 smartvenue.db
    else
        print_warning "No database found in repository"
        print_info "Database will be created on first run"
    fi
}

setup_environment() {
    print_header "Configuring Environment"

    # Backend environment
    if [[ ! -f "$INSTALL_DIR/backend/.env" ]]; then
        print_info "Creating backend .env file..."

        # Get local and Tailscale IPs for CORS
        LOCAL_IP=$(hostname -I | awk '{print $1}')
        TAILSCALE_IP=$(ip addr show tailscale0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d'/' -f1)

        # Build CORS origins list (JSON array format for pydantic)
        CORS_LIST="[\"http://localhost:5173\",\"http://localhost:3000\",\"http://$LOCAL_IP\""
        if [[ -n "$TAILSCALE_IP" ]]; then
            CORS_LIST="$CORS_LIST,\"http://$TAILSCALE_IP\""
        fi
        CORS_LIST="$CORS_LIST]"

        cat > "$INSTALL_DIR/backend/.env" << EOF
# Database
DATABASE_URL=sqlite:///./smartvenue.db

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
        print_success "Backend environment configured"
        print_info "CORS origins: $CORS_LIST"
    else
        print_info "Backend .env already exists, skipping"
    fi

    # Frontend environment
    if [[ ! -f "$INSTALL_DIR/frontend-v2/.env.local" ]]; then
        print_info "Creating frontend .env.local file..."

        # Try to detect local IP
        LOCAL_IP=$(hostname -I | awk '{print $1}')

        read -p "Enter backend URL [http://$LOCAL_IP:$BACKEND_PORT]: " BACKEND_URL
        BACKEND_URL=${BACKEND_URL:-http://$LOCAL_IP:$BACKEND_PORT}

        cat > "$INSTALL_DIR/frontend-v2/.env.local" << EOF
VITE_API_URL=$BACKEND_URL
EOF
        print_success "Frontend environment configured"
    else
        print_info "Frontend .env.local already exists, skipping"
    fi
}

setup_systemd_services() {
    print_header "Setting Up Systemd Services"

    # Create backend service
    print_info "Creating backend systemd service..."
    sudo tee /etc/systemd/system/smartvenue-backend.service > /dev/null << EOF
[Unit]
Description=SmartVenue Backend API
After=network.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$INSTALL_DIR/backend
Environment="PATH=$INSTALL_DIR/venv/bin"
ExecStart=$INSTALL_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    print_success "Backend service created"

    # Get local IP for network scanner
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    SUBNET=$(echo $LOCAL_IP | cut -d'.' -f1-3)

    print_info "Creating network scanner service..."
    sudo tee /etc/systemd/system/smartvenue-scanner.service > /dev/null << EOF
[Unit]
Description=SmartVenue Network Scanner
After=network.target smartvenue-backend.service

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$INSTALL_DIR/backend
Environment="PATH=$INSTALL_DIR/venv/bin"
ExecStart=$INSTALL_DIR/venv/bin/python -m app.services.scheduled_network_scan --subnet $SUBNET --interval 10
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

    print_success "Network scanner service created (scanning $SUBNET.0/24 every 10 minutes)"

    # Reload systemd
    sudo systemctl daemon-reload

    print_info "Services created but not started yet"
}

setup_nginx() {
    print_header "Setting Up Nginx"

    # Get server IPs
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    TAILSCALE_IP=$(ip addr show tailscale0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d'/' -f1)

    if [[ -n "$TAILSCALE_IP" ]]; then
        print_success "Tailscale IP detected: $TAILSCALE_IP"
        SERVER_NAMES="$LOCAL_IP $TAILSCALE_IP"
    else
        print_warning "Tailscale not detected, using local IP only"
        SERVER_NAMES="$LOCAL_IP"
    fi

    read -p "Enter additional server hostnames or IPs (space-separated) [$SERVER_NAMES]: " EXTRA_NAMES
    if [[ -n "$EXTRA_NAMES" ]]; then
        SERVER_NAMES="$EXTRA_NAMES"
    fi

    print_info "Creating nginx configuration for: $SERVER_NAMES"
    sudo tee /etc/nginx/sites-available/smartvenue > /dev/null << EOF
server {
    listen 80;
    server_name $SERVER_NAMES;

    # Frontend (serve built files)
    location / {
        root $INSTALL_DIR/frontend-v2/dist;
        try_files \$uri \$uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # WebSocket support (if needed)
    location /ws {
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
    }

    # Serve install script
    location /install.sh {
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
    }
}
EOF

    # Enable site
    sudo ln -sf /etc/nginx/sites-available/smartvenue /etc/nginx/sites-enabled/

    # Remove default site if exists
    sudo rm -f /etc/nginx/sites-enabled/default

    # Test nginx config
    if sudo nginx -t 2>&1 | grep -q "successful"; then
        print_success "Nginx configuration valid"
    else
        print_error "Nginx configuration has errors"
        sudo nginx -t
        exit 1
    fi
}

#######################################################################
# Startup & Verification
#######################################################################

start_services() {
    print_header "Starting Services"

    print_info "Enabling and starting backend service..."
    sudo systemctl enable smartvenue-backend.service
    sudo systemctl start smartvenue-backend.service
    sleep 5

    if sudo systemctl is-active --quiet smartvenue-backend.service; then
        print_success "Backend service started"
    else
        print_error "Backend service failed to start"
        print_info "Recent logs:"
        sudo journalctl -u smartvenue-backend.service -n 20 --no-pager
        print_info "Full logs: sudo journalctl -u smartvenue-backend.service -n 50"
        exit 1
    fi

    print_info "Enabling and starting network scanner service..."
    sudo systemctl enable smartvenue-scanner.service
    sudo systemctl start smartvenue-scanner.service
    sleep 2

    if sudo systemctl is-active --quiet smartvenue-scanner.service; then
        print_success "Network scanner service started"
    else
        print_warning "Network scanner failed to start (check logs: sudo journalctl -u smartvenue-scanner.service)"
    fi

    print_info "Restarting nginx..."
    sudo systemctl restart nginx

    if sudo systemctl is-active --quiet nginx; then
        print_success "Nginx started"
    else
        print_error "Nginx failed to start"
        exit 1
    fi
}

verify_installation() {
    print_header "Verifying Installation"

    # Check backend health
    print_info "Checking backend health..."
    sleep 2
    if curl -sf http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
        print_success "Backend is responding"
    else
        print_warning "Backend health check failed (might still be starting)"
    fi

    # Check nginx
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    print_info "Checking nginx..."
    if curl -sf http://localhost/ > /dev/null 2>&1; then
        print_success "Nginx is serving frontend"
    else
        print_warning "Nginx check failed"
    fi

    print_header "Installation Complete!"
    echo ""
    print_success "SmartVenue has been installed successfully!"
    echo ""
    echo -e "${BLUE}Access the application at:${NC}"
    echo -e "  ${GREEN}http://$LOCAL_IP${NC}"
    echo ""
    echo -e "${BLUE}Service Management:${NC}"
    echo -e "  View backend logs:   ${YELLOW}sudo journalctl -u smartvenue-backend.service -f${NC}"
    echo -e "  Restart backend:     ${YELLOW}sudo systemctl restart smartvenue-backend.service${NC}"
    echo -e "  Check status:        ${YELLOW}sudo systemctl status smartvenue-backend.service${NC}"
    echo ""
    echo -e "${BLUE}Database Location:${NC}"
    echo -e "  ${YELLOW}$INSTALL_DIR/backend/smartvenue.db${NC}"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo -e "  1. Navigate to http://$LOCAL_IP in your browser"
    echo -e "  2. Login with default credentials (check documentation)"
    echo -e "  3. Configure your devices and settings"
    echo ""
    print_info "For updates, run: ./update.sh"
    echo ""
}

#######################################################################
# Main Installation Flow
#######################################################################

main() {
    print_header "SmartVenue Installation Script"

    print_info "Installation directory: $INSTALL_DIR"
    print_info "Application user: $APP_USER"
    echo ""

    read -p "Continue with installation? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Installation cancelled"
        exit 0
    fi

    check_root
    check_ubuntu
    install_system_deps
    clone_repository
    check_python_version
    install_node
    setup_backend
    setup_frontend
    setup_database
    setup_environment
    setup_systemd_services
    setup_nginx
    start_services
    verify_installation
}

# Run main installation
main

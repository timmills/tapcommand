#!/bin/bash

#######################################################################
# SmartVenue Installation Script for Ubuntu 24 Server
# This script installs and configures SmartVenue on a fresh system
#######################################################################

set -e  # Exit on any error

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
REPO_URL="https://github.com/yourusername/smartvenue.git"  # TODO: Update with actual repo

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

    print_info "Cloning repository from $REPO_URL..."
    if ! git clone "$REPO_URL" "$INSTALL_DIR"; then
        print_error "Failed to clone repository"
        print_info "Make sure git is installed and the repository URL is correct"
        exit 1
    fi

    print_success "Repository cloned successfully"
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
    pip install --upgrade pip -q

    print_info "Installing Python dependencies..."
    cd backend
    pip install -r requirements.txt -q

    print_success "Backend dependencies installed"

    deactivate
}

setup_frontend() {
    print_header "Setting Up Frontend"

    cd "$INSTALL_DIR/frontend-v2"

    print_info "Installing npm dependencies (this may take a few minutes)..."
    npm install --silent

    print_info "Building frontend for production..."
    npm run build

    print_success "Frontend built successfully"
}

setup_database() {
    print_header "Setting Up Database"

    cd "$INSTALL_DIR/backend"

    if [[ -f "smartvenue.db" ]]; then
        print_warning "Database already exists at backend/smartvenue.db"
        read -p "Keep existing database? (Y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            print_info "Backing up existing database..."
            mv smartvenue.db "smartvenue.db.backup.$(date +%Y%m%d_%H%M%S)"
            print_success "Database backed up"
        else
            print_success "Keeping existing database"
            return
        fi
    fi

    if [[ -f "smartvenue_template.db" ]]; then
        print_info "Using template database..."
        cp smartvenue_template.db smartvenue.db
        print_success "Database initialized from template"
    else
        print_info "No template found - database will be created on first run"
    fi

    # Set proper permissions
    chmod 664 smartvenue.db 2>/dev/null || true
}

setup_environment() {
    print_header "Configuring Environment"

    # Backend environment
    if [[ ! -f "$INSTALL_DIR/backend/.env" ]]; then
        print_info "Creating backend .env file..."
        cat > "$INSTALL_DIR/backend/.env" << EOF
# Database
DATABASE_URL=sqlite:///./smartvenue.db

# JWT Configuration
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS (adjust if needed)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Server
HOST=0.0.0.0
PORT=$BACKEND_PORT

# Logging
LOG_LEVEL=INFO
EOF
        print_success "Backend environment configured"
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

    # Create frontend service (for development/testing)
    print_info "Creating frontend systemd service..."
    sudo tee /etc/systemd/system/smartvenue-frontend.service > /dev/null << EOF
[Unit]
Description=SmartVenue Frontend Development Server
After=network.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$INSTALL_DIR/frontend-v2
ExecStart=/usr/bin/npm run dev -- --host 0.0.0.0 --port $FRONTEND_PORT
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    print_success "Frontend service created"

    # Reload systemd
    sudo systemctl daemon-reload

    print_info "Services created but not started yet"
}

setup_nginx() {
    print_header "Setting Up Nginx"

    # Get server name/IP
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    read -p "Enter server hostname or IP [$LOCAL_IP]: " SERVER_NAME
    SERVER_NAME=${SERVER_NAME:-$LOCAL_IP}

    print_info "Creating nginx configuration..."
    sudo tee /etc/nginx/sites-available/smartvenue > /dev/null << EOF
server {
    listen 80;
    server_name $SERVER_NAME;

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
    sleep 3

    if sudo systemctl is-active --quiet smartvenue-backend.service; then
        print_success "Backend service started"
    else
        print_error "Backend service failed to start"
        print_info "Check logs with: sudo journalctl -u smartvenue-backend.service -n 50"
        exit 1
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
    if curl -sf http://localhost:$BACKEND_PORT/api/health > /dev/null 2>&1; then
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
    check_python_version
    install_node
    clone_repository
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

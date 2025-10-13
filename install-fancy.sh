#!/bin/bash

#######################################################################
# TapCommand Fancy Installation Script for Ubuntu 24 Server
# Enhanced with Gum for a beautiful terminal UI experience
#######################################################################

set -e  # Exit on any error

# Remove this script after execution (self-cleanup)
trap 'rm -f "$0"' EXIT

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${SCRIPT_DIR}/tapcommand"
APP_USER="${SUDO_USER:-$USER}"
PYTHON_VERSION="3.12"
NODE_VERSION="22"
BACKEND_PORT="8000"
FRONTEND_PORT="5173"
REPO_URL="https://github.com/timmills/tapcommand.git"
REPO_BRANCH="release"

# Check if gum is available
HAS_GUM=false
if command -v gum &> /dev/null; then
    HAS_GUM=true
fi

#######################################################################
# Fancy UI Functions (with fallback to basic colors)
#######################################################################

fancy_header() {
    if [ "$HAS_GUM" = true ]; then
        gum style \
            --border double \
            --border-foreground 212 \
            --padding "1 2" \
            --margin "1" \
            --width 60 \
            --align center \
            "$1"
    else
        echo -e "\n╔════════════════════════════════════════════════════════╗"
        echo -e "║  $1"
        echo -e "╚════════════════════════════════════════════════════════╝\n"
    fi
}

fancy_success() {
    if [ "$HAS_GUM" = true ]; then
        gum style --foreground 10 "✓ $1"
    else
        echo -e "\033[0;32m✓ $1\033[0m"
    fi
}

fancy_error() {
    if [ "$HAS_GUM" = true ]; then
        gum style --foreground 9 "✗ $1"
    else
        echo -e "\033[0;31m✗ $1\033[0m"
    fi
}

fancy_warning() {
    if [ "$HAS_GUM" = true ]; then
        gum style --foreground 11 "⚠ $1"
    else
        echo -e "\033[1;33m⚠ $1\033[0m"
    fi
}

fancy_info() {
    if [ "$HAS_GUM" = true ]; then
        gum style --foreground 12 "ℹ $1"
    else
        echo -e "\033[0;34mℹ $1\033[0m"
    fi
}

fancy_spin() {
    local title="$1"
    shift
    if [ "$HAS_GUM" = true ]; then
        gum spin --spinner dot --title "$title" -- "$@"
    else
        echo -n "⏳ $title"
        "$@" > /dev/null 2>&1
        echo " ✓"
    fi
}

fancy_confirm() {
    if [ "$HAS_GUM" = true ]; then
        gum confirm "$1"
    else
        read -p "$1 (y/N): " -n 1 -r
        echo
        [[ $REPLY =~ ^[Yy]$ ]]
    fi
}

fancy_input() {
    local placeholder="$1"
    local default="$2"
    if [ "$HAS_GUM" = true ]; then
        gum input --placeholder "$placeholder" --value "$default"
    else
        read -p "$placeholder [$default]: " input
        echo "${input:-$default}"
    fi
}

#######################################################################
# Installation Functions
#######################################################################

check_root() {
    if [[ $EUID -eq 0 ]]; then
        fancy_error "This script should NOT be run as root directly"
        fancy_info "Run it as a normal user with sudo privileges: ./install-fancy.sh"
        exit 1
    fi

    if ! sudo -v; then
        fancy_error "This script requires sudo privileges"
        exit 1
    fi
}

check_ubuntu() {
    if [[ ! -f /etc/os-release ]]; then
        fancy_error "Cannot detect OS version"
        exit 1
    fi

    . /etc/os-release
    if [[ "$ID" != "ubuntu" ]]; then
        fancy_warning "This script is designed for Ubuntu 24. You are running: $ID"
        if ! fancy_confirm "Continue anyway?"; then
            exit 1
        fi
    fi
}

install_gum() {
    if [ "$HAS_GUM" = true ]; then
        fancy_success "Gum is already installed!"
        return
    fi

    fancy_info "Installing Gum for enhanced UI..."

    # Install gum
    if ! command -v gum &> /dev/null; then
        sudo mkdir -p /etc/apt/keyrings
        curl -fsSL https://repo.charm.sh/apt/gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/charm.gpg
        echo "deb [signed-by=/etc/apt/keyrings/charm.gpg] https://repo.charm.sh/apt/ * *" | sudo tee /etc/apt/sources.list.d/charm.list
        sudo apt-get update -qq && sudo apt-get install -y gum
        HAS_GUM=true
        fancy_success "Gum installed successfully!"
    fi
}

clone_repository() {
    fancy_header "Cloning TapCommand Repository"

    # Check if git is available
    if ! command -v git &> /dev/null; then
        fancy_error "git is not installed or not in PATH"
        exit 1
    fi

    fancy_info "Target directory: $INSTALL_DIR"

    if [[ -d "$INSTALL_DIR" ]]; then
        fancy_warning "Directory $INSTALL_DIR already exists"
        if fancy_confirm "Remove and re-clone?"; then
            fancy_info "Removing existing directory..."
            rm -rf "$INSTALL_DIR"
        else
            fancy_info "Using existing directory"
            return
        fi
    fi

    fancy_info "Cloning from $REPO_URL (branch: $REPO_BRANCH)..."
    if [ "$HAS_GUM" = true ]; then
        gum spin --spinner dot --title "Cloning repository..." -- \
            git clone -b "$REPO_BRANCH" "$REPO_URL" "$INSTALL_DIR" 2>&1 | grep -v "Cloning into"
    else
        git clone -b "$REPO_BRANCH" "$REPO_URL" "$INSTALL_DIR"
    fi

    fancy_success "Repository cloned successfully!"

    # Verify the clone
    if [[ ! -d "$INSTALL_DIR/backend" ]]; then
        fancy_error "Clone succeeded but backend directory not found!"
        exit 1
    fi
}

install_system_deps() {
    fancy_header "Installing System Dependencies"

    fancy_spin "Updating package lists..." sudo apt-get update -qq

    fancy_info "Installing core dependencies..."
    if [ "$HAS_GUM" = true ]; then
        gum spin --spinner globe --title "Installing packages (this may take a few minutes)..." -- \
            sudo apt-get install -y \
                python3 python3-pip python3-venv python3-dev \
                build-essential curl git nginx sqlite3 \
                avahi-utils libavahi-compat-libdnssd-dev \
                nmap net-tools bc libssl-dev libffi-dev \
                iputils-ping iproute2
    else
        sudo apt-get install -y \
            python3 python3-pip python3-venv python3-dev \
            build-essential curl git nginx sqlite3 \
            avahi-utils libavahi-compat-libdnssd-dev \
            nmap net-tools bc libssl-dev libffi-dev \
            iputils-ping iproute2
    fi

    fancy_success "System dependencies installed"
}

check_python_version() {
    fancy_header "Checking Python Version"

    PYTHON_VER=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    fancy_info "Detected Python version: $PYTHON_VER"

    if [[ $(echo "$PYTHON_VER >= $PYTHON_VERSION" | bc) -ne 1 ]]; then
        fancy_error "Python $PYTHON_VERSION or higher is required (found $PYTHON_VER)"
        exit 1
    fi

    fancy_success "Python version OK"
}

install_node() {
    fancy_header "Installing Node.js"

    if command -v node &> /dev/null; then
        NODE_VER=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
        if [[ $NODE_VER -ge $NODE_VERSION ]]; then
            fancy_success "Node.js $NODE_VER already installed"
            return
        fi
    fi

    fancy_info "Installing Node.js $NODE_VERSION via NodeSource..."
    curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | sudo -E bash - > /dev/null 2>&1
    sudo apt-get install -y nodejs > /dev/null 2>&1

    fancy_success "Node.js $(node --version) installed"
    fancy_success "npm $(npm --version) installed"
}

setup_backend() {
    fancy_header "Setting Up Backend"

    fancy_info "Creating Python virtual environment..."
    cd "$INSTALL_DIR"
    python3 -m venv venv

    fancy_info "Activating virtual environment..."
    source venv/bin/activate

    # Set timezone to fix conflicting system config
    export TZ=Australia/Sydney

    fancy_spin "Upgrading pip..." pip install --upgrade pip

    fancy_info "Installing Python dependencies (this may take several minutes)..."
    cd backend
    if [ "$HAS_GUM" = true ]; then
        gum spin --spinner monkey --title "Installing backend dependencies..." -- \
            pip install -r requirements.txt
    else
        pip install -r requirements.txt
    fi

    fancy_success "Backend dependencies installed"
    deactivate
}

setup_esphome_cache() {
    fancy_header "ESPHome Firmware Compiler Setup"

    fancy_info "ESPHome is used to compile firmware for IR blaster devices."
    fancy_info "First-time compilation can be slow due to downloading build tools."
    echo ""

    if fancy_confirm "Would you like to pre-download ESPHome compilation tools now? (Recommended, takes 3-5 minutes)"; then
        cd "$INSTALL_DIR"
        source venv/bin/activate
        export TZ=Australia/Sydney

        fancy_info "Creating test firmware to download PlatformIO toolchains..."

        ESPHOME_TEST_DIR=$(mktemp -d)
        cat > "$ESPHOME_TEST_DIR/test.yaml" << 'EOF'
esphome:
  name: test-firmware

esp8266:
  board: d1_mini

wifi:
  ssid: "test"
  password: "test1234"

api:

logger:
EOF

        if [ "$HAS_GUM" = true ]; then
            gum spin --spinner globe --title "Downloading ESPHome toolchains (this may take 3-5 minutes)..." -- \
                timeout 600 esphome compile "$ESPHOME_TEST_DIR/test.yaml" > /dev/null 2>&1 || true
        else
            fancy_info "Downloading ESPHome toolchains (this may take 3-5 minutes)..."
            timeout 600 esphome compile "$ESPHOME_TEST_DIR/test.yaml" > /dev/null 2>&1 || true
        fi

        rm -rf "$ESPHOME_TEST_DIR"

        if [ -d "$HOME/.platformio" ] || [ -d "/tmp/tapcommand-esphome/.platformio" ]; then
            fancy_success "ESPHome build cache populated successfully"
        else
            fancy_warning "ESPHome cache setup completed (toolchains will download on first compile)"
        fi
        deactivate
    else
        fancy_info "Skipping ESPHome pre-warming. First compilation will take longer."
    fi
}

setup_frontend() {
    fancy_header "Setting Up Frontend"

    cd "$INSTALL_DIR/frontend-v2"

    if [ "$HAS_GUM" = true ]; then
        gum spin --spinner points --title "Installing npm dependencies..." -- \
            npm install --silent
    else
        fancy_info "Installing npm dependencies..."
        npm install --silent
    fi

    if [ "$HAS_GUM" = true ]; then
        gum spin --spinner moon --title "Building frontend for production..." -- \
            npx vite build --mode production 2>&1 | grep -v "^$"
    else
        fancy_info "Building frontend for production..."
        npx vite build --mode production
    fi

    fancy_info "Setting permissions for nginx..."
    chmod o+x "$HOME"
    chmod -R o+rX dist/

    fancy_success "Frontend built successfully"
}

setup_database() {
    fancy_header "Setting Up Database"

    cd "$INSTALL_DIR/backend"

    if [[ -f "tapcommand.db" ]]; then
        fancy_success "Database found in repository"
        chmod 664 tapcommand.db

        # Ask if user wants to reset user database
        echo ""
        fancy_info "The database contains existing user accounts and authentication data."
        fancy_warning "You can optionally reset ALL users to start with a fresh admin account."
        echo ""

        if fancy_confirm "Would you like to reset the user database? (This will delete ALL users)"; then
            fancy_info "Resetting user database..."
            cd "$INSTALL_DIR"
            source venv/bin/activate
            export TZ=Australia/Sydney

            # Run the reset script non-interactively by piping the confirmation
            echo "DELETE ALL USERS" | python3 backend/reset_database_users.py

            deactivate

            fancy_success "User database reset complete!"
            fancy_info "Default credentials:"
            fancy_info "  - admin / admin (Super Admin)"
            fancy_info "  - staff / staff (Operator)"
        else
            fancy_info "Keeping existing user database"
        fi
    else
        fancy_warning "No database found in repository"
        fancy_info "Database will be created on first run with default credentials:"
        fancy_info "  - admin / admin (Super Admin)"
        fancy_info "  - staff / staff (Operator)"
    fi
}

setup_environment() {
    fancy_header "Configuring Environment"

    # Backend environment
    if [[ ! -f "$INSTALL_DIR/backend/.env" ]]; then
        fancy_info "Creating backend .env file..."

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
        fancy_success "Backend environment configured"
        fancy_info "CORS origins: $CORS_LIST"
    else
        fancy_info "Backend .env already exists, skipping"
    fi

    # Frontend environment
    if [[ ! -f "$INSTALL_DIR/frontend-v2/.env.local" ]]; then
        fancy_info "Creating frontend .env.local file..."

        # Default to auto-detection (uses nginx proxy)
        cat > "$INSTALL_DIR/frontend-v2/.env.local" << EOF
# Set to 'auto' to enable automatic network detection
# Or set to specific URL like http://192.168.101.153:8000
VITE_API_BASE_URL=auto
EOF
        fancy_success "Frontend environment configured (auto-detection enabled)"
    else
        fancy_info "Frontend .env.local already exists, skipping"
    fi
}

setup_systemd_services() {
    fancy_header "Setting Up Systemd Services"

    fancy_info "Creating backend systemd service..."
    sudo tee /etc/systemd/system/tapcommand-backend.service > /dev/null << EOF
[Unit]
Description=TapCommand Backend API
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

    fancy_success "Backend service created"

    # Get local IP for network scanner
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    SUBNET=$(echo $LOCAL_IP | cut -d'.' -f1-3)

    fancy_info "Creating network scanner service..."
    sudo tee /etc/systemd/system/tapcommand-scanner.service > /dev/null << EOF
[Unit]
Description=TapCommand Network Scanner
After=network.target tapcommand-backend.service

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$INSTALL_DIR/backend
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$INSTALL_DIR/venv/bin/python -m app.services.scheduled_network_scan --subnet $SUBNET --interval 10
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

    fancy_success "Network scanner service created (scanning $SUBNET.0/24 every 10 minutes)"
    sudo systemctl daemon-reload
}

setup_nginx() {
    fancy_header "Setting Up Nginx"

    # Get server IPs
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    TAILSCALE_IP=$(ip addr show tailscale0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d'/' -f1)

    if [[ -n "$TAILSCALE_IP" ]]; then
        fancy_success "Tailscale IP detected: $TAILSCALE_IP"
        SERVER_NAMES="$LOCAL_IP $TAILSCALE_IP"
    else
        fancy_warning "Tailscale not detected, using local IP only"
        SERVER_NAMES="$LOCAL_IP"
    fi

    EXTRA_NAMES=$(fancy_input "Additional server hostnames/IPs (space-separated)" "$SERVER_NAMES")
    if [[ -n "$EXTRA_NAMES" ]]; then
        SERVER_NAMES="$EXTRA_NAMES"
    fi

    fancy_info "Creating nginx configuration for: $SERVER_NAMES"
    sudo tee /etc/nginx/sites-available/tapcommand > /dev/null << EOF
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
    sudo ln -sf /etc/nginx/sites-available/tapcommand /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default

    # Test nginx config
    if sudo nginx -t 2>&1 | grep -q "successful"; then
        fancy_success "Nginx configuration valid"
    else
        fancy_error "Nginx configuration has errors"
        sudo nginx -t
        exit 1
    fi
}

start_services() {
    fancy_header "Starting Services"

    fancy_spin "Enabling backend service..." sudo systemctl enable tapcommand-backend.service
    fancy_spin "Starting backend service..." sudo systemctl start tapcommand-backend.service
    sleep 3

    if sudo systemctl is-active --quiet tapcommand-backend.service; then
        fancy_success "Backend service started"
    else
        fancy_error "Backend service failed to start"
        fancy_info "Recent logs:"
        sudo journalctl -u tapcommand-backend.service -n 20 --no-pager
        exit 1
    fi

    fancy_spin "Enabling network scanner service..." sudo systemctl enable tapcommand-scanner.service
    fancy_spin "Starting network scanner service..." sudo systemctl start tapcommand-scanner.service
    sleep 2

    if sudo systemctl is-active --quiet tapcommand-scanner.service; then
        fancy_success "Network scanner service started"
    else
        fancy_warning "Network scanner failed to start (check logs: sudo journalctl -u tapcommand-scanner.service)"
    fi

    fancy_spin "Restarting nginx..." sudo systemctl restart nginx

    if sudo systemctl is-active --quiet nginx; then
        fancy_success "Nginx started"
    else
        fancy_error "Nginx failed to start"
        exit 1
    fi
}

verify_installation() {
    fancy_header "Verifying Installation"

    fancy_info "Checking backend health..."
    sleep 2
    if curl -sf http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
        fancy_success "Backend is responding"
    else
        fancy_warning "Backend health check failed (might still be starting)"
    fi

    LOCAL_IP=$(hostname -I | awk '{print $1}')
    fancy_info "Checking nginx..."
    if curl -sf http://localhost/ > /dev/null 2>&1; then
        fancy_success "Nginx is serving frontend"
    fi

    # Final success message
    if [ "$HAS_GUM" = true ]; then
        echo ""
        gum style \
            --border thick \
            --border-foreground 10 \
            --padding "2 4" \
            --margin "1" \
            "🎉 TapCommand Installed Successfully!" \
            "" \
            "🌐 Access: http://$LOCAL_IP" \
            "" \
            "📊 Backend logs: sudo journalctl -u tapcommand-backend.service -f" \
            "🔄 Restart: sudo systemctl restart tapcommand-backend.service" \
            "📁 Database: $INSTALL_DIR/backend/tapcommand.db"
    else
        echo ""
        fancy_success "TapCommand has been installed successfully!"
        echo ""
        echo "🌐 Access the application at: http://$LOCAL_IP"
        echo ""
        echo "Service Management:"
        echo "  View backend logs:   sudo journalctl -u tapcommand-backend.service -f"
        echo "  Restart backend:     sudo systemctl restart tapcommand-backend.service"
        echo "  Check status:        sudo systemctl status tapcommand-backend.service"
        echo ""
        echo "Database Location: $INSTALL_DIR/backend/tapcommand.db"
        echo ""
    fi
}

run_health_check() {
    echo ""
    if fancy_confirm "Would you like to run a comprehensive health check now?"; then
        fancy_header "Running Health Check"

        if [[ -f "$INSTALL_DIR/health-check.sh" ]]; then
            cd "$INSTALL_DIR"
            chmod +x health-check.sh
            ./health-check.sh
        else
            fancy_warning "Health check script not found in repository"
            fancy_info "You can run it later with: cd $INSTALL_DIR && ./health-check.sh"
        fi
    else
        fancy_info "You can run a health check anytime with: cd $INSTALL_DIR && ./health-check.sh"
    fi
}

#######################################################################
# Main Installation Flow
#######################################################################

main() {
    clear

    if [ "$HAS_GUM" = true ]; then
        gum style \
            --border double \
            --border-foreground 212 \
            --padding "2 4" \
            --margin "1 0" \
            --width 60 \
            --align center \
            "🏢 TapCommand Installation Script" \
            "" \
            "Fancy Terminal UI Edition"
    else
        echo "╔════════════════════════════════════════════════════════╗"
        echo "║      🏢 TapCommand Installation Script                ║"
        echo "║          Fancy Terminal UI Edition                     ║"
        echo "╚════════════════════════════════════════════════════════╝"
    fi

    echo ""
    fancy_info "Installation directory: $INSTALL_DIR"
    fancy_info "Application user: $APP_USER"
    echo ""

    if ! fancy_confirm "Continue with installation?"; then
        fancy_info "Installation cancelled"
        exit 0
    fi

    check_root
    check_ubuntu
    install_gum
    install_system_deps
    clone_repository
    check_python_version
    install_node
    setup_backend
    setup_esphome_cache
    setup_frontend
    setup_database
    setup_environment
    setup_systemd_services
    setup_nginx
    start_services
    verify_installation
    run_health_check
}

# Run main installation
main

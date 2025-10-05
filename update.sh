#!/bin/bash

#######################################################################
# SmartVenue Update Script
# Handles updates from git with database migration support
#######################################################################

set -e  # Exit on any error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$INSTALL_DIR/backend"
FRONTEND_DIR="$INSTALL_DIR/frontend-v2"
BACKUP_DIR="$INSTALL_DIR/backups"

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

#######################################################################
# Pre-update Checks
#######################################################################

check_prerequisites() {
    print_header "Pre-Update Checks"

    # Check if this is a git repository
    if [[ ! -d "$INSTALL_DIR/.git" ]]; then
        print_error "This directory is not a git repository"
        exit 1
    fi

    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        print_warning "You have uncommitted changes"
        git status --short
        echo ""
        read -p "Continue with update? This will stash your changes. (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Update cancelled"
            exit 0
        fi
        git stash
        print_info "Changes stashed"
    fi

    print_success "Pre-checks complete"
}

#######################################################################
# Backup
#######################################################################

create_backup() {
    print_header "Creating Backup"

    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    mkdir -p "$BACKUP_DIR"

    # Backup database
    if [[ -f "$BACKEND_DIR/smartvenue.db" ]]; then
        print_info "Backing up database..."
        cp "$BACKEND_DIR/smartvenue.db" "$BACKUP_DIR/smartvenue_${TIMESTAMP}.db"
        print_success "Database backed up to: $BACKUP_DIR/smartvenue_${TIMESTAMP}.db"
    fi

    # Backup .env files
    print_info "Backing up environment files..."
    [[ -f "$BACKEND_DIR/.env" ]] && cp "$BACKEND_DIR/.env" "$BACKUP_DIR/backend_env_${TIMESTAMP}"
    [[ -f "$FRONTEND_DIR/.env.local" ]] && cp "$FRONTEND_DIR/.env.local" "$BACKUP_DIR/frontend_env_${TIMESTAMP}"

    print_success "Backup complete"
}

#######################################################################
# Update Code
#######################################################################

update_code() {
    print_header "Updating Code from Git"

    print_info "Current branch: $(git branch --show-current)"
    print_info "Current commit: $(git rev-parse --short HEAD)"

    print_info "Fetching updates..."
    git fetch origin

    # Get current and remote commit
    CURRENT_COMMIT=$(git rev-parse HEAD)
    REMOTE_COMMIT=$(git rev-parse @{u})

    if [[ "$CURRENT_COMMIT" == "$REMOTE_COMMIT" ]]; then
        print_success "Already up to date"
        return 0
    fi

    print_info "Updates available. Pulling changes..."
    git pull

    NEW_COMMIT=$(git rev-parse --short HEAD)
    print_success "Updated to commit: $NEW_COMMIT"

    # Show changes
    echo ""
    print_info "Changes in this update:"
    git log --oneline --no-decorate $CURRENT_COMMIT..$NEW_COMMIT
    echo ""
}

#######################################################################
# Update Dependencies
#######################################################################

update_backend_deps() {
    print_header "Updating Backend Dependencies"

    cd "$BACKEND_DIR"

    if [[ ! -d "venv" ]]; then
        print_error "Virtual environment not found. Run install.sh first."
        exit 1
    fi

    print_info "Activating virtual environment..."
    source venv/bin/activate

    print_info "Checking for requirements changes..."
    if git diff HEAD@{1} HEAD -- requirements.txt | grep -q '^[+-]'; then
        print_info "Requirements changed. Installing updates..."
        pip install -r requirements.txt -q
        print_success "Backend dependencies updated"
    else
        print_info "No changes to requirements.txt"
    fi

    deactivate
}

update_frontend_deps() {
    print_header "Updating Frontend Dependencies"

    cd "$FRONTEND_DIR"

    print_info "Checking for package.json changes..."
    if git diff HEAD@{1} HEAD -- package.json package-lock.json | grep -q '^[+-]'; then
        print_info "Dependencies changed. Running npm install..."
        npm install --silent
        print_success "Frontend dependencies updated"
    else
        print_info "No changes to package.json"
    fi
}

rebuild_frontend() {
    print_header "Rebuilding Frontend"

    cd "$FRONTEND_DIR"

    print_info "Building production frontend..."
    npm run build

    print_success "Frontend rebuilt"
}

#######################################################################
# Database Migration
#######################################################################

run_database_migrations() {
    print_header "Checking Database Migrations"

    cd "$BACKEND_DIR"

    # Check if alembic is being used
    if [[ -d "migrations" ]]; then
        print_info "Found migrations directory"

        source venv/bin/activate

        # Check if there are pending migrations
        if [[ -f "alembic.ini" ]]; then
            print_info "Running database migrations with Alembic..."

            # Check current version
            CURRENT_VERSION=$(alembic current 2>/dev/null | grep -oP '(?<=\(head\)|^)[a-f0-9]+' || echo "none")
            print_info "Current migration: $CURRENT_VERSION"

            # Upgrade to latest
            alembic upgrade head

            NEW_VERSION=$(alembic current 2>/dev/null | grep -oP '(?<=\(head\)|^)[a-f0-9]+' || echo "none")

            if [[ "$CURRENT_VERSION" != "$NEW_VERSION" ]]; then
                print_success "Database migrated to: $NEW_VERSION"
            else
                print_info "Database already at latest version"
            fi
        else
            print_warning "Migrations directory found but no alembic.ini"
            print_info "Database will auto-migrate on startup"
        fi

        deactivate
    else
        print_info "No migrations directory found"
        print_info "Database schema managed by SQLAlchemy"
    fi
}

#######################################################################
# Service Management
#######################################################################

restart_services() {
    print_header "Restarting Services"

    print_info "Stopping backend service..."
    sudo systemctl stop smartvenue-backend.service || true

    sleep 2

    print_info "Starting backend service..."
    sudo systemctl start smartvenue-backend.service

    sleep 3

    if sudo systemctl is-active --quiet smartvenue-backend.service; then
        print_success "Backend service restarted"
    else
        print_error "Backend service failed to start"
        print_info "Check logs with: sudo journalctl -u smartvenue-backend.service -n 50"
        exit 1
    fi

    print_info "Reloading nginx..."
    sudo systemctl reload nginx

    print_success "All services restarted"
}

verify_update() {
    print_header "Verifying Update"

    sleep 2

    # Check backend health
    print_info "Checking backend health..."
    if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
        print_success "Backend is responding"
    else
        print_error "Backend health check failed"
        print_info "Check logs: sudo journalctl -u smartvenue-backend.service -n 50"
        return 1
    fi

    # Check if frontend files exist
    if [[ -d "$FRONTEND_DIR/dist" ]] && [[ -f "$FRONTEND_DIR/dist/index.html" ]]; then
        print_success "Frontend build exists"
    else
        print_error "Frontend build missing"
        return 1
    fi

    print_success "Update verification complete"
}

#######################################################################
# Cleanup
#######################################################################

cleanup_old_backups() {
    print_header "Cleanup"

    if [[ -d "$BACKUP_DIR" ]]; then
        # Keep only last 10 backups
        BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/smartvenue_*.db 2>/dev/null | wc -l)
        if [[ $BACKUP_COUNT -gt 10 ]]; then
            print_info "Removing old backups (keeping last 10)..."
            ls -1t "$BACKUP_DIR"/smartvenue_*.db | tail -n +11 | xargs rm -f
            print_success "Old backups removed"
        fi
    fi
}

#######################################################################
# Rollback
#######################################################################

rollback() {
    print_header "Rollback"

    print_error "Update failed or was cancelled"
    print_info "To rollback manually:"
    echo ""
    echo "  1. Restore database:"
    echo "     Latest backup: $(ls -1t "$BACKUP_DIR"/smartvenue_*.db 2>/dev/null | head -1)"
    echo "     cp [backup] $BACKEND_DIR/smartvenue.db"
    echo ""
    echo "  2. Revert git changes:"
    echo "     git reset --hard HEAD@{1}"
    echo ""
    echo "  3. Restart services:"
    echo "     sudo systemctl restart smartvenue-backend.service"
    echo ""
}

#######################################################################
# Main Update Flow
#######################################################################

main() {
    print_header "SmartVenue Update Script"

    # Trap errors for rollback info
    trap rollback ERR

    check_prerequisites
    create_backup
    update_code
    update_backend_deps
    update_frontend_deps
    rebuild_frontend
    run_database_migrations
    restart_services
    verify_update
    cleanup_old_backups

    print_header "Update Complete!"
    echo ""
    print_success "SmartVenue has been updated successfully!"
    echo ""
    print_info "New version: $(git rev-parse --short HEAD)"
    print_info "Previous version: $(git rev-parse --short HEAD@{1})"
    echo ""
    print_info "Backups saved to: $BACKUP_DIR"
    echo ""
}

# Run update
main

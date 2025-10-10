#!/bin/bash

#######################################################################
# SmartVenue Health Check & Auto-Fix Script
# Verifies all services and dependencies are running correctly
#######################################################################

# Don't exit on errors - we're checking for them!
set +e

# Configuration
INSTALL_DIR="/home/coastal/smartvenue"
BACKEND_PORT="8000"
EXPECTED_WORKERS=3
LOG_FILE="/tmp/smartvenue-health-check.log"

# Colors for fallback
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if gum is available
HAS_GUM=false
if command -v gum &> /dev/null; then
    HAS_GUM=true
fi

# Parse arguments
FIX_MODE=false
VERBOSE=false
JSON_OUTPUT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            FIX_MODE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --help|-h)
            echo "SmartVenue Health Check Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --fix         Auto-fix common issues"
            echo "  --verbose     Show detailed output"
            echo "  --json        Output results as JSON"
            echo "  --help        Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Counters for results
PASSED=0
WARNINGS=0
FAILURES=0
FIXES_APPLIED=0

# Array to store results for JSON output
declare -a RESULTS

#######################################################################
# UI Functions
#######################################################################

fancy_header() {
    if [ "$HAS_GUM" = true ] && [ "$JSON_OUTPUT" = false ]; then
        gum style \
            --border double \
            --border-foreground 212 \
            --padding "1 2" \
            --margin "1" \
            --width 70 \
            --align center \
            "$1"
    else
        echo -e "\n${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${BLUE}║  $1${NC}"
        echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}\n"
    fi
}

fancy_section() {
    if [ "$HAS_GUM" = true ] && [ "$JSON_OUTPUT" = false ]; then
        gum style \
            --foreground 212 \
            --bold \
            "▶ $1"
    else
        echo -e "\n${BLUE}▶ $1${NC}"
    fi
}

check_pass() {
    ((PASSED++))
    RESULTS+=("PASS:$1")
    if [ "$JSON_OUTPUT" = false ]; then
        if [ "$HAS_GUM" = true ]; then
            gum style --foreground 10 "  ✓ $1"
        else
            echo -e "${GREEN}  ✓ $1${NC}"
        fi
    fi
}

check_warn() {
    ((WARNINGS++))
    RESULTS+=("WARN:$1")
    if [ "$JSON_OUTPUT" = false ]; then
        if [ "$HAS_GUM" = true ]; then
            gum style --foreground 11 "  ⚠ $1"
        else
            echo -e "${YELLOW}  ⚠ $1${NC}"
        fi
    fi
}

check_fail() {
    ((FAILURES++))
    RESULTS+=("FAIL:$1")
    if [ "$JSON_OUTPUT" = false ]; then
        if [ "$HAS_GUM" = true ]; then
            gum style --foreground 9 "  ✗ $1"
        else
            echo -e "${RED}  ✗ $1${NC}"
        fi
    fi
}

check_fix() {
    ((FIXES_APPLIED++))
    RESULTS+=("FIXED:$1")
    if [ "$JSON_OUTPUT" = false ]; then
        if [ "$HAS_GUM" = true ]; then
            gum style --foreground 13 "  🔧 $1"
        else
            echo -e "${BLUE}  🔧 $1${NC}"
        fi
    fi
}

#######################################################################
# Check Functions
#######################################################################

check_system_dependencies() {
    fancy_section "System Dependencies"

    # Python version
    if command -v python3 &> /dev/null; then
        PYTHON_VER=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        if [[ $(echo "$PYTHON_VER >= 3.10" | bc) -eq 1 ]]; then
            check_pass "Python $PYTHON_VER installed"
        else
            check_warn "Python $PYTHON_VER found (3.12+ recommended)"
        fi
    else
        check_fail "Python 3 not found"
    fi

    # Required system packages
    for pkg in nmap curl git bc; do
        if command -v $pkg &> /dev/null; then
            check_pass "$pkg installed"
        else
            check_fail "$pkg not installed"
        fi
    done
}

check_file_structure() {
    fancy_section "File Structure"

    # Main directory
    if [ -d "$INSTALL_DIR" ]; then
        check_pass "Install directory exists: $INSTALL_DIR"
    else
        check_fail "Install directory not found: $INSTALL_DIR"
        return
    fi

    # Backend directory
    if [ -d "$INSTALL_DIR/backend" ]; then
        check_pass "Backend directory exists"
    else
        check_fail "Backend directory not found"
    fi

    # Virtual environment
    if [ -d "$INSTALL_DIR/venv" ]; then
        check_pass "Python virtual environment exists"
    else
        check_fail "Virtual environment not found"
        if [ "$FIX_MODE" = true ]; then
            check_fix "Creating virtual environment..."
            cd "$INSTALL_DIR"
            python3 -m venv venv
        fi
    fi

    # Database
    if [ -f "$INSTALL_DIR/backend/smartvenue.db" ]; then
        DB_SIZE=$(du -h "$INSTALL_DIR/backend/smartvenue.db" | cut -f1)
        check_pass "Database exists ($DB_SIZE)"

        # Check if writable
        if [ -w "$INSTALL_DIR/backend/smartvenue.db" ]; then
            check_pass "Database is writable"
        else
            check_fail "Database is not writable"
        fi
    else
        check_warn "Database not found (will be created on first run)"
    fi
}

check_configuration() {
    fancy_section "Configuration Files"

    # Backend .env
    if [ -f "$INSTALL_DIR/backend/.env" ]; then
        check_pass "Backend .env exists"

        # Check critical variables
        if grep -q "DATABASE_URL=" "$INSTALL_DIR/backend/.env"; then
            check_pass "DATABASE_URL configured"
        else
            check_warn "DATABASE_URL not set in .env"
        fi

        # CORS_ORIGINS is optional - can be configured in code
        if grep -q "CORS_ORIGINS=" "$INSTALL_DIR/backend/.env"; then
            check_pass "CORS_ORIGINS configured in .env"
        fi
    else
        check_fail "Backend .env not found"
        if [ "$FIX_MODE" = true ]; then
            check_fix "Creating default .env file..."
            cat > "$INSTALL_DIR/backend/.env" << 'EOF'
DATABASE_URL=sqlite:///./smartvenue.db
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
CORS_ALLOW_CREDENTIALS=false
WIFI_SSID=TV
SCHEDULER_TIMEZONE=Australia/Sydney
EOF
        fi
    fi
}

check_backend_process() {
    fancy_section "Backend Service"

    # Check if uvicorn is running
    if pgrep -f "uvicorn app.main" > /dev/null; then
        PID=$(pgrep -f "uvicorn app.main" | head -1)
        check_pass "Backend process running (PID: $PID)"

        # Check port
        if ss -tlnp 2>/dev/null | grep ":$BACKEND_PORT" > /dev/null || \
           netstat -tlnp 2>/dev/null | grep ":$BACKEND_PORT" > /dev/null; then
            check_pass "Backend listening on port $BACKEND_PORT"
        else
            check_warn "Backend not listening on port $BACKEND_PORT"
        fi

        # Health check
        if curl -sf "http://localhost:$BACKEND_PORT/health" > /dev/null 2>&1; then
            check_pass "Backend health check passed"
        else
            check_fail "Backend health check failed"
        fi
    else
        check_fail "Backend process not running"
        if [ "$FIX_MODE" = true ]; then
            check_fix "Starting backend..."
            cd "$INSTALL_DIR/backend"
            source ../venv/bin/activate
            nohup uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload > /tmp/backend.log 2>&1 &
            sleep 3
        fi
    fi
}

check_queue_processor() {
    fancy_section "Command Queue Processor"

    # Check if backend is running
    if ! pgrep -f "uvicorn app.main" > /dev/null; then
        check_fail "Cannot check queue processor (backend not running)"
        return
    fi

    # Try to get queue metrics
    METRICS=$(curl -sf "http://localhost:$BACKEND_PORT/api/v1/commands/queue/metrics" 2>/dev/null)
    if [ $? -eq 0 ]; then
        check_pass "Queue processor is responding"

        # Parse metrics if verbose
        if [ "$VERBOSE" = true ]; then
            QUEUE_SIZE=$(echo "$METRICS" | grep -o '"queue_size":[0-9]*' | cut -d':' -f2)
            if [ -n "$QUEUE_SIZE" ]; then
                check_pass "Current queue size: $QUEUE_SIZE"
            fi
        fi
    else
        check_warn "Queue processor metrics unavailable"
    fi

    # Check logs for worker startup
    if journalctl -u smartvenue-backend -n 100 --no-pager 2>/dev/null | grep -q "Worker.*started"; then
        WORKER_COUNT=$(journalctl -u smartvenue-backend -n 100 --no-pager 2>/dev/null | grep -c "Worker.*started")
        if [ "$WORKER_COUNT" -ge "$EXPECTED_WORKERS" ]; then
            check_pass "Queue workers started ($WORKER_COUNT workers)"
        else
            check_warn "Only $WORKER_COUNT workers found (expected $EXPECTED_WORKERS)"
        fi
    fi
}

check_network_scanner() {
    fancy_section "Network Scanner Service"

    if pgrep -f "scheduled_network_scan" > /dev/null; then
        PID=$(pgrep -f "scheduled_network_scan" | head -1)
        check_pass "Network scanner running (PID: $PID)"

        # Check last scan time via API
        LAST_SCAN=$(curl -sf "http://localhost:$BACKEND_PORT/api/network/last-scan-time" 2>/dev/null)
        if [ $? -eq 0 ]; then
            SCAN_TIME=$(echo "$LAST_SCAN" | grep -o '"last_scan_time":"[^"]*"' | cut -d'"' -f4)
            if [ -n "$SCAN_TIME" ] && [ "$SCAN_TIME" != "null" ]; then
                # Convert ISO timestamp to Unix timestamp and calculate time ago
                if command -v date &> /dev/null; then
                    # Remove timezone designator and handle ISO format
                    SCAN_UNIX=$(date -d "${SCAN_TIME}" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "${SCAN_TIME}" +%s 2>/dev/null)
                    NOW_UNIX=$(date +%s)

                    if [ -n "$SCAN_UNIX" ]; then
                        DIFF=$((NOW_UNIX - SCAN_UNIX))
                        MINUTES=$((DIFF / 60))
                        HOURS=$((DIFF / 3600))

                        if [ $DIFF -lt 60 ]; then
                            TIME_AGO="${DIFF} seconds ago"
                        elif [ $DIFF -lt 3600 ]; then
                            TIME_AGO="${MINUTES} minutes ago"
                        else
                            TIME_AGO="${HOURS} hours ago"
                        fi

                        if [ $MINUTES -lt 15 ]; then
                            check_pass "Last network scan: $TIME_AGO"
                        elif [ $MINUTES -lt 60 ]; then
                            check_warn "Last network scan: $TIME_AGO (should run every 10 min)"
                        else
                            check_warn "Last network scan: $TIME_AGO (stale)"
                        fi
                    else
                        check_pass "Last network scan: $SCAN_TIME"
                    fi
                else
                    check_pass "Last network scan: $SCAN_TIME"
                fi
            else
                check_warn "No network scans performed yet"
            fi

            # Check device count in cache
            DEVICES_CACHED=$(echo "$LAST_SCAN" | grep -o '"devices_in_cache":[0-9]*' | cut -d':' -f2)
            if [ -n "$DEVICES_CACHED" ]; then
                check_pass "Devices in scan cache: $DEVICES_CACHED"
            fi
        fi
    else
        check_fail "Network scanner not running"
        if [ "$FIX_MODE" = true ]; then
            check_fix "Starting network scanner..."
            LOCAL_IP=$(hostname -I | awk '{print $1}')
            SUBNET=$(echo $LOCAL_IP | cut -d'.' -f1-3)
            cd "$INSTALL_DIR/backend"
            source ../venv/bin/activate
            nohup python -m app.services.scheduled_network_scan --subnet $SUBNET --interval 10 > /tmp/scanner.log 2>&1 &
            sleep 2
        fi
    fi
}

check_database_health() {
    fancy_section "Database Health"

    if [ ! -f "$INSTALL_DIR/backend/smartvenue.db" ]; then
        check_warn "Database not found"
        return
    fi

    # Check database size
    DB_SIZE_BYTES=$(stat -f%z "$INSTALL_DIR/backend/smartvenue.db" 2>/dev/null || stat -c%s "$INSTALL_DIR/backend/smartvenue.db" 2>/dev/null)
    DB_SIZE_MB=$((DB_SIZE_BYTES / 1024 / 1024))

    if [ "$DB_SIZE_MB" -lt 1 ]; then
        check_warn "Database is very small ($DB_SIZE_MB MB) - might be empty"
    elif [ "$DB_SIZE_MB" -gt 500 ]; then
        check_warn "Database is large ($DB_SIZE_MB MB) - consider cleanup"
    else
        check_pass "Database size: $DB_SIZE_MB MB"
    fi

    # Try to query database
    if command -v sqlite3 &> /dev/null; then
        # Count devices
        DEVICE_COUNT=$(sqlite3 "$INSTALL_DIR/backend/smartvenue.db" "SELECT COUNT(*) FROM devices;" 2>/dev/null || echo "0")
        if [ "$DEVICE_COUNT" -gt 0 ]; then
            check_pass "Devices in database: $DEVICE_COUNT"
        else
            check_warn "No devices found in database"
        fi

        # Check virtual controllers
        VC_COUNT=$(sqlite3 "$INSTALL_DIR/backend/smartvenue.db" "SELECT COUNT(*) FROM virtual_controllers;" 2>/dev/null || echo "0")
        if [ "$VC_COUNT" -gt 0 ]; then
            check_pass "Virtual controllers: $VC_COUNT"
        fi
    else
        check_warn "sqlite3 not installed - cannot verify database contents"
    fi
}

check_api_endpoints() {
    fancy_section "Critical API Endpoints"

    if ! curl -sf "http://localhost:$BACKEND_PORT/health" > /dev/null 2>&1; then
        check_fail "Backend not responding - skipping API checks"
        return
    fi

    # Test health endpoint
    HEALTH=$(curl -sf "http://localhost:$BACKEND_PORT/health" 2>/dev/null)
    if echo "$HEALTH" | grep -q '"status":"healthy"'; then
        check_pass "Health endpoint: /health"
    else
        check_fail "Health endpoint returned invalid response"
    fi

    # Test managed devices endpoint
    DEVICES=$(curl -sf "http://localhost:$BACKEND_PORT/api/v1/management/managed" 2>/dev/null)
    if [ $? -eq 0 ]; then
        DEVICE_COUNT=$(echo "$DEVICES" | grep -o '"hostname"' | wc -l)
        check_pass "Managed devices endpoint: $DEVICE_COUNT devices"
    else
        check_warn "Managed devices endpoint unavailable"
    fi

    # Test queue metrics endpoint
    QUEUE_METRICS=$(curl -sf "http://localhost:$BACKEND_PORT/api/v1/commands/queue/metrics" 2>/dev/null)
    if [ $? -eq 0 ]; then
        PENDING=$(echo "$QUEUE_METRICS" | grep -o '"pending_count":[0-9]*' | cut -d':' -f2)
        PROCESSING=$(echo "$QUEUE_METRICS" | grep -o '"processing_count":[0-9]*' | cut -d':' -f2)
        HEALTHY=$(echo "$QUEUE_METRICS" | grep -o '"healthy":[a-z]*' | cut -d':' -f2)
        if [ "$HEALTHY" = "true" ]; then
            check_pass "Queue metrics: ${PENDING:-0} pending, ${PROCESSING:-0} processing"
        else
            check_warn "Queue metrics: ${PENDING:-0} pending, ${PROCESSING:-0} processing (unhealthy)"
        fi
    else
        check_warn "Queue metrics endpoint unavailable"
    fi

    # Test network scan cache endpoint
    SCAN_CACHE=$(curl -sf "http://localhost:$BACKEND_PORT/api/network/scan-cache" 2>/dev/null)
    if [ $? -eq 0 ]; then
        CACHED_DEVICES=$(echo "$SCAN_CACHE" | grep -o '"total":[0-9]*' | cut -d':' -f2)
        if [ -n "$CACHED_DEVICES" ] && [ "$CACHED_DEVICES" -gt 0 ]; then
            check_pass "Network scan cache: $CACHED_DEVICES devices cached"
        else
            check_warn "Network scan cache is empty"
        fi
    else
        check_warn "Network scan cache endpoint unavailable"
    fi

    # Test virtual controllers endpoint
    VCS=$(curl -sf "http://localhost:$BACKEND_PORT/api/v1/virtual-controllers" 2>/dev/null)
    if [ $? -eq 0 ]; then
        VC_COUNT=$(echo "$VCS" | grep -o '"controller_id"' | wc -l)
        if [ "$VC_COUNT" -gt 0 ]; then
            check_pass "Virtual controllers: $VC_COUNT configured"
        fi
    fi

    # Test API documentation
    if curl -sf "http://localhost:$BACKEND_PORT/docs" > /dev/null 2>&1; then
        check_pass "API documentation accessible: /docs"
    else
        check_warn "API docs unavailable"
    fi
}

check_git_status() {
    fancy_section "Git Repository"

    cd "$INSTALL_DIR"

    if [ -d ".git" ]; then
        check_pass "Git repository initialized"

        # Current branch
        BRANCH=$(git branch --show-current)
        check_pass "Current branch: $BRANCH"

        # Uncommitted changes
        if git diff-index --quiet HEAD -- 2>/dev/null; then
            check_pass "Working directory clean"
        else
            check_warn "Uncommitted changes present"
        fi

        # Remote configured
        if git remote get-url origin &> /dev/null; then
            REMOTE=$(git remote get-url origin)
            if [ "$VERBOSE" = true ]; then
                check_pass "Remote configured: $REMOTE"
            fi
        else
            check_warn "No git remote configured"
        fi
    else
        check_warn "Not a git repository"
    fi
}

check_system_resources() {
    fancy_section "System Resources"

    # CPU usage
    if command -v top &> /dev/null; then
        CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
        if [ -n "$CPU_USAGE" ]; then
            CPU_INT=${CPU_USAGE%.*}
            if [ "$CPU_INT" -lt 80 ]; then
                check_pass "CPU usage: ${CPU_INT}%"
            else
                check_warn "High CPU usage: ${CPU_INT}%"
            fi
        fi
    fi

    # Memory usage
    if command -v free &> /dev/null; then
        MEM_USED=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
        if [ "$MEM_USED" -lt 80 ]; then
            check_pass "Memory usage: ${MEM_USED}%"
        else
            check_warn "High memory usage: ${MEM_USED}%"
        fi
    fi

    # Disk space
    DISK_USAGE=$(df -h "$INSTALL_DIR" | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -lt 80 ]; then
        check_pass "Disk usage: ${DISK_USAGE}%"
    elif [ "$DISK_USAGE" -lt 90 ]; then
        check_warn "Disk usage high: ${DISK_USAGE}%"
    else
        check_fail "Disk critically full: ${DISK_USAGE}%"
    fi
}

check_tailscale_status() {
    fancy_section "Network Connectivity"

    # Check if Tailscale is installed
    if ! command -v tailscale &> /dev/null; then
        check_warn "Tailscale not installed"
        return
    fi

    # Check Tailscale status
    if tailscale status &> /dev/null; then
        # Get connection status
        TS_STATUS=$(tailscale status --json 2>/dev/null)
        if [ $? -eq 0 ]; then
            # Check if we have any peers
            PEER_COUNT=$(echo "$TS_STATUS" | grep -o '"Peer"' | wc -l)

            # Get Tailscale IP
            TS_IP=$(tailscale ip -4 2>/dev/null | head -1)

            if [ -n "$TS_IP" ]; then
                check_pass "Tailscale connected: $TS_IP"

                if [ "$PEER_COUNT" -gt 0 ]; then
                    check_pass "Tailscale peers: $PEER_COUNT"
                fi
            else
                check_warn "Tailscale running but no IP assigned"
            fi
        else
            check_pass "Tailscale service running"
        fi
    else
        check_warn "Tailscale not connected"
        if [ "$FIX_MODE" = true ]; then
            check_fix "Starting Tailscale..."
            sudo tailscale up
        fi
    fi
}

#######################################################################
# Main Execution
#######################################################################

main() {
    # Start logging
    exec > >(tee "$LOG_FILE")

    if [ "$JSON_OUTPUT" = false ]; then
        clear

        if [ "$HAS_GUM" = true ]; then
            gum style \
                --border double \
                --border-foreground 212 \
                --padding "2 4" \
                --margin "1 0" \
                --width 70 \
                --align center \
                "🏥 SmartVenue Health Check" \
                "" \
                "System Verification & Auto-Fix"
        else
            echo "╔══════════════════════════════════════════════════════════════════╗"
            echo "║            🏥 SmartVenue Health Check                           ║"
            echo "║               System Verification & Auto-Fix                    ║"
            echo "╚══════════════════════════════════════════════════════════════════╝"
        fi

        echo ""
        if [ "$FIX_MODE" = true ]; then
            echo "Mode: Auto-fix enabled"
        else
            echo "Mode: Check only (use --fix to auto-repair)"
        fi
        echo ""
    fi

    # Run all checks
    check_system_dependencies
    check_file_structure
    check_configuration
    check_backend_process
    check_queue_processor
    check_network_scanner
    check_database_health
    check_api_endpoints
    check_git_status
    check_system_resources
    check_tailscale_status

    # Summary
    if [ "$JSON_OUTPUT" = true ]; then
        # JSON output
        echo "{"
        echo "  \"timestamp\": \"$(date -Iseconds)\","
        echo "  \"passed\": $PASSED,"
        echo "  \"warnings\": $WARNINGS,"
        echo "  \"failures\": $FAILURES,"
        echo "  \"fixes_applied\": $FIXES_APPLIED,"
        echo "  \"results\": ["
        for i in "${!RESULTS[@]}"; do
            STATUS="${RESULTS[$i]%%:*}"
            MESSAGE="${RESULTS[$i]#*:}"
            echo "    {\"status\": \"$STATUS\", \"message\": \"$MESSAGE\"}"
            if [ $i -lt $((${#RESULTS[@]} - 1)) ]; then
                echo ","
            fi
        done
        echo "  ]"
        echo "}"
    else
        echo ""
        if [ "$HAS_GUM" = true ]; then
            gum style \
                --border thick \
                --border-foreground $( [ "$FAILURES" -eq 0 ] && echo "10" || echo "9" ) \
                --padding "1 2" \
                --margin "1" \
                "Health Check Complete!" \
                "" \
                "✓ Passed: $PASSED" \
                "⚠ Warnings: $WARNINGS" \
                "✗ Failures: $FAILURES" \
                "$( [ "$FIX_MODE" = true ] && echo "🔧 Fixes Applied: $FIXES_APPLIED" || echo "" )" \
                "" \
                "Report saved: $LOG_FILE"
        else
            echo "════════════════════════════════════════════════════════════════"
            echo "Health Check Complete!"
            echo ""
            echo -e "${GREEN}✓ Passed: $PASSED${NC}"
            echo -e "${YELLOW}⚠ Warnings: $WARNINGS${NC}"
            echo -e "${RED}✗ Failures: $FAILURES${NC}"
            if [ "$FIX_MODE" = true ]; then
                echo -e "${BLUE}🔧 Fixes Applied: $FIXES_APPLIED${NC}"
            fi
            echo ""
            echo "Report saved: $LOG_FILE"
            echo "════════════════════════════════════════════════════════════════"
        fi
    fi

    # Exit code based on failures
    if [ "$FAILURES" -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

# Run main
main

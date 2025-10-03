# SmartVenue Command Routing Architecture - Deep Analysis & Design

**Author:** Claude 4.5 (Sonnet)
**Date:** 2025-10-01
**Purpose:** Architectural decision document for hybrid command routing system

---

## Executive Summary

**Recommendation: HYBRID ARCHITECTURE**

- **Direct routing** for interactive operations requiring immediate feedback
- **Queue routing** for bulk operations and system tasks
- **Smart routing** for single-device control operations (with fallback)

**Key Insight:** Not all operations are equal. Forcing everything through a queue adds unnecessary latency for operations where the queue provides no benefit, while leaving everything direct creates reliability and scalability problems for bulk operations.

---

## Problem Statement

The current system routes all commands directly to ESP devices. This works for single operations but has limitations:

### Current Architecture Problems

1. **No bulk operation support** - UI must wait for each command sequentially
2. **No retry mechanism** - Failed commands are lost
3. **No rate limiting** - Can overwhelm devices with concurrent requests
4. **No scheduling** - Can't defer operations to off-peak times
5. **No history** - Hard to track what was sent when
6. **Poor UX for multi-device ops** - User waits for all devices serially

### But Also...

**Adding a queue to everything creates NEW problems:**

1. **Increased latency** for simple operations (ID button becomes slow)
2. **Complex debugging** - Harder to trace command flow
3. **Database overhead** - Writing to DB for operations that don't need persistence
4. **Polling overhead** - Queue processor constantly checking for work
5. **False sense of success** - "Queued successfully" ≠ "Command executed"

---

## Proposed Solution: Hybrid Architecture

### Architecture Principles

1. **Right tool for the right job** - Route based on operation characteristics
2. **User experience first** - Interactive operations must feel instant
3. **Reliability second** - Important operations must complete eventually
4. **Observability third** - System must be debuggable and auditable

### Command Classification System

#### Class A: IMMEDIATE (Direct Routing - No Queue)

**Characteristics:**
- User blocking operation (waiting for response)
- Requires immediate feedback
- Interactive/confirmatory
- Failure tolerance: None (must know immediately)

**Operations:**
- Diagnostic signal (ID button)
- Health check / ping
- Get device status
- Get capabilities

**Routing Decision:** **DIRECT ONLY**

**Why:** Queue adds only latency, no benefits. User is literally standing there waiting to see if LED flashes.

**Implementation:**
```python
@router.post("/{hostname}/diagnostic")
async def trigger_diagnostic(hostname: str):
    """Direct, non-queued diagnostic signal"""
    # Immediate execution, no queue
    return await esphome_manager.send_tv_command(
        hostname=hostname,
        command="diagnostic_signal",
        box=0,
        digit=1
    )
```

#### Class B: INTERACTIVE (Smart Routing - Direct with Fallback)

**Characteristics:**
- User-initiated single-device control
- Moderate urgency (user wants quick feedback)
- Tolerance for slight delay
- Should work most of the time

**Operations:**
- Single device power
- Single device channel change
- Single device volume/mute
- Single device navigation

**Routing Decision:** **DIRECT FIRST, QUEUE ON FAILURE**

**Why:** Most of the time device is online and responds quickly. Queue only adds overhead. But if device is busy/offline, fallback to queue for retry.

**Implementation:**
```python
@router.post("/{hostname}/command")
async def send_command(hostname: str, cmd: CommandRequest):
    """Smart routing - try direct, fallback to queue"""

    # Try direct execution first (fast path)
    try:
        result = await esphome_manager.send_tv_command(
            hostname=hostname,
            command=cmd.command,
            box=cmd.box,
            timeout=3.0  # Quick timeout
        )

        if result:
            return {"success": True, "method": "direct"}

    except TimeoutError:
        pass  # Fall through to queue

    # Direct failed or timed out - queue for retry
    queue_id = await command_queue.enqueue(
        hostname=hostname,
        command=cmd.command,
        box=cmd.box,
        max_attempts=3
    )

    return {
        "success": True,
        "method": "queued",
        "queue_id": queue_id,
        "message": "Device busy, queued for retry"
    }
```

#### Class C: BULK (Queue Routing - Always Queued)

**Characteristics:**
- Multi-device operations
- User NOT blocking (expects progress tracking)
- High reliability requirement
- Operation takes time anyway

**Operations:**
- Bulk power on/off
- Bulk channel changes
- Zone-based operations
- Scheduled operations

**Routing Decision:** **QUEUE ONLY**

**Why:** User expects progress tracking. Operation takes time anyway. Needs coordination across multiple devices. Queue is the right tool.

**Implementation:**
```python
@router.post("/bulk-command")
async def bulk_command(request: BulkCommandRequest):
    """Always queue bulk operations"""

    command_ids = []
    for device in request.devices:
        queue_id = await command_queue.enqueue(
            hostname=device.hostname,
            command=request.command,
            box=device.port,
            priority=request.priority or 0,
            batch_id=request.batch_id  # Link related commands
        )
        command_ids.append(queue_id)

    return {
        "success": True,
        "method": "queued",
        "batch_id": request.batch_id,
        "command_ids": command_ids,
        "total_queued": len(command_ids)
    }
```

#### Class D: SYSTEM (Queue Routing - Background Tasks)

**Characteristics:**
- Automated/background operations
- No user waiting
- Can be deferred/scheduled
- Low priority

**Operations:**
- Capability refresh
- Health check sweeps
- Firmware update checks
- Log collection
- Statistics

**Routing Decision:** **QUEUE ONLY (Low Priority)**

**Why:** No user waiting. Should not interfere with user operations. Queue provides scheduling and resource management.

**Implementation:**
```python
@router.post("/system/refresh-capabilities")
async def refresh_all_capabilities():
    """Queue system task with low priority"""

    devices = await get_all_online_devices()

    for device in devices:
        await command_queue.enqueue(
            hostname=device.hostname,
            command="refresh_capabilities",
            priority=-10,  # Low priority
            max_attempts=1,  # Don't retry system tasks aggressively
            scheduled_at=datetime.now() + timedelta(seconds=30)  # Defer
        )

    return {"success": True, "queued_count": len(devices)}
```

---

## Architecture Diagrams

### Current (All Direct)
```
┌─────────┐
│   UI    │
└────┬────┘
     │ Every command goes direct
     ▼
┌─────────────────┐
│  FastAPI        │
│  /command       │
└────┬────────────┘
     │ Direct call
     ▼
┌─────────────────┐
│  ESPHome        │
│  Manager        │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│  ESP Device     │
└─────────────────┘

Problems:
- No retry
- No bulk support
- No scheduling
- No history
```

### Proposed (Hybrid)
```
┌─────────────────────────────────────────────────┐
│                    UI Layer                      │
└──────┬────────────────────────┬─────────────────┘
       │                        │
       │ Class A (ID, Health)   │ Class C (Bulk)
       │ Direct                 │ Queue
       ▼                        ▼
┌──────────────┐         ┌──────────────────┐
│   /diagnostic│         │  /bulk-command   │
│   /health    │         │  /schedule       │
└──────┬───────┘         └────────┬─────────┘
       │                          │
       │                          ▼
       │                 ┌─────────────────────┐
       │                 │  Command Queue      │
       │                 │  (Database)         │
       │                 └──────┬──────────────┘
       │                        │
       │                        ▼
       │                 ┌─────────────────────┐
       │                 │  Queue Processor    │
       │                 │  (Background)       │
       │                 └──────┬──────────────┘
       │                        │
       │ Class B (Single)       │
       │ Smart routing          │
       ▼                        │
┌──────────────────────────────┴────┐
│      ESPHome Manager               │
│      (Connection Pool)             │
└──────────────┬────────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│         ESP Devices              │
└──────────────────────────────────┘

Benefits:
✅ Fast interactive operations
✅ Reliable bulk operations
✅ Retry mechanism
✅ History tracking
✅ Scheduling support
✅ Progress tracking
```

---

## Implementation Details

### 1. Command Queue Schema (Enhanced)

```sql
CREATE TABLE command_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Command details
    hostname VARCHAR NOT NULL,
    command VARCHAR NOT NULL,
    port INTEGER DEFAULT 0,
    channel VARCHAR,
    digit INTEGER,

    -- Classification
    command_class VARCHAR NOT NULL,  -- 'interactive', 'bulk', 'system'
    batch_id VARCHAR,                -- Link related commands

    -- Queue management
    status VARCHAR DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    scheduled_at DATETIME,

    -- Execution tracking
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    last_attempt_at DATETIME,
    completed_at DATETIME,

    -- Results
    success BOOLEAN,
    error_message TEXT,
    execution_time_ms INTEGER,

    -- Routing info
    routing_method VARCHAR,          -- 'direct_success', 'direct_failed_queued', 'queued'

    -- Metadata
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR,
    user_ip VARCHAR,
    notes TEXT,

    -- Indexes
    INDEX idx_status_priority (status, priority DESC),
    INDEX idx_scheduled (scheduled_at),
    INDEX idx_hostname_status (hostname, status),
    INDEX idx_batch (batch_id),
    INDEX idx_created (created_at)
);

-- Separate table for port status (lightweight, frequently read)
CREATE TABLE port_status (
    hostname VARCHAR NOT NULL,
    port INTEGER NOT NULL,
    last_channel VARCHAR,
    last_command VARCHAR,
    last_command_at DATETIME,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (hostname, port)
);

-- Command execution log (for history, partitioned/archived)
CREATE TABLE command_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    queue_id INTEGER,  -- Link to command_queue if queued
    hostname VARCHAR NOT NULL,
    command VARCHAR NOT NULL,
    port INTEGER,
    success BOOLEAN NOT NULL,
    execution_time_ms INTEGER,
    routing_method VARCHAR,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_created (created_at),
    INDEX idx_hostname_created (hostname, created_at)
);
```

### 2. Enhanced ESPHome Manager

```python
class ESPHomeManager:
    """
    Enhanced manager with connection pooling and smart routing
    """

    def __init__(self):
        self.clients: Dict[str, ESPHomeClient] = {}
        self.connection_pool_size = 50
        self.command_queue = CommandQueue()

    async def send_command_smart(
        self,
        hostname: str,
        command: str,
        command_class: str = "interactive",
        **kwargs
    ) -> CommandResult:
        """
        Smart routing based on command class

        Args:
            command_class: 'immediate', 'interactive', 'bulk', or 'system'
        """

        if command_class == "immediate":
            # Direct only, no fallback
            return await self._send_direct(hostname, command, **kwargs)

        elif command_class == "interactive":
            # Try direct first, queue on failure
            try:
                result = await self._send_direct(
                    hostname, command, timeout=3.0, **kwargs
                )
                if result.success:
                    return result
            except (TimeoutError, ConnectionError):
                pass

            # Fallback to queue
            queue_id = await self.command_queue.enqueue(
                hostname=hostname,
                command=command,
                command_class="interactive",
                **kwargs
            )
            return CommandResult(
                success=True,
                method="queued",
                queue_id=queue_id
            )

        elif command_class in ("bulk", "system"):
            # Always queue
            queue_id = await self.command_queue.enqueue(
                hostname=hostname,
                command=command,
                command_class=command_class,
                **kwargs
            )
            return CommandResult(
                success=True,
                method="queued",
                queue_id=queue_id
            )

        else:
            raise ValueError(f"Unknown command class: {command_class}")

    async def _send_direct(
        self,
        hostname: str,
        command: str,
        timeout: float = 5.0,
        **kwargs
    ) -> CommandResult:
        """Direct execution with timeout"""

        device = await self._get_device_info(hostname)
        client = self.get_client(hostname, device.ip_address)

        start_time = time.time()

        try:
            success = await asyncio.wait_for(
                client.call_service(command, kwargs),
                timeout=timeout
            )

            execution_time = (time.time() - start_time) * 1000

            return CommandResult(
                success=success,
                method="direct",
                execution_time_ms=int(execution_time)
            )

        except asyncio.TimeoutError:
            raise TimeoutError(f"Command timed out after {timeout}s")
```

### 3. Queue Processor (Enhanced)

```python
class CommandQueueProcessor:
    """
    Background worker with priority-based processing
    """

    def __init__(self):
        self.poll_interval = 0.5  # 500ms
        self.batch_size = 10
        self.running = False
        self.workers = []
        self.worker_count = 3  # Concurrent workers

    async def start(self):
        """Start multiple worker threads"""
        self.running = True

        # Start worker coroutines
        self.workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.worker_count)
        ]

        logger.info(f"Started {self.worker_count} queue workers")

    async def _worker(self, worker_id: int):
        """Individual worker coroutine"""

        while self.running:
            try:
                # Get highest priority pending command
                cmd = await self._get_next_command()

                if cmd:
                    await self._execute_command(cmd, worker_id)
                else:
                    # No work available, sleep briefly
                    await asyncio.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1.0)

    async def _get_next_command(self) -> Optional[CommandQueue]:
        """
        Get next command to execute (priority-based)

        Priority order:
        1. Interactive commands that failed direct (highest)
        2. Bulk user operations (medium)
        3. System tasks (lowest)
        """

        db = next(get_db())
        try:
            now = datetime.now()

            cmd = db.query(CommandQueue).filter(
                and_(
                    CommandQueue.status == 'pending',
                    CommandQueue.attempts < CommandQueue.max_attempts,
                    or_(
                        CommandQueue.scheduled_at == None,
                        CommandQueue.scheduled_at <= now
                    )
                )
            ).order_by(
                # Priority order
                CommandQueue.priority.desc(),
                CommandQueue.created_at.asc()
            ).with_for_update(skip_locked=True).first()  # Lock for worker

            if cmd:
                cmd.status = 'processing'
                cmd.attempts += 1
                cmd.last_attempt_at = now
                db.commit()

            return cmd

        finally:
            db.close()

    async def _execute_command(self, cmd: CommandQueue, worker_id: int):
        """Execute queued command"""

        logger.info(
            f"Worker {worker_id} executing command {cmd.id}: "
            f"{cmd.command} on {cmd.hostname} (attempt {cmd.attempts})"
        )

        db = next(get_db())
        try:
            device = db.query(Device).filter(
                Device.hostname == cmd.hostname
            ).first()

            if not device:
                raise Exception(f"Device {cmd.hostname} not found")

            start_time = time.time()

            # Execute via ESPHome manager
            success = await esphome_manager.send_tv_command(
                hostname=cmd.hostname,
                ip_address=device.ip_address,
                command=cmd.command,
                box=cmd.port,
                channel=cmd.channel,
                digit=cmd.digit
            )

            execution_time = int((time.time() - start_time) * 1000)

            # Update command record
            cmd.execution_time_ms = execution_time
            cmd.success = success

            if success:
                cmd.status = 'completed'
                cmd.completed_at = datetime.now()

                # Update port status if channel command
                if cmd.command == "channel" and cmd.channel:
                    await self._update_port_status(
                        db, cmd.hostname, cmd.port, cmd.channel
                    )

                # Log to history
                await self._log_to_history(db, cmd, success, execution_time)

            else:
                # Command failed
                if cmd.attempts >= cmd.max_attempts:
                    cmd.status = 'failed'
                    cmd.completed_at = datetime.now()
                    cmd.error_message = "Max retry attempts exceeded"
                else:
                    # Retry
                    cmd.status = 'pending'
                    cmd.error_message = f"Failed attempt {cmd.attempts}, will retry"

                    # Exponential backoff - reschedule
                    backoff_seconds = 2 ** cmd.attempts  # 2, 4, 8 seconds
                    cmd.scheduled_at = datetime.now() + timedelta(
                        seconds=backoff_seconds
                    )

            db.commit()

        except Exception as e:
            logger.error(f"Error executing command {cmd.id}: {e}")

            cmd.error_message = str(e)

            if cmd.attempts >= cmd.max_attempts:
                cmd.status = 'failed'
                cmd.completed_at = datetime.now()
                cmd.success = False
            else:
                cmd.status = 'pending'
                # Backoff and retry
                backoff_seconds = 2 ** cmd.attempts
                cmd.scheduled_at = datetime.now() + timedelta(
                    seconds=backoff_seconds
                )

            db.commit()

        finally:
            db.close()

    async def _update_port_status(
        self,
        db: Session,
        hostname: str,
        port: int,
        channel: str
    ):
        """Update port status table for UI display"""

        status = db.query(PortStatus).filter(
            and_(
                PortStatus.hostname == hostname,
                PortStatus.port == port
            )
        ).first()

        now = datetime.now()

        if status:
            status.last_channel = channel
            status.last_command_at = now
            status.updated_at = now
        else:
            status = PortStatus(
                hostname=hostname,
                port=port,
                last_channel=channel,
                last_command_at=now
            )
            db.add(status)

    async def _log_to_history(
        self,
        db: Session,
        cmd: CommandQueue,
        success: bool,
        execution_time_ms: int
    ):
        """Log completed command to history table"""

        history = CommandHistory(
            queue_id=cmd.id,
            hostname=cmd.hostname,
            command=cmd.command,
            port=cmd.port,
            success=success,
            execution_time_ms=execution_time_ms,
            routing_method=cmd.routing_method
        )
        db.add(history)
```

### 4. API Endpoints (Enhanced)

```python
# Immediate operations (Class A)
@router.post("/{hostname}/diagnostic", tags=["immediate"])
async def diagnostic(hostname: str):
    """Direct diagnostic - no queue"""
    result = await esphome_manager.send_command_smart(
        hostname=hostname,
        command="diagnostic_signal",
        command_class="immediate",
        box=0,
        digit=1
    )
    return result

@router.get("/{hostname}/health", tags=["immediate"])
async def health_check(hostname: str):
    """Direct health check - no queue"""
    result = await esphome_manager.health_check(hostname)
    return {"online": result, "method": "direct"}

# Interactive operations (Class B)
@router.post("/{hostname}/command", tags=["interactive"])
async def send_command(hostname: str, cmd: CommandRequest):
    """Smart routing - direct with queue fallback"""
    result = await esphome_manager.send_command_smart(
        hostname=hostname,
        command=cmd.command,
        command_class="interactive",
        box=cmd.box,
        channel=cmd.channel,
        digit=cmd.digit
    )
    return result

# Bulk operations (Class C)
@router.post("/bulk/command", tags=["bulk"])
async def bulk_command(request: BulkCommandRequest):
    """Always queued - bulk operations"""

    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    command_ids = []

    for target in request.targets:
        queue_id = await command_queue.enqueue(
            hostname=target.hostname,
            command=request.command,
            port=target.port,
            channel=request.channel,
            command_class="bulk",
            batch_id=batch_id,
            priority=5  # Higher than system, lower than interactive fallback
        )
        command_ids.append(queue_id)

    return {
        "batch_id": batch_id,
        "queued_count": len(command_ids),
        "command_ids": command_ids
    }

@router.get("/bulk/{batch_id}/status", tags=["bulk"])
async def bulk_status(batch_id: str):
    """Check bulk operation progress"""

    db = next(get_db())
    commands = db.query(CommandQueue).filter(
        CommandQueue.batch_id == batch_id
    ).all()

    return {
        "batch_id": batch_id,
        "total": len(commands),
        "completed": sum(1 for c in commands if c.status == 'completed'),
        "failed": sum(1 for c in commands if c.status == 'failed'),
        "pending": sum(1 for c in commands if c.status in ('pending', 'processing')),
        "commands": [
            {
                "id": c.id,
                "hostname": c.hostname,
                "status": c.status,
                "success": c.success,
                "attempts": c.attempts
            }
            for c in commands
        ]
    }

# System operations (Class D)
@router.post("/system/refresh-capabilities", tags=["system"])
async def refresh_capabilities():
    """Queue capability refresh for all devices"""

    devices = await get_online_devices()

    for device in devices:
        await command_queue.enqueue(
            hostname=device.hostname,
            command="refresh_capabilities",
            command_class="system",
            priority=-10,  # Low priority
            max_attempts=1
        )

    return {"queued_count": len(devices)}
```

---

## Benefits Analysis

### Hybrid vs All-Direct

| Aspect | All-Direct | Hybrid |
|--------|-----------|--------|
| ID Button Latency | ✅ Fast | ✅ Fast (direct) |
| Single Device Control | ✅ Fast | ✅ Fast (direct + fallback) |
| Bulk Operations | ❌ Slow/Unreliable | ✅ Reliable |
| Retry on Failure | ❌ No | ✅ Yes |
| Progress Tracking | ❌ No | ✅ Yes |
| History | ❌ Limited | ✅ Complete |
| Scheduling | ❌ No | ✅ Yes |

### Hybrid vs All-Queue

| Aspect | All-Queue | Hybrid |
|--------|-----------|--------|
| ID Button Latency | ❌ Slow (queue delay) | ✅ Fast (direct) |
| Single Device Control | 🟡 Slower | ✅ Fast (direct) |
| Bulk Operations | ✅ Reliable | ✅ Reliable |
| System Complexity | 🟡 Higher | 🟡 Moderate |
| Database Load | ❌ Higher | ✅ Lower |
| Debugging | 🟡 Complex | ✅ Clear routing |

---

## Migration Strategy

### Phase 1: Infrastructure (Week 1)
1. Create command_queue, port_status, command_history tables
2. Implement CommandQueue class with enqueue/dequeue
3. Implement QueueProcessor with worker threads
4. Add command classification to CommandRequest model

### Phase 2: Hybrid Routing (Week 2)
1. Implement enhanced ESPHomeManager.send_command_smart()
2. Add Class A endpoints (diagnostic, health) - direct only
3. Add Class B endpoints (command) - smart routing
4. Keep existing endpoints working (backward compatibility)

### Phase 3: Bulk Operations (Week 3)
1. Add Class C endpoints (bulk operations)
2. Implement batch tracking
3. Add progress monitoring endpoints
4. Update UI to show bulk operation progress

### Phase 4: System Tasks (Week 4)
1. Add Class D endpoints (system tasks)
2. Implement capability refresh queue
3. Add scheduled task support
4. Implement 7-day history cleanup job

### Phase 5: Monitoring & Optimization (Week 5)
1. Add queue metrics (length, processing time, success rate)
2. Implement alerting for stuck commands
3. Performance tuning (worker count, batch size)
4. Load testing

---

## Performance Characteristics

### Expected Latencies

| Operation | Current | Hybrid (Direct) | Hybrid (Queued) |
|-----------|---------|----------------|-----------------|
| ID Button | 2-3s | 2-3s | N/A |
| Health Check | 1-2s | 1-2s | N/A |
| Single Power | 2-4s | 2-4s | 5-10s (if fallback) |
| Single Channel | 3-5s | 3-5s | 5-10s (if fallback) |
| Bulk 10 devices | 30-50s | N/A | 10-20s (parallel) |
| Bulk 50 devices | 150-250s | N/A | 30-60s (parallel) |

### Resource Usage

**Direct Only (Current):**
- API Connections: 1 per request
- Database Writes: 0
- Background Threads: 0

**Hybrid (Proposed):**
- API Connections: 1 per request (cached pool)
- Database Writes: Only queued operations
- Background Threads: 3 worker threads
- Database Queries: ~2-5 per second (queue polling)

---

## Failure Scenarios & Handling

### Scenario 1: Device Offline

**Interactive Command (Smart Routing):**
1. Direct call times out (3s)
2. Fallback to queue
3. Queue retries 3x with backoff (2s, 4s, 8s)
4. Total time: 3s + 2s + 4s + 8s = 17s
5. User sees: "Device busy, queued for retry"

**Bulk Command (Always Queued):**
1. Command enters queue immediately
2. Queue worker attempts 3x with backoff
3. Marked as failed after 3 attempts
4. User sees progress: 9/10 completed, 1 failed

### Scenario 2: Queue Processor Down

**Interactive Command:**
- Direct path still works ✅
- Fallback queued commands accumulate
- When processor restarts, processes backlog

**Bulk Command:**
- Commands accumulate in pending state
- When processor restarts, processes by priority
- No data loss

### Scenario 3: Database Down

**Interactive Command:**
- Direct path still works ✅
- Queue fallback fails, returns error
- Graceful degradation to direct-only mode

**Bulk Command:**
- Cannot queue, returns error immediately
- User gets clear error message

### Scenario 4: Network Congestion

**Interactive Command:**
- Direct timeout triggers queue fallback
- Queue processes with backoff
- Adaptive retry timing

**Bulk Command:**
- Queue naturally rate-limits
- Prevents overwhelming network
- Parallel workers (3) limit concurrency

---

## Monitoring & Observability

### Key Metrics

```python
# Real-time metrics
queue_metrics = {
    "pending_count": 42,
    "processing_count": 3,
    "completed_last_hour": 156,
    "failed_last_hour": 4,
    "avg_execution_time_ms": 2450,
    "avg_queue_wait_time_ms": 1200,
    "worker_utilization": 0.73,  # 73% busy
    "oldest_pending_age_seconds": 45
}

# Health checks
@router.get("/queue/health")
async def queue_health():
    db = next(get_db())

    # Check for stuck commands
    stuck_threshold = datetime.now() - timedelta(minutes=5)
    stuck_count = db.query(CommandQueue).filter(
        and_(
            CommandQueue.status == 'processing',
            CommandQueue.last_attempt_at < stuck_threshold
        )
    ).count()

    # Check queue depth
    pending_count = db.query(CommandQueue).filter(
        CommandQueue.status == 'pending'
    ).count()

    healthy = stuck_count == 0 and pending_count < 1000

    return {
        "healthy": healthy,
        "stuck_commands": stuck_count,
        "pending_count": pending_count,
        "warning": "Queue depth high" if pending_count > 500 else None
    }
```

### Logging Strategy

```python
# Structured logging for traceability
logger.info(
    "Command executed",
    extra={
        "command_id": cmd.id,
        "hostname": cmd.hostname,
        "command": cmd.command,
        "routing_method": "direct" or "queued",
        "success": True,
        "execution_time_ms": 2450,
        "attempts": 1,
        "user_ip": request.client.host
    }
)
```

---

## Security Considerations

### Rate Limiting

```python
# Per-user rate limits
@router.post("/{hostname}/command")
@limiter.limit("100/minute")  # Max 100 commands per minute per user
async def send_command(request: Request, hostname: str, cmd: CommandRequest):
    ...

# Global rate limit for queue
@router.post("/bulk/command")
@limiter.limit("10/minute")  # Max 10 bulk operations per minute per user
async def bulk_command(request: Request, bulk: BulkCommandRequest):
    ...
```

### Command Validation

```python
# Validate command parameters
def validate_command(cmd: CommandRequest):
    # Prevent command injection
    if cmd.command not in ALLOWED_COMMANDS:
        raise ValueError(f"Invalid command: {cmd.command}")

    # Validate port range
    if cmd.box and not (0 <= cmd.box <= 5):
        raise ValueError(f"Invalid port: {cmd.box}")

    # Validate channel range
    if cmd.channel and not cmd.channel.isdigit():
        raise ValueError(f"Invalid channel: {cmd.channel}")
```

### Audit Trail

```python
# Complete audit trail in command_history
# - Who sent the command (user_ip)
# - When it was sent (created_at)
# - What happened (success, error_message)
# - How it was routed (routing_method)

# Retention: 7 days for detailed history, 90 days for aggregated stats
```

---

## Conclusion

### Recommendation: HYBRID ARCHITECTURE

**Implement Class-Based Routing:**

- **Class A (Immediate)**: Direct only - ID button, health checks
- **Class B (Interactive)**: Smart routing - single device controls
- **Class C (Bulk)**: Queue only - multi-device operations
- **Class D (System)**: Queue only - background tasks

### Key Benefits

1. ✅ **No Latency Increase** for interactive operations (ID button still fast)
2. ✅ **Reliable Bulk Operations** with progress tracking
3. ✅ **Automatic Retry** for failed commands
4. ✅ **Complete History** for audit and debugging
5. ✅ **Graceful Degradation** when queue is down
6. ✅ **Resource Efficiency** - queue only when needed
7. ✅ **Clear Separation** of concerns

### Implementation Priority

**Phase 1 (Must Have):**
- Command queue infrastructure
- Queue processor with workers
- Class B endpoints (smart routing for single commands)

**Phase 2 (Should Have):**
- Class C endpoints (bulk operations)
- Progress tracking
- Batch operations

**Phase 3 (Nice to Have):**
- Class D endpoints (system tasks)
- Advanced scheduling
- Metrics and monitoring dashboard

### Next Steps

1. Review and approve architectural decision
2. Create detailed tickets for Phase 1
3. Begin implementation of queue infrastructure
4. Maintain backward compatibility during migration
5. Monitor performance in production


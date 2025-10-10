from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.db.database import get_db
from app.models.device_management import ManagedDevice, IRPort, DeviceDiscovery

router = APIRouter(tags=["admin"])


def _serialize_discovered(device: DeviceDiscovery) -> Dict[str, Any]:
    return {
        "id": device.id,
        "hostname": device.hostname,
        "ip_address": device.ip_address,
        "device_type": device.device_type,
        "is_managed": device.is_managed,
        "first_discovered": device.first_discovered.isoformat() if device.first_discovered else None,
        "last_seen": device.last_seen.isoformat() if device.last_seen else None,
        "properties": device.discovery_properties or {},
    }


def _serialize_managed(device: ManagedDevice) -> Dict[str, Any]:
    return {
        "id": device.id,
        "hostname": device.hostname,
        "device_name": device.device_name,
        "location": device.location,
        "total_ir_ports": device.total_ir_ports,
        "is_online": device.is_online,
        "device_type": device.device_type,
        "current_ip": device.current_ip_address,
        "last_seen": device.last_seen.isoformat() if device.last_seen else None,
    }


def _serialize_ir_port(port: IRPort) -> Dict[str, Any]:
    return {
        "id": port.id,
        "device_id": port.device_id,
        "port_number": port.port_number,
        "port_id": port.port_id,
        "gpio_pin": port.gpio_pin,
        "connected_device_name": port.connected_device_name,
        "is_active": port.is_active,
        "device_number": port.device_number,
        "cable_length": port.cable_length,
    }


@router.get("/database-overview")
async def get_database_overview(db: Session = Depends(get_db)):
    """Return a simplified overview of device state for debugging."""

    discovered = db.query(DeviceDiscovery).all()
    managed = db.query(ManagedDevice).all()
    ir_ports = db.query(IRPort).all()

    return {
        "discovered_devices": [_serialize_discovered(d) for d in discovered],
        "managed_devices": [_serialize_managed(m) for m in managed],
        "ir_ports": [_serialize_ir_port(p) for p in ir_ports],
        "statistics": {
            "discovered_devices": len(discovered),
            "managed_devices": len(managed),
            "ir_ports": len(ir_ports),
        },
    }


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(db: Session = Depends(get_db)):
    """Minimal HTML dashboard to inspect current device state."""

    overview = await get_database_overview(db)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>TapCommand Database Admin</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif; margin: 20px; background: #f8fafc; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            .card {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }}
            .stat {{ text-align: center; padding: 15px; background: #f1f5f9; border-radius: 6px; }}
            .stat-number {{ font-size: 24px; font-weight: bold; color: #1e293b; }}
            .stat-label {{ font-size: 12px; color: #64748b; text-transform: uppercase; margin-top: 5px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
            th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
            th {{ background: #f8fafc; font-weight: 600; color: #374151; }}
            .refresh-btn {{ background: #3b82f6; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }}
            .refresh-btn:hover {{ background: #2563eb; }}
            .online {{ color: #10b981; }}
            .offline {{ color: #ef4444; }}
        </style>
        <script>
            function refreshData() {{
                window.location.reload();
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>TapCommand Database Administration</h1>
                <p>Real-time database monitoring and device management overview</p>
                <button class="refresh-btn" onclick="refreshData()">🔄 Refresh Data</button>
            </div>

            <div class="card">
                <h2>Statistics</h2>
                <div class="stats">
                    <div class="stat">
                        <div class="stat-number">{overview['statistics']['discovered_devices']}</div>
                        <div class="stat-label">Discovered Devices</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">{overview['statistics']['managed_devices']}</div>
                        <div class="stat-label">Managed Devices</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">{overview['statistics']['ir_ports']}</div>
                        <div class="stat-label">IR Ports</div>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>Discovered Devices</h2>
                <table>
                    <tr>
                        <th>Hostname</th>
                        <th>IP</th>
                        <th>Type</th>
                        <th>Managed</th>
                    </tr>
                    {''.join([f"<tr><td>{d['hostname']}</td><td>{d['ip_address']}</td><td>{d['device_type'] or 'n/a'}</td><td>{'✅' if d['is_managed'] else '❌'}</td></tr>" for d in overview['discovered_devices']])}
                </table>
            </div>

            <div class="card">
                <h2>Managed Devices</h2>
                <table>
                    <tr>
                        <th>Name</th>
                        <th>Hostname</th>
                        <th>Location</th>
                        <th>Status</th>
                    </tr>
                    {''.join([f"<tr><td>{m['device_name'] or 'n/a'}</td><td>{m['hostname']}</td><td>{m['location'] or 'n/a'}</td><td>{'🟢 Online' if m['is_online'] else '🔴 Offline'}</td></tr>" for m in overview['managed_devices']])}
                </table>
            </div>
        </div>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)

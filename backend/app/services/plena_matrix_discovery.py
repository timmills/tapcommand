"""
Bosch Plena Matrix Discovery Service

Discover and configure Bosch Plena Matrix amplifiers (PLM-4Px2x series)
via UDP API
"""

import asyncio
import logging
import socket
import struct
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session

from ..models.virtual_controller import VirtualController, VirtualDevice
from ..db.database import SessionLocal

logger = logging.getLogger(__name__)


@dataclass
class PlenaMatrixInfo:
    """Information about a Plena Matrix device"""
    device_name: str
    model: str
    firmware_version: str
    total_zones: int
    zones: List[Dict[str, Any]]


class PlenaMatrixDiscoveryService:
    """Discover and configure Plena Matrix amplifiers"""

    # UDP Ports
    RECEIVE_PORT = 12128
    TRANSMIT_PORT = 12129

    # Protocol IDs (from official API manual)
    PROTOCOL_ID_AMPLIFIER = 0x5E41  # PLM-4Px2x amplifiers
    PROTOCOL_ID_MATRIX = 0x5E40     # PLM-8M8 matrix mixer

    # Sub types
    SUBTYPE_MASTER = 0x0001   # Packets from master (us)
    SUBTYPE_SLAVE = 0x0100    # Packets from slave (device)

    # Command types
    CMD_PING = b'PING'
    CMD_WHAT = b'WHAT'  # Get device info
    CMD_EXPL = b'EXPL'  # Get extended info
    CMD_SYNC = b'SYNC'  # Synchronization
    CMD_PASS = b'PASS'  # Password check

    # SYNC types for PLM-4Px2x
    SYNC_TYPE_SYSTEM = 100  # System state, I/O names, global settings
    SYNC_TYPE_PRESETS = 101  # Preset names and validity
    SYNC_TYPE_AUDIO = 102  # All audio parameters

    def __init__(self):
        self._sequence_number = 0

    def _get_next_sequence(self) -> int:
        """Get next sequence number (1-65535, never 0)"""
        self._sequence_number = (self._sequence_number + 1) % 65536
        if self._sequence_number == 0:
            self._sequence_number = 1
        return self._sequence_number

    def _build_packet_header(self, sequence: int, chunk_length: int) -> bytes:
        """
        Build the 10-byte UDP packet header per Plena Matrix API spec

        Returns: [Protocol ID: 2][Sub Type: 2][Sequence: 2][Reserved: 2][Chunk Length: 2]
        """
        return struct.pack(
            '>HHHHH',
            self.PROTOCOL_ID_AMPLIFIER,  # Protocol ID for PLM-4Px2x
            self.SUBTYPE_MASTER,         # We are the master
            sequence,                     # Sequence number
            0x0000,                       # Reserved (always 0)
            chunk_length                  # Length of data after header
        )

    async def ping_device(self, ip_address: str, port: int = RECEIVE_PORT, timeout: float = 2.0) -> bool:
        """
        Ping a Plena Matrix device to check if it's reachable

        Returns:
            True if device responds, False otherwise
        """
        try:
            # Create socket and bind to TRANSMIT_PORT (12129) to receive responses
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', self.TRANSMIT_PORT))  # Bind to port 12129 for receiving
            sock.settimeout(timeout)

            # Build PING packet with proper 10-byte header + 4-byte command
            seq = self._get_next_sequence()
            command_data = self.CMD_PING  # Just "PING", no additional data
            chunk_length = len(command_data)

            # Build complete packet: [10-byte header][4-byte PING command]
            header = self._build_packet_header(seq, chunk_length)
            packet = header + command_data

            # Send ping to RECEIVE_PORT (12128)
            sock.sendto(packet, (ip_address, port))
            logger.debug(f"Sent PING to {ip_address}:{port} (packet: {packet.hex()})")

            # Wait for response on TRANSMIT_PORT (12129)
            response, addr = sock.recvfrom(1024)
            sock.close()

            logger.info(f"✓ Plena Matrix device responded from {addr}: {response.hex()}")
            return True

        except socket.timeout:
            logger.debug(f"Ping timeout for {ip_address}")
            return False
        except Exception as e:
            logger.error(f"Ping error for {ip_address}: {e}")
            return False

    async def get_device_info(self, ip_address: str, port: int = RECEIVE_PORT) -> Optional[Dict[str, Any]]:
        """
        Get device information from Plena Matrix using WHAT command

        Returns:
            Dictionary with device info or None if failed
        """
        try:
            # Create socket and bind to TRANSMIT_PORT (12129) to receive responses
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', self.TRANSMIT_PORT))  # Bind to port 12129 for receiving
            sock.settimeout(3.0)

            # Build WHAT packet with proper header
            seq = self._get_next_sequence()
            command_data = self.CMD_WHAT
            chunk_length = len(command_data)

            header = self._build_packet_header(seq, chunk_length)
            packet = header + command_data

            # Send command to RECEIVE_PORT (12128)
            sock.sendto(packet, (ip_address, port))
            logger.debug(f"Sent WHAT to {ip_address}:{port}")

            # Wait for response on TRANSMIT_PORT (12129)
            response, addr = sock.recvfrom(1024)
            sock.close()

            # Parse response: [10-byte header][4-byte command][data]
            if len(response) < 14:  # Minimum: 10 header + 4 command
                logger.warning(f"Invalid response from {ip_address}")
                return None

            # Parse header
            protocol_id, sub_type, seq_resp, reserved, chunk_length = struct.unpack('>HHHHH', response[0:10])

            # Parse command and data
            cmd = response[10:14]
            data = response[14:] if chunk_length > 4 else b''

            logger.debug(f"Response: protocol={hex(protocol_id)}, cmd={cmd}, data_len={len(data)}")

            # Verify we got a WHAT response
            if cmd != self.CMD_WHAT:
                logger.warning(f"Expected WHAT response, got {cmd}")
                return None

            # Parse WHAT response data (per API manual page 8)
            # Format: firmware(4), MAC(6), IP(4), subnet(4), gateway(4), DHCP(1), custom(1), lockout(1), device_name(32), user_name(81)
            device_info = {
                "ip_address": ip_address,
                "model": "Unknown",
                "firmware_version": "Unknown",
                "total_zones": 4,  # Default for PLM-4Px2x
                "mac_address": None,
                "device_name": None,
                "user_name": None
            }

            if len(data) >= 4:
                # Parse firmware version
                idx = 0
                fw_major = data[idx]
                fw_minor = data[idx+1]
                fw_rev = struct.unpack('>H', data[idx+2:idx+4])[0]
                device_info["firmware_version"] = f"{fw_major}.{fw_minor}.{fw_rev}"
                idx += 4

                # Parse MAC address
                if len(data) >= idx + 6:
                    mac = ':'.join(f'{b:02x}' for b in data[idx:idx+6])
                    device_info["mac_address"] = mac
                    idx += 6

                    # Skip IP, subnet, gateway, DHCP (already know IP)
                    idx += 13  # 4 + 4 + 4 + 1

                    # Parse custom mode byte (determines model)
                    if len(data) >= idx + 1:
                        custom_mode = data[idx]
                        if custom_mode == 0x00:
                            device_info["model"] = "PLM-4P120"  # 125W variant
                        elif custom_mode == 0x01:
                            device_info["model"] = "PLM-4P220"  # 220W variant
                        elif custom_mode == 0x04:
                            device_info["model"] = "PLM-4P125"  # Actually 220W
                        else:
                            device_info["model"] = f"PLM-4Px2x (mode {custom_mode:#04x})"
                        idx += 1

                        # Skip lockout flag
                        idx += 1

                        # Parse device name (32 bytes)
                        if len(data) >= idx + 32:
                            device_name = data[idx:idx+32].rstrip(b'\x00').decode('ascii', errors='ignore')
                            device_info["device_name"] = device_name
                            idx += 32

                            # Parse user name (81 bytes)
                            if len(data) >= idx + 81:
                                user_name = data[idx:idx+81].rstrip(b'\x00').decode('utf-8', errors='ignore')
                                device_info["user_name"] = user_name

            logger.info(f"✓ Retrieved device info from {ip_address}: {device_info['model']} v{device_info['firmware_version']}")
            return device_info

        except Exception as e:
            logger.error(f"Failed to get device info from {ip_address}: {e}")
            return None

    async def get_sync_data(self, ip_address: str, sync_type: int, port: int = RECEIVE_PORT, timeout: float = 5.0) -> Optional[bytes]:
        """
        Request SYNC data from device

        Args:
            ip_address: Device IP
            sync_type: 100 (system), 101 (presets), or 102 (audio params)
            port: UDP port (default 12128)
            timeout: Response timeout

        Returns:
            Raw SYNC response data or None if failed
        """
        try:
            # Create socket and bind to TRANSMIT_PORT (12129) to receive responses
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', self.TRANSMIT_PORT))
            sock.settimeout(timeout)

            # Build SYNC packet: [10-byte header][4-byte SYNC][1-byte type]
            seq = self._get_next_sequence()
            command_data = self.CMD_SYNC + struct.pack('B', sync_type)
            chunk_length = len(command_data)

            header = self._build_packet_header(seq, chunk_length)
            packet = header + command_data

            # Send command
            sock.sendto(packet, (ip_address, port))
            logger.debug(f"Sent SYNC type {sync_type} to {ip_address}:{port}")

            # Wait for response (SYNC responses can be large)
            response, addr = sock.recvfrom(4096)
            sock.close()

            # Parse response header
            if len(response) < 14:
                logger.warning(f"Invalid SYNC response from {ip_address}")
                return None

            protocol_id, sub_type, seq_resp, reserved, chunk_length = struct.unpack('>HHHHH', response[0:10])
            cmd = response[10:14]
            data = response[14:] if chunk_length > 4 else b''

            if cmd != self.CMD_SYNC:
                logger.warning(f"Expected SYNC response, got {cmd}")
                return None

            logger.info(f"✓ Retrieved SYNC type {sync_type} from {ip_address} ({len(data)} bytes)")
            return data

        except socket.timeout:
            logger.warning(f"SYNC type {sync_type} timeout for {ip_address}")
            return None
        except Exception as e:
            logger.error(f"Failed to get SYNC type {sync_type} from {ip_address}: {e}")
            return None

    async def parse_preset_names(self, sync_data: bytes, total_presets: int = 8) -> List[Dict[str, Any]]:
        """
        Parse SYNC Type 101 response to extract preset names

        Args:
            sync_data: Raw SYNC Type 101 response data
            total_presets: Number of presets to parse (typically 4-8)

        Returns:
            List of preset dictionaries with name and validity

        Format: [type byte][preset1: 1 validity + 32 name][preset2: 1 validity + 32 name]...
        Each preset is 33 bytes total
        """
        presets = []

        if not sync_data or len(sync_data) < 1:
            logger.warning("No SYNC data to parse")
            return presets

        try:
            idx = 0
            # Skip first byte (SYNC type echo)
            if len(sync_data) > 0 and sync_data[0] == 101:
                idx = 1

            # Each preset has: validity flag (1 byte) + name (32 bytes UTF-8)
            for preset_num in range(total_presets):
                if idx + 33 > len(sync_data):
                    break

                is_valid = sync_data[idx] != 0
                preset_name = sync_data[idx+1:idx+33].rstrip(b'\x00').decode('utf-8', errors='ignore').strip()
                # Clean non-printable characters
                preset_name = ''.join(c for c in preset_name if c.isprintable())

                presets.append({
                    "preset_number": preset_num + 1,
                    "preset_name": preset_name if preset_name else f"Preset {preset_num + 1}",
                    "is_valid": is_valid,
                    "preset_index": preset_num
                })

                idx += 33

            logger.info(f"✓ Parsed {len(presets)} presets from SYNC data")

        except Exception as e:
            logger.error(f"Failed to parse preset names: {e}")

        return presets

    async def parse_io_names(self, sync_data: bytes) -> Dict[str, List[str]]:
        """
        Parse SYNC Type 100 response to extract I/O names

        Args:
            sync_data: Raw SYNC Type 100 response data

        Returns:
            Dictionary with 'inputs' and 'outputs' lists of names

        Note: For PLM-4Px2x, the response format is:
            - 1 byte: unknown/type
            - 4 x 32 bytes: Input names (MIC 1, MIC 2, etc.)
            - 4 x 32 bytes: Output/Zone names (BAR, POKIES, OUTSIDE, BISTRO)
        """
        io_names = {
            "inputs": [],
            "outputs": []
        }

        if not sync_data or len(sync_data) < 1:
            logger.warning("No SYNC Type 100 data to parse")
            return io_names

        try:
            # Data format is NOT block-aligned! Names wrap across 32-byte boundaries.
            # The data is continuous: [type][all input/output names concatenated]
            # Names are null-terminated strings packed together

            # Skip the type byte (0x64 = SYNC type 100)
            all_names_data = sync_data[1:]

            # Split by null bytes to get individual names
            name_list = []
            current_name = b''
            for byte in all_names_data:
                if byte == 0:
                    if current_name:
                        # Decode and clean the name
                        name = current_name.decode('utf-8', errors='ignore').strip()
                        name = ''.join(c for c in name if c.isprintable())
                        name_list.append(name)
                        current_name = b''
                else:
                    current_name += bytes([byte])

            # Add final name if not null-terminated
            if current_name:
                name = current_name.decode('utf-8', errors='ignore').strip()
                name = ''.join(c for c in name if c.isprintable())
                name_list.append(name)

            # First 4 names are inputs, next 4 are outputs
            for i in range(min(4, len(name_list))):
                io_names["inputs"].append(name_list[i] if name_list[i] else f"Input {i+1}")

            for i in range(4, min(8, len(name_list))):
                io_names["outputs"].append(name_list[i] if name_list[i] else f"Output {i-3}")

            logger.info(f"✓ Parsed {len(io_names['inputs'])} inputs, {len(io_names['outputs'])} outputs from SYNC Type 100")

        except Exception as e:
            logger.error(f"Failed to parse I/O names: {e}")

        return io_names

    async def discover_zones(
        self,
        ip_address: str,
        total_zones: int = 4,
        zone_names: Optional[List[str]] = None,
        port: int = RECEIVE_PORT
    ) -> List[Dict[str, Any]]:
        """
        Discover zones on a Plena Matrix amplifier

        Args:
            ip_address: Amplifier IP address
            total_zones: Number of zones (4 for PLM-4P220/120, 2 for bridged mode)
            zone_names: Optional list of zone names from SYNC Type 100
            port: UDP port

        Returns:
            List of zone dictionaries
        """
        zones = []

        # If zone names not provided, try to get them from SYNC Type 100
        if not zone_names:
            logger.info(f"Fetching zone names via SYNC Type 100 from {ip_address}...")
            sync_data = await self.get_sync_data(ip_address, self.SYNC_TYPE_SYSTEM, port)
            if sync_data:
                io_names = await self.parse_io_names(sync_data)
                zone_names = io_names.get("outputs", [])[:total_zones]
                logger.info(f"✓ Retrieved zone names: {zone_names}")

        # Create zone configurations
        for zone_num in range(1, total_zones + 1):
            zone_index = zone_num - 1

            # Use actual name from device if available, otherwise default
            if zone_names and zone_index < len(zone_names) and zone_names[zone_index]:
                zone_name = zone_names[zone_index]
            else:
                zone_name = f"Zone {zone_num}"

            zone = {
                "zone_number": zone_num,
                "zone_name": zone_name,
                "zone_index": zone_index,  # 0-indexed for API
                "gain_range": [-80.0, 10.0],  # Typical Plena Matrix range
                "supports_mute": True,
                "is_active": True
            }
            zones.append(zone)

        logger.info(f"Discovered {len(zones)} zones on {ip_address}: {[z['zone_name'] for z in zones]}")
        return zones

    def create_virtual_devices_from_zones(
        self,
        db: Session,
        controller: VirtualController,
        zones: List[Dict[str, Any]]
    ) -> List[VirtualDevice]:
        """
        Create VirtualDevice entries for each zone

        Args:
            db: Database session
            controller: Parent VirtualController
            zones: List of zone dictionaries from discover_zones()

        Returns:
            List of created VirtualDevice objects
        """
        devices = []

        for zone in zones:
            # Check if zone already exists
            existing = db.query(VirtualDevice).filter(
                VirtualDevice.controller_id == controller.id,
                VirtualDevice.port_number == zone["zone_number"]
            ).first()

            if existing:
                logger.info(f"Zone {zone['zone_name']} already exists, skipping")
                devices.append(existing)
                continue

            # Get IP and port from controller's connection_config
            controller_config = controller.connection_config or {}
            ip_address = controller_config.get("ip_address", "")
            port = controller_config.get("port", 12128)

            # Create new VirtualDevice for this zone
            device = VirtualDevice(
                controller_id=controller.id,
                port_number=zone["zone_number"],
                device_name=zone["zone_name"],
                device_type="audio_zone",
                protocol="bosch_plena_matrix",
                ip_address=ip_address,
                port=port,
                is_active=zone.get("is_active", True),
                is_online=True,
                connection_config={
                    "zone_index": zone["zone_index"],
                    "gain_range": zone["gain_range"],
                    "supports_mute": zone["supports_mute"]
                },
                cached_volume_level=50,  # Default to 50%
                cached_mute_status=False
            )

            db.add(device)
            devices.append(device)
            logger.info(f"✓ Created zone: {zone['zone_name']}")

        db.commit()
        return devices


async def discover_and_create_plena_matrix_controller(
    ip_address: str,
    controller_name: str,
    port: int = 12128,
    total_zones: int = 4,
    venue_name: Optional[str] = None,
    location: Optional[str] = None
) -> Tuple[VirtualController, List[VirtualDevice]]:
    """
    Discover a Plena Matrix amplifier and create controller + zones

    Args:
        ip_address: Amplifier IP address
        controller_name: Friendly name for the controller
        port: UDP port (default 12128)
        total_zones: Number of zones (4 for PLM-4P220/120)
        venue_name: Optional venue name
        location: Optional location tag

    Returns:
        Tuple of (VirtualController, List[VirtualDevice])

    Raises:
        Exception if discovery or creation fails
    """
    db = SessionLocal()
    discovery = PlenaMatrixDiscoveryService()

    try:
        # Step 1: Ping device
        logger.info(f"Pinging Plena Matrix at {ip_address}...")
        if not await discovery.ping_device(ip_address, port):
            raise Exception(f"Plena Matrix at {ip_address} not responding")

        # Step 2: Get device info
        logger.info(f"Getting device info from {ip_address}...")
        device_info = await discovery.get_device_info(ip_address, port)

        if not device_info:
            logger.warning(f"Could not get device info, using defaults")
            device_info = {
                "model": "PLM-4P220",
                "firmware_version": "Unknown"
            }

        # Step 2a: Get presets (SYNC Type 101)
        logger.info(f"Discovering presets on {ip_address}...")
        preset_data = await discovery.get_sync_data(ip_address, discovery.SYNC_TYPE_PRESETS, port)
        presets = []
        if preset_data:
            presets = await discovery.parse_preset_names(preset_data, total_presets=8)
            logger.info(f"✓ Found {len(presets)} presets")
        else:
            logger.warning(f"Could not retrieve preset information")

        # Step 3: Create Virtual Controller
        controller_id = f"plm-{ip_address.replace('.', '-')}"

        # Check if controller already exists
        existing_controller = db.query(VirtualController).filter(
            VirtualController.controller_id == controller_id
        ).first()

        if existing_controller:
            logger.info(f"Controller {controller_id} already exists, using existing")
            controller = existing_controller
        else:
            # Build connection config with discovered information
            connection_config = {
                "ip_address": ip_address,
                "port": port,
                "mac_address": device_info.get("mac_address"),
                "device_name": device_info.get("device_name"),
                "user_name": device_info.get("user_name"),
                "device_model": device_info.get("model", "PLM-4P220"),
                "firmware_version": device_info.get("firmware_version", "Unknown"),
                "total_zones": total_zones,
                "presets": presets,
                "discovered_at": asyncio.get_event_loop().time()
            }

            controller = VirtualController(
                controller_id=controller_id,
                controller_name=controller_name,
                controller_type="audio",
                protocol="bosch_plena_matrix",
                venue_name=venue_name,
                location=location,
                is_online=True,
                connection_config=connection_config
            )
            db.add(controller)
            db.commit()
            logger.info(f"✓ Created controller: {controller_name}")

        # Step 4: Discover zones
        logger.info(f"Discovering zones on {controller_name}...")
        zones = await discovery.discover_zones(ip_address, total_zones)

        # Step 5: Create Virtual Devices for zones
        devices = discovery.create_virtual_devices_from_zones(db, controller, zones)

        logger.info(f"✅ Successfully configured {controller_name} with {len(devices)} zones")
        # Return controller_id instead of the object to avoid session issues
        return (controller_id, len(devices))

    except Exception as e:
        logger.error(f"Failed to discover Plena Matrix: {e}", exc_info=True)
        db.rollback()
        raise

    finally:
        db.close()

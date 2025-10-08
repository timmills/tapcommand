"""
TV Status Polling Service
Background service to poll network TVs for status updates
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from ..db.database import SessionLocal
from ..models.virtual_controller import VirtualDevice

logger = logging.getLogger(__name__)


class TVStatusPoller:
    """
    Background service to poll network TVs for status

    Polling tiers:
    - Tier 1 (3s): LG webOS, Roku, Hisense (WebSocket/MQTT connections)
    - Tier 2 (5s): Sony Bravia, Philips, Vizio (HTTP polling)
    - Tier 3 (disabled): Samsung Legacy (no status available)
    """

    def __init__(self):
        self.running = False
        self.poll_tasks = {}

    async def start(self):
        """Start polling service"""
        if self.running:
            logger.warning("Status poller already running")
            return

        self.running = True
        logger.info("🔄 Starting TV status polling service")

        # Start polling loop
        asyncio.create_task(self._polling_loop())

    async def stop(self):
        """Stop polling service"""
        self.running = False
        logger.info("⏹️  Stopping TV status polling service")

        # Cancel all poll tasks
        for task in self.poll_tasks.values():
            task.cancel()

        self.poll_tasks.clear()

    async def _polling_loop(self):
        """Main polling loop"""
        while self.running:
            try:
                db = SessionLocal()

                try:
                    # Get all active virtual devices
                    devices = db.query(VirtualDevice).filter(
                        VirtualDevice.is_active == True,
                        VirtualDevice.status_available == True
                    ).all()

                    logger.debug(f"Polling {len(devices)} devices for status")

                    # Poll each device
                    for device in devices:
                        await self._poll_device(device, db)

                finally:
                    db.close()

            except Exception as e:
                logger.error(f"Error in polling loop: {e}")

            # Wait before next poll cycle
            await asyncio.sleep(3)  # Poll every 3 seconds

    async def _poll_device(self, device: VirtualDevice, db: Session):
        """Poll a single device for status"""
        try:
            # Determine polling interval based on protocol
            interval = self._get_poll_interval(device.protocol)

            # Check if enough time has passed since last poll
            if device.last_status_poll:
                elapsed = (datetime.now() - device.last_status_poll).total_seconds()
                if elapsed < interval:
                    return  # Skip this poll

            # Poll based on protocol
            status = await self._poll_by_protocol(device)

            if status:
                # Update cache
                self._update_status_cache(device, status, db)

                # Reset failure count
                device.status_poll_failures = 0
            else:
                # Increment failure count
                device.status_poll_failures = (device.status_poll_failures or 0) + 1

                # If too many failures, mark as offline
                if device.status_poll_failures >= 3:
                    device.is_online = False
                    logger.warning(f"Device {device.device_name} marked offline after 3 failed polls")

            # Update last poll time
            device.last_status_poll = datetime.now()
            db.commit()

        except Exception as e:
            logger.error(f"Error polling device {device.device_name}: {e}")
            device.status_poll_failures = (device.status_poll_failures or 0) + 1
            db.commit()

    def _get_poll_interval(self, protocol: str) -> int:
        """Get polling interval in seconds based on protocol"""
        tier1 = ["lg_webos", "roku", "hisense_vidaa"]  # 3 seconds
        tier2 = ["sony_bravia", "vizio_smartcast", "philips_jointspace"]  # 5 seconds

        if protocol in tier1:
            return 3
        elif protocol in tier2:
            return 5
        else:
            return 10  # Default

    async def _poll_by_protocol(self, device: VirtualDevice) -> Optional[Dict[str, Any]]:
        """
        Poll device status based on protocol

        Returns dict with status info or None if failed
        """
        protocol = device.protocol

        try:
            if protocol == "hisense_vidaa":
                return await self._poll_hisense(device)
            elif protocol == "lg_webos":
                return await self._poll_lg_webos(device)
            elif protocol == "sony_bravia":
                return await self._poll_sony(device)
            elif protocol == "roku":
                return await self._poll_roku(device)
            elif protocol == "vizio_smartcast":
                return await self._poll_vizio(device)
            elif protocol == "philips_jointspace":
                return await self._poll_philips(device)
            else:
                return None

        except Exception as e:
            logger.error(f"Error polling {protocol} device: {e}")
            return None

    async def _poll_hisense(self, device: VirtualDevice) -> Optional[Dict[str, Any]]:
        """Poll Hisense TV for status"""
        try:
            from hisensetv import HisenseTv

            tv = HisenseTv(
                hostname=device.ip_address,
                port=36669,
                username="hisenseservice",
                password="multimqttservice"
            )

            # Get volume
            volume_info = tv.get_volume()
            # volume_info = {"volume_type": 0, "volume_value": 25}

            # Get state (includes current source)
            state_info = tv.get_state()
            # state_info = {"statetype": "sourceswitch", "sourceid": "3", "sourcename": "HDMI 1"}

            return {
                "power": "on",  # If we can connect, TV is on
                "volume": volume_info.get("volume_value") if volume_info else None,
                "muted": volume_info.get("volume_value") == -1 if volume_info else None,
                "input": state_info.get("sourcename") if state_info else None,
                "app": None  # Hisense doesn't provide app info reliably
            }

        except Exception as e:
            logger.debug(f"Hisense poll failed: {e}")
            return None

    async def _poll_lg_webos(self, device: VirtualDevice) -> Optional[Dict[str, Any]]:
        """Poll LG webOS TV for status"""
        try:
            from pywebostv.connection import WebOSClient
            from pywebostv.controls import MediaControl, SystemControl, InputControl, ApplicationControl

            # Note: This requires pairing key from connection_config
            pairing_key = None
            if device.connection_config and isinstance(device.connection_config, dict):
                pairing_key = device.connection_config.get("pairing_key")

            client = WebOSClient(device.ip_address, secure=False)
            # Store pairing key if provided
            if pairing_key:
                client.client_key = pairing_key

            client.connect()

            media = MediaControl(client)
            system = SystemControl(client)
            inputs = InputControl(client)
            apps = ApplicationControl(client)

            # Get volume
            volume_info = media.get_volume()
            # {"volume": 25, "muted": false}

            # Get current input
            current_input = inputs.get_input()
            # {"id": "HDMI_1", "label": "HDMI 1"}

            # Get current app
            current_app = apps.get_current()
            # {"id": "netflix", "title": "Netflix"}

            # Get power state
            power_state = system.get_power_state()
            # {"state": "Active"}

            # Try to get channel info if watching TV
            channel_info = None
            try:
                # If current app is LiveTV, try to get channel
                if current_app and current_app.get("id") == "com.webos.app.livetv":
                    # LG webOS provides channel through TV control
                    from pywebostv.controls import TvControl
                    tv = TvControl(client)
                    channel_info = tv.get_current_channel()
                    # Returns channel number if available
            except:
                pass  # Channel info not available

            return {
                "power": power_state.get("state", "unknown").lower() if power_state else "unknown",
                "volume": volume_info.get("volume") if volume_info else None,
                "muted": volume_info.get("muted") if volume_info else None,
                "input": current_input.get("label") if current_input else None,
                "app": current_app.get("title") if current_app else None,
                "channel": channel_info.get("channelNumber") if channel_info else None
            }

        except Exception as e:
            logger.debug(f"LG webOS poll failed: {e}")
            return None

    async def _poll_sony(self, device: VirtualDevice) -> Optional[Dict[str, Any]]:
        """Poll Sony Bravia TV for status"""
        try:
            import requests

            # Get PSK from connection_config
            psk = "0000"  # Default
            if device.connection_config and isinstance(device.connection_config, dict):
                psk = device.connection_config.get("psk", "0000")

            headers = {
                "X-Auth-PSK": psk,
                "Content-Type": "application/json"
            }

            # Get power state
            power_response = requests.post(
                f"http://{device.ip_address}/sony/system",
                headers=headers,
                json={"method": "getPowerStatus", "version": "1.0", "id": 1, "params": []},
                timeout=3
            )
            power_data = power_response.json()
            power_state = power_data.get("result", [{}])[0].get("status", "unknown")

            # Get volume
            volume_response = requests.post(
                f"http://{device.ip_address}/sony/audio",
                headers=headers,
                json={"method": "getVolumeInformation", "version": "1.0", "id": 1, "params": []},
                timeout=3
            )
            volume_data = volume_response.json()
            volume_info = volume_data.get("result", [[]])[0]
            speaker_info = next((v for v in volume_info if v.get("target") == "speaker"), {}) if volume_info else {}

            # Get current input
            input_response = requests.post(
                f"http://{device.ip_address}/sony/avContent",
                headers=headers,
                json={"method": "getPlayingContentInfo", "version": "1.0", "id": 1, "params": []},
                timeout=3
            )
            input_data = input_response.json()
            input_info = input_data.get("result", [{}])[0]

            return {
                "power": power_state.lower(),
                "volume": speaker_info.get("volume"),
                "muted": speaker_info.get("mute"),
                "input": input_info.get("title"),
                "app": None  # Sony doesn't provide app info easily
            }

        except Exception as e:
            logger.debug(f"Sony poll failed: {e}")
            return None

    async def _poll_roku(self, device: VirtualDevice) -> Optional[Dict[str, Any]]:
        """Poll Roku device for status"""
        try:
            import requests
            import xml.etree.ElementTree as ET

            # Get device info (includes power state)
            device_info_response = requests.get(
                f"http://{device.ip_address}:8060/query/device-info",
                timeout=2
            )
            device_info_xml = ET.fromstring(device_info_response.text)
            power_mode = device_info_xml.find("power-mode")
            power_state = power_mode.text if power_mode is not None else "unknown"

            # Get active app
            active_app_response = requests.get(
                f"http://{device.ip_address}:8060/query/active-app",
                timeout=2
            )
            active_app_xml = ET.fromstring(active_app_response.text)
            app_element = active_app_xml.find("app")
            app_name = app_element.text if app_element is not None else None

            return {
                "power": power_state.lower(),
                "volume": None,  # Roku doesn't provide volume query
                "muted": None,
                "input": None,  # Roku is streaming only
                "app": app_name
            }

        except Exception as e:
            logger.debug(f"Roku poll failed: {e}")
            return None

    async def _poll_vizio(self, device: VirtualDevice) -> Optional[Dict[str, Any]]:
        """Poll Vizio SmartCast TV for status"""
        try:
            from pyvizio import Vizio

            # Get auth token from connection_config
            auth_token = None
            if device.connection_config and isinstance(device.connection_config, dict):
                auth_token = device.connection_config.get("auth_token")

            if not auth_token:
                logger.warning(f"Vizio device {device.device_name} missing auth token")
                return None

            tv = Vizio(device.ip_address, auth_token)

            # Get power state
            power_state = tv.get_power_state()  # Returns 1 (on) or 0 (off)

            # Get volume
            volume = tv.get_current_volume()  # Returns 0-100

            # Get current input
            current_input = tv.get_current_input()  # Returns {"name": "HDMI-1", ...}

            return {
                "power": "on" if power_state == 1 else "off",
                "volume": volume,
                "muted": None,  # Vizio may not provide this easily
                "input": current_input.get("name") if current_input else None,
                "app": None
            }

        except Exception as e:
            logger.debug(f"Vizio poll failed: {e}")
            return None

    async def _poll_philips(self, device: VirtualDevice) -> Optional[Dict[str, Any]]:
        """Poll Philips Android TV for status"""
        try:
            import requests

            # Try port 1926 first (Android), fallback to 1925
            ports = [1926, 1925]
            protocols = ["https", "http"]

            for port, protocol in zip(ports, protocols):
                try:
                    base_url = f"{protocol}://{device.ip_address}:{port}"

                    # Get power state
                    power_response = requests.get(
                        f"{base_url}/6/powerstate",
                        timeout=2,
                        verify=False
                    )
                    power_data = power_response.json()
                    power_state = power_data.get("powerstate", "unknown")

                    # Get volume
                    volume_response = requests.get(
                        f"{base_url}/6/audio/volume",
                        timeout=2,
                        verify=False
                    )
                    volume_data = volume_response.json()

                    # Get current source
                    source_response = requests.get(
                        f"{base_url}/6/sources/current",
                        timeout=2,
                        verify=False
                    )
                    source_data = source_response.json()

                    return {
                        "power": power_state.lower(),
                        "volume": volume_data.get("current"),
                        "muted": volume_data.get("muted"),
                        "input": source_data.get("name"),
                        "app": None
                    }

                except:
                    continue  # Try next port

            return None

        except Exception as e:
            logger.debug(f"Philips poll failed: {e}")
            return None

    def _update_status_cache(self, device: VirtualDevice, status: Dict[str, Any], db: Session):
        """Update device status cache"""
        device.cached_power_state = status.get("power")
        device.cached_volume_level = status.get("volume")
        device.cached_mute_status = status.get("muted")
        device.cached_current_input = status.get("input")
        device.cached_current_app = status.get("app")
        device.is_online = True

        # Update channel if provided by the TV API
        if status.get("channel"):
            device.cached_current_channel = status.get("channel")

        logger.debug(f"Updated status for {device.device_name}: {status}")


# Global poller instance
tv_status_poller = TVStatusPoller()

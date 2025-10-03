# ESPHome Profiles

## esp_multi_report.yaml

Production firmware clone that exposes an API service for reporting its supported brands and commands. Key additions:

- `report_capabilities` ESPHome service calls a script that publishes the JSON payload to an internal text sensor.
- The backend now calls that service during device adoption and caches the payload in the discovery table.
- Capability payload includes top-level device metadata plus a `commands` list (`power`, `mute`, `number_0`… etc.).

### Compile

```bash
source ../venv/bin/activate
esphome compile esp_multi_report.yaml
```

Artifacts land in `.esphome/build/ir/.pioenvs/ir/`.

### Manual Testing

Use `aioesphomeapi` to connect and execute the service manually:

```python
from aioesphomeapi import APIClient
import asyncio

async def fetch():
    client = APIClient(address="<ip>", port=6053, password="", noise_psk="<psk>")
    await client.connect(login=True)
    entities, services = await client.list_entities_services()
    service = next(s for s in services if s.name == "report_capabilities")
    payload = {}
    def cb(state):
        if getattr(state, "object_id", "") == "ir_capabilities_payload":
            payload["data"] = state.state
    client.subscribe_states(cb)
    client.execute_service(service, {})
    await asyncio.sleep(5)
    await client.disconnect()
    return payload.get("data")

asyncio.run(fetch())
```

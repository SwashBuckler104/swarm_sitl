#!/usr/bin/env python3
import asyncio
from mavsdk import System
from mavsdk import mission_raw

WPL_PATH = "missions/drone1.wpl"
SYSTEM_ADDRESS = "udpin://127.0.0.1:14550"  # ArduPilot SITL default


def load_wpl_as_raw_items(path):
    from mavsdk import mission_raw
    items = []
    with open(path, "r") as f:
        lines = [l.strip() for l in f if l.strip()]
    if not lines or not lines[0].upper().startswith("QGC WPL"):
        raise RuntimeError("Invalid WPL header (expected 'QGC WPL 110')")
    for line in lines[1:]:
        # Accept any whitespace (tabs or spaces)
        parts = line.split()
        if len(parts) < 12:
            raise RuntimeError(f"Malformed WPL line: {line}")
        seq = int(parts[0])
        current = int(parts[1])
        frame = int(parts[2])
        cmd = int(parts[3])
        p1 = float(parts[4]); p2 = float(parts[5]); p3 = float(parts[6]); p4 = float(parts[7])
        lat = float(parts[8]); lon = float(parts[9]); alt = float(parts[10])
        autocontinue = int(parts[11])

        # ArduPilot prefers ITEM_INT semantics; ensure frame is an INT-capable frame if needed
        # Common: 3 == MAV_FRAME_GLOBAL_RELATIVE_ALT (works fine with INT items)
        # Lat/lon scaled by 1e7 for INT
        items.append(mission_raw.MissionItem(
            seq,
            frame,
            cmd,
            current,
            autocontinue,
            p1, p2, p3, p4,
            int(lat * 1e7),
            int(lon * 1e7),
            float(alt),
            0  # MAV_MISSION_TYPE_MISSION
        ))
    return items

async def connect_vehicle():
    drone = System()
    await drone.connect(system_address=SYSTEM_ADDRESS)
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("-- Connected")
            return drone
    raise RuntimeError("Not connected")

async def wait_ready(drone):
    # Wait for global position and home position like QGC before arming
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("-- Global position and home OK")
            return

async def main():
    drone = await connect_vehicle()
    # Build mission items from WPL
    items = load_wpl_as_raw_items(WPL_PATH)
    if not items:
        raise RuntimeError("No mission items loaded")
    print(f"-- Uploading mission with {len(items)} items")
    await drone.mission_raw.upload_mission(items)
    print("-- Mission uploaded")

    # Ensure readiness similar to QGC
    await wait_ready(drone)

    # Arm and start mission
    print("-- Arming")
    await drone.action.arm()
    print("-- Starting mission")
    await drone.mission_raw.start_mission()
    print("-- Mission started")

if __name__ == "__main__":
    asyncio.run(main())
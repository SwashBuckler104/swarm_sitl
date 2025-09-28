#!/usr/bin/env python3
"""
upload_swarm.py
Uploads a mission to multiple SITL drones using MAVSDK / UDP connections.
"""

import asyncio
from mavsdk import System

# List of drone UDP endpoints
DRONES = [
    "udpin://127.0.0.1:14550?localport=50050",
    "udpin://127.0.0.1:14551?localport=50051",
    "udpin://127.0.0.1:14552?localport=50052",
    "udpin://127.0.0.1:14553?localport=50053"
]

# Example mission items (replace with your mission)
MISSION_ITEMS = [
    {
        "latitude_deg": 12.935,
        "longitude_deg": 77.610,
        "relative_altitude_m": 20,
        "speed_m_s": 5,
        "is_fly_through": True
    },
    {
        "latitude_deg": 12.936,
        "longitude_deg": 77.611,
        "relative_altitude_m": 20,
        "speed_m_s": 5,
        "is_fly_through": True
    }
]

async def upload_mission(drone, sysid):
    print(f"[Drone {sysid}] Connecting to {DRONES[sysid]}...")
    await drone.connect(system_address=DRONES[sysid])

    # Wait for heartbeat
    print(f"[Drone {sysid}] Waiting for heartbeat...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print(f"[Drone {sysid}] Connected!")
            break

    # Convert mission items to MAVSDK format
    from mavsdk.mission import MissionItem
    mission = []
    for item in MISSION_ITEMS:
        mission.append(
            MissionItem(
                latitude_deg=item["latitude_deg"],
                longitude_deg=item["longitude_deg"],
                relative_altitude_m=item["relative_altitude_m"],
                speed_m_s=item["speed_m_s"],
                is_fly_through=item["is_fly_through"],
                gimbal_pitch_deg=0,
                gimbal_yaw_deg=0,
                camera_action=MissionItem.CameraAction.NONE
            )
        )

    # Upload mission
    print(f"[Drone {sysid}] Uploading mission...")
    await drone.mission.upload_mission(mission)
    print(f"[Drone {sysid}] Mission uploaded successfully!")

async def main():
    drones = [System() for _ in DRONES]
    tasks = [upload_mission(drone, i) for i, drone in enumerate(drones)]
    await asyncio.gather(*tasks)
    print("All missions uploaded!")

if __name__ == "__main__":
    asyncio.run(main())

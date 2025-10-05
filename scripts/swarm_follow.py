#!/usr/bin/env python3
from pymavlink import mavutil
import time

# --- CONNECTION SETTINGS ---
LEADER_URI = "udp:127.0.0.1:14551"

# follower connections and SYSIDs
FOLLOWERS = [
    ("udp:127.0.0.1:14561", 2),
    ("udp:127.0.0.1:14571", 3),
    ("udp:127.0.0.1:14581", 4),
]

# offsets (x, y, z) in meters for each follower
OFFSETS = [
    (0, 0, 0),
    (0, 0, 0),
    (0, 0, 0),
]

UPDATE_HZ = 10


def connect(uri, name):
    print(f"[+] Connecting {name} -> {uri}")
    c = mavutil.mavlink_connection(uri)
    c.wait_heartbeat()
    print(f"[+] Heartbeat received from {name}")
    return c


def send_local_position_target(conn, sysid, x, y, z):
    time_boot_ms = int((time.time() * 1000) % 0xFFFFFFFF)  # ✅ fixed timestamp
    conn.mav.set_position_target_local_ned_send(
        time_boot_ms,
        sysid,  # target_system
        0,      # target_component
        mavutil.mavlink.MAV_FRAME_LOCAL_NED,
        0b0000111111111000,  # type_mask (only position enabled)
        x, y, z,  # position
        0, 0, 0,  # velocity
        0, 0, 0,  # acceleration
        0, 0      # yaw, yaw_rate
    )


def main():
    leader = connect(LEADER_URI, "LEADER")
    followers = [(connect(uri, f"FOLL_{sysid}"), sysid, offs)
                 for (uri, sysid), offs in zip(FOLLOWERS, OFFSETS)]

    print("[+] Entering follow loop (CTRL+C to stop)")
    dt = 1 / UPDATE_HZ

    try:
        while True:
            msg = leader.recv_match(type="LOCAL_POSITION_NED", blocking=True, timeout=1)
            if not msg:
                continue

            lx, ly, lz = msg.x, msg.y, msg.z

            for conn, sysid, (dx, dy, dz) in followers:
                send_local_position_target(conn, sysid, lx + dx, ly + dy, lz + dz)

            time.sleep(dt)
    except KeyboardInterrupt:
        print("\n[!] Stopping follower relay.")


if __name__ == "__main__":
    main()

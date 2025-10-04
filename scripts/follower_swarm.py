#!/usr/bin/env python3
import time
from pymavlink import mavutil
import math

# -----------------------------
# UDP connections to each SITL drone
# Adjust ports to match your sim_vehicle.py output
# -----------------------------

def connect_mavlink(uri, sysid_name=""):
    print(f"Connecting to {sysid_name} at {uri}...")
    conn = mavutil.mavlink_connection(uri)
    # Retry loop until heartbeat is received
    while True:
        try:
            hb = conn.recv_match(type='HEARTBEAT', blocking=True, timeout=1)
            if hb:
                print(f"Heartbeat received from {sysid_name}")
                break
        except:
            pass
        time.sleep(0.5)
    return conn

# master = mavutil.mavlink_connection('tcp:127.0.0.1:5760')  # SYSID 1
# follower2 = mavutil.mavlink_connection('tcp:127.0.0.1:5770')  # SYSID 2
# follower3 = mavutil.mavlink_connection('tcp:127.0.0.1:5780')  # SYSID 3
# follower4 = mavutil.mavlink_connection('tcp:127.0.0.1:5790')  # SYSID 4


master = mavutil.mavlink_connection('tcp:127.0.0.1:14550')  # SYSID 1
follower2 = mavutil.mavlink_connection('tcp:127.0.0.1:14551')  # SYSID 2
follower3 = mavutil.mavlink_connection('tcp:127.0.0.1:14552')  # SYSID 3
follower4 = mavutil.mavlink_connection('tcp:127.0.0.1:14553')  # SYSID 4


followers = [
    (follower2, 2, (0, -2)),  # 2 m behind master
    (follower3, 3, (2, -2)),  # 2 m behind, 2 m right
    (follower4, 4, (-2, -2)), # 2 m behind, 2 m left
]

# Wait for heartbeats
print("Waiting for heartbeats...")
for v in [master, follower2, follower3, follower4]:
    v.wait_heartbeat()
print("All vehicles connected!")

# Simple conversion from meters to latitude/longitude offsets
def offset_latlon(lat, lon, north_m, east_m):
    R = 6378137.0  # Earth radius in meters
    dLat = north_m / R
    dLon = east_m / (R * math.cos(math.pi * lat / 180))
    return lat + (dLat * 180 / math.pi), lon + (dLon * 180 / math.pi)

# Send position to follower
def send_position(follower, sysid, lat, lon, alt):
    follower.mav.set_position_target_global_int_send(
        int(time.time() * 1000),  # timestamp ms
        sysid,                    # target system
        0,                        # target component
        mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
        0b110111111000,           # type mask: pos only
        int(lat * 1e7), int(lon * 1e7), int(alt * 1000),
        0,0,0,0,0,0,0,0
    )

# Main loop
try:
    while True:
        msg = master.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
        if not msg:
            continue

        master_lat = msg.lat / 1e7
        master_lon = msg.lon / 1e7
        master_alt = msg.relative_alt / 1000.0

        # Update followers
        for follower, sysid, (dx, dy) in followers:
            lat, lon = offset_latlon(master_lat, master_lon, dx, dy)
            send_position(follower, sysid, lat, lon, master_alt)

        time.sleep(0.1)  # 10 Hz update

except KeyboardInterrupt:
    print("Stopping swarm bridge.")

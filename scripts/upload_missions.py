#!/usr/bin/env python3
import time, sys
from pymavlink import mavutil, mavwp

# Choose one of these based on how SITL is launched:
# SITL_CONNECTION = "tcp:127.0.0.1:5760"      # if sim_vehicle --no-mavproxy (default TCP server)
SITL_CONNECTION = "udp:127.0.0.1:14550"   # if using MAVProxy hub and a dedicated output for the script

WPL_FILE = "missions/drone1_takeoff.wpl"    # or missions/drone1.wpl if using guided takeoff from QGC
ITEM_TIMEOUT_S = 2.0
MAX_RETRIES = 5

def wait_heartbeat(master, timeout=10):
    if master.wait_heartbeat(timeout=timeout) is None:
        raise TimeoutError("No heartbeat from vehicle")
    print(f"Heartbeat OK: sys={master.target_system} comp={master.target_component}")

def wait_home_or_position(master, timeout=30):
    t0 = time.time()
    got_home = False
    have_pos = False
    try:
        master.mav.request_data_stream_send(master.target_system, master.target_component,
                                            mavutil.mavlink.MAV_DATA_STREAM_POSITION, 4, 1)
    except Exception:
        pass
    while time.time() - t0 < timeout:
        msg = master.recv_match(type=['HOME_POSITION','GPS_RAW_INT','EKF_STATUS_REPORT','STATUSTEXT'],
                                blocking=True, timeout=1)
        if not msg:
            continue
        t = msg.get_type()
        if t == 'HOME_POSITION':
            got_home = True
            print("HOME_POSITION received")
        elif t == 'GPS_RAW_INT':
            if getattr(msg, 'fix_type', 0) >= 3:
                have_pos = True
        elif t == 'EKF_STATUS_REPORT':
            if getattr(msg, 'flags', 0) != 0:
                have_pos = True
        elif t == 'STATUSTEXT':
            print(msg)
        if got_home or have_pos:
            print("Ready to upload mission")
            return
    print("Proceeding without full readiness (timeout)")

def upload_mission(master, path):
    loader = mavwp.MAVWPLoader()
    count = loader.load(path)
    if count <= 0:
        raise RuntimeError("Mission file has zero items")
    print(f"Loaded mission: {count} items from {path}")

    master.waypoint_clear_all_send()
    time.sleep(0.2)
    master.waypoint_count_send(count)

    retries = 0
    while True:
        msg = master.recv_match(type=['MISSION_REQUEST','MISSION_REQUEST_INT','MISSION_ACK'],
                                blocking=True, timeout=ITEM_TIMEOUT_S)
        if msg is None:
            if retries >= MAX_RETRIES:
                raise TimeoutError("Mission upload timeout")
            retries += 1
            print(f"Timeout waiting for request/ack, retry {retries}/{MAX_RETRIES}")
            master.waypoint_count_send(count)
            continue

        m = msg.to_dict()
        if m['mavpackettype'] == 'MISSION_ACK':
            result = m.get('type')
            print(f"Got MISSION_ACK type={result}")
            if result == mavutil.mavlink.MAV_MISSION_ACCEPTED:
                print("Mission upload successful")
                return
            raise RuntimeError(f"Mission upload failed with ACK type={result}")

        seq = m.get('seq')
        if seq is None or not (0 <= seq < count):
            raise RuntimeError(f"Bad MISSION_REQUEST: {m}")

        master.mav.send(loader.wp(seq))
        print(f"Sent waypoint {seq}/{count-1}")

def main():
    master = mavutil.mavlink_connection(SITL_CONNECTION)
    wait_heartbeat(master)
    wait_home_or_position(master, timeout=30)
    upload_mission(master, WPL_FILE)
    print("Done. Use QGC to arm and fly the mission.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

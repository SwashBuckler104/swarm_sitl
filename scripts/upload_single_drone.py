#!/usr/bin/env python3
import time
import sys
from pymavlink import mavutil, mavwp

# ---------------- CONFIG ----------------
WPL_FILE = "missions/drone1_takeoff.wpl"   # QGC WPL 110 mission file
SITL_CONNECTION = "tcp:127.0.0.1:5760"     # Match SITL --out or default TCP server
TIMEOUT_S = 5.0                            # General wait timeout
ITEM_TIMEOUT_S = 2.0                       # Per mission item request timeout
MAX_RETRIES = 5                            # Resend count limit for mission upload
GUIDED_TAKEOFF_ALT_M = 30.0                # Altitude for guided takeoff fallback
# ---------------------------------------

def wait_heartbeat(master, timeout=10):
    hb = master.wait_heartbeat(timeout=timeout)
    if hb is None:
        raise TimeoutError("No heartbeat received from vehicle")
    print(f"Heartbeat OK: sys={master.target_system} comp={master.target_component}")

def wait_home_and_position(master, timeout=45):
    t0 = time.time()
    got_home = False
    have_pos = False
    try:
        master.mav.request_data_stream_send(master.target_system, master.target_component,
                                            mavutil.mavlink.MAV_DATA_STREAM_POSITION, 4, 1)
    except Exception:
        pass
    while time.time() - t0 < timeout:
        msg = master.recv_match(type=['HOME_POSITION', 'GPS_RAW_INT', 'EKF_STATUS_REPORT', 'STATUSTEXT'], blocking=True, timeout=1)
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
            flags = getattr(msg, 'flags', 0)
            if flags != 0:
                have_pos = True
        elif t == 'STATUSTEXT':
            print(msg)
        if got_home or have_pos:
            print("Home/position readiness satisfied")
            return
    raise TimeoutError("Home/position not ready in time")

def set_mode(master, mode_name):
    modes = master.mode_mapping()
    if mode_name not in modes:
        raise RuntimeError(f"Unknown mode {mode_name}, available: {list(modes.keys())}")
    mode_id = modes[mode_name]
    master.set_mode(mode_id)
    ack = master.recv_match(type='COMMAND_ACK', blocking=True, timeout=TIMEOUT_S)
    if ack:
        a = ack.to_dict()
        if a.get('command') == mavutil.mavlink.MAV_CMD_DO_SET_MODE:
            print(f"Mode change result: {a.get('result')}")

def arm_and_wait(master, timeout=30):
    master.arducopter_arm()
    print("Arming...")
    t0 = time.time()
    while time.time() - t0 < timeout:
        if master.motors_armed():
            print("Armed")
            return
        time.sleep(0.2)
    raise TimeoutError("Motors failed to arm within timeout")

def upload_mission(master, wpl_path):
    loader = mavwp.MAVWPLoader()
    count = loader.load(wpl_path)
    if count <= 0:
        raise RuntimeError("Mission file has zero items")
    print(f"Loaded mission: {count} items from {wpl_path}")

    # Clear existing mission and send count
    master.waypoint_clear_all_send()
    time.sleep(0.5)
    master.waypoint_count_send(count)

    sent = set()
    retries = 0
    while True:
        msg = master.recv_match(type=['MISSION_REQUEST', 'MISSION_REQUEST_INT', 'MISSION_ACK'], blocking=True, timeout=ITEM_TIMEOUT_S)
        if msg is None:
            if retries >= MAX_RETRIES:
                raise TimeoutError("Mission upload timeout waiting for requests/ACK")
            retries += 1
            print(f"Timeout waiting for MISSION_REQUEST/ACK, retry {retries}/{MAX_RETRIES}")
            master.waypoint_count_send(count)
            continue

        m = msg.to_dict()
        pkt = m.get('mavpackettype')
        if pkt == 'MISSION_ACK':
            result = m.get('type')
            print(f"Got MISSION_ACK type={result} ({'MAV_MISSION_ACCEPTED' if result == mavutil.mavlink.MAV_MISSION_ACCEPTED else 'Error'})")
            if result == mavutil.mavlink.MAV_MISSION_ACCEPTED:
                print("Mission upload successful")
                break
            else:
                raise RuntimeError(f"Mission upload failed with ACK type={result}")

        seq = m.get('seq')
        if seq is None or not (0 <= seq < count):
            raise RuntimeError(f"Bad MISSION_REQUEST: {m}")

        wp_item = loader.wp(seq)
        master.mav.send(wp_item)
        sent.add(seq)
        retries = 0
        print(f"Sent waypoint {seq}/{count-1}")

    return loader

def mission_starts_with_takeoff(loader):
    try:
        first = loader.wp(0)
        return getattr(first, 'command', None) == mavutil.mavlink.MAV_CMD_NAV_TAKEOFF
    except Exception:
        return False

def guided_takeoff(master, alt_m=30.0, settle_s=2.0):
    print(f"Guided takeoff to {alt_m} m")
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0,
        0, 0, 0, 0,
        0, 0,
        alt_m
    )
    reached = False
    t0 = time.time()
    while time.time() - t0 < 30:
        msg = master.recv_match(type=['VFR_HUD', 'STATUSTEXT'], blocking=True, timeout=1)
        if not msg:
            continue
        if msg.get_type() == 'VFR_HUD':
            alt = getattr(msg, 'alt', 0.0)
            print(f"Altitude: {alt:.1f} m")
            if alt >= (alt_m - 2.0):
                if not reached:
                    reached = True
                    t_reach = time.time()
                elif time.time() - t_reach >= settle_s:
                    print("Takeoff altitude reached")
                    return
        elif msg.get_type() == 'STATUSTEXT':
            print(msg)
    print("Proceeding without confirmed altitude (timeout)")

def start_auto_mission(master):
    set_mode(master, 'AUTO')
    master.mav.mission_start_send(master.target_system, master.target_component)
    print("Mission start requested")

def monitor_progress(master):
    print("Monitoring mission progress (Ctrl-C to exit)")
    while True:
        msg = master.recv_match(type=['MISSION_CURRENT', 'MISSION_ITEM_REACHED', 'STATUSTEXT'], blocking=True, timeout=2)
        if msg:
            print(msg)

def main():
    print(f"Connecting to {SITL_CONNECTION}...")
    master = mavutil.mavlink_connection(SITL_CONNECTION)
    wait_heartbeat(master)
    wait_home_and_position(master, timeout=45)

    loader = upload_mission(master, WPL_FILE)

    if mission_starts_with_takeoff(loader):
        print("Mission starts with TAKEOFF; AUTO can start on ground")
        set_mode(master, 'GUIDED')
        arm_and_wait(master, timeout=30)
        start_auto_mission(master)
    else:
        print("Mission lacks TAKEOFF; performing guided takeoff, then AUTO")
        set_mode(master, 'GUIDED')
        arm_and_wait(master, timeout=30)
        guided_takeoff(master, alt_m=GUIDED_TAKEOFF_ALT_M)
        start_auto_mission(master)

    monitor_progress(master)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

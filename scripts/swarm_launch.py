#!/usr/bin/env python3
"""
swarm_launch.py — Autonomous swarm startup.

Workflow (controlled by flags below):
  1. [optional] Upload the .plan mission to Drone 1 via MAVLink
  2. Connect to follower drones 2, 3, 4
  3. Set GUIDED mode, arm, and take off each follower
  4. [optional] Set Drone 1 to AUTO mode and arm it to start the mission
  5. Launch swarm_follow.py

Run AFTER:  bash scripts/launch_sitl.sh  (and wait ~30s for SITL to init)
"""
import json
import os
import sys
import time
import subprocess
from pymavlink import mavutil

# ── Configuration ──────────────────────────────────────────────────────────────

PLAN_FILE   = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '..', 'missions', 'Aerophile.plan')

LEADER_URI  = "udp:127.0.0.1:14551"
GUIDED_MODE = 4      # ArduCopter GUIDED mode number
AUTO_MODE   = 3      # ArduCopter AUTO mode number
TAKEOFF_ALT = 3      # metres above home (relative) for followers

FOLLOWERS = [
    ("udp:127.0.0.1:14561", 2),
    ("udp:127.0.0.1:14571", 3),
    ("udp:127.0.0.1:14581", 4),
]

# ── Feature flags : Currently Mission Upload has a BUG that needs to be debugged till then use it with these flags set as Flase───────────────────────────────────────────────────────────────

UPLOAD_MISSION  = False   # Upload .plan to Drone 1 via MAVLink
AUTO_START_LEADER = False  # Arm Drone 1 in AUTO mode to start the mission


# ── Mission Upload ──────────────────────────────────────────────────────────────

def load_plan(path):
    with open(path) as f:
        plan = json.load(f)
    mission = plan['mission']
    return mission['plannedHomePosition'], mission['items']


def build_mission_items(home, plan_items):
    items = []
    items.append({
        'seq': 0, 'frame': 0, 'command': 16,
        'current': 0, 'autocontinue': 1,
        'p1': 0.0, 'p2': 0.0, 'p3': 0.0, 'p4': 0.0,
        'x': int(home[0] * 1e7),
        'y': int(home[1] * 1e7),
        'z': float(home[2]),
    })
    for seq, item in enumerate(plan_items, start=1):
        params = item.get('params', [0] * 7)
        lat = float(params[4]) if len(params) > 4 and params[4] else 0.0
        lon = float(params[5]) if len(params) > 5 and params[5] else 0.0
        alt = float(params[6]) if len(params) > 6 and params[6] else 0.0
        items.append({
            'seq': seq,
            'frame': item.get('frame', 3),
            'command': item['command'],
            'current': 1 if seq == 1 else 0,
            'autocontinue': 1 if item.get('autoContinue', True) else 0,
            'p1': float(params[0]) if len(params) > 0 else 0.0,
            'p2': float(params[1]) if len(params) > 1 else 0.0,
            'p3': float(params[2]) if len(params) > 2 else 0.0,
            'p4': float(params[3]) if len(params) > 3 else 0.0,
            'x': int(lat * 1e7),
            'y': int(lon * 1e7),
            'z': alt,
        })
    return items


def send_item(conn, item):
    conn.mav.mission_item_int_send(
        conn.target_system, conn.target_component,
        item['seq'], item['frame'], item['command'],
        item['current'], item['autocontinue'],
        item['p1'], item['p2'], item['p3'], item['p4'],
        item['x'], item['y'], item['z'],
    )


def upload_mission(conn, plan_path):
    print(f"  [*] Loading {os.path.basename(plan_path)} ...")
    home, plan_items = load_plan(plan_path)
    items = build_mission_items(home, plan_items)
    n = len(items)
    print(f"  [*] Uploading {n} items (home + {len(plan_items)} mission items) ...")

    conn.mav.mission_clear_all_send(conn.target_system, conn.target_component)
    time.sleep(0.5)
    conn.mav.mission_count_send(conn.target_system, conn.target_component, n)

    sent = set()
    final_ack = None
    deadline = time.time() + max(30.0, n * 0.5)

    while time.time() < deadline:
        msg = conn.recv_match(
            type=['MISSION_REQUEST_INT', 'MISSION_REQUEST', 'MISSION_ACK'],
            blocking=True, timeout=3.0
        )
        if msg is None:
            continue
        if msg.get_type() == 'MISSION_ACK':
            final_ack = msg
            break
        seq = msg.seq
        if 0 <= seq < n:
            send_item(conn, items[seq])
            sent.add(seq)
        if len(sent) == n:
            final_ack = conn.recv_match(type='MISSION_ACK', blocking=True, timeout=10.0)
            break

    if final_ack and final_ack.type == 0:
        print(f"  [+] MISSION_ACK: accepted")
    else:
        ack_type = final_ack.type if final_ack else 'timeout'
        print(f"  [!] MISSION_ACK type={ack_type} — upload failed")
        return False

    # Best-effort count check (MAVProxy may race to consume the MISSION_COUNT reply)
    conn.mav.mission_request_list_send(conn.target_system, conn.target_component)
    mc = conn.recv_match(type='MISSION_COUNT', blocking=True, timeout=5.0)
    if mc and mc.count == n:
        print(f"  [+] Verified: vehicle reports {mc.count} items")
    elif mc:
        print(f"  [!] Count mismatch: expected {n}, got {mc.count} (ACK OK — proceeding)")
    else:
        print(f"  [!] Count check timed out (MAVProxy likely consumed it — ACK was OK)")
    return True


# ── Connection & Follower Helpers ───────────────────────────────────────────────

def connect(uri, name):
    print(f"  [*] Connecting to {name} ({uri}) ...")
    conn = mavutil.mavlink_connection(uri)
    conn.wait_heartbeat(timeout=30)
    print(f"  [+] {name} connected  (sysid={conn.target_system})")
    return conn


def set_guided(conn, name):
    conn.mav.command_long_send(
        conn.target_system, conn.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        GUIDED_MODE, 0, 0, 0, 0, 0
    )
    deadline = time.time() + 10
    while time.time() < deadline:
        msg = conn.recv_match(type='HEARTBEAT', blocking=True, timeout=2)
        if msg and msg.custom_mode == GUIDED_MODE:
            print(f"  [+] {name} → GUIDED")
            return
    print(f"  [!] {name}: GUIDED confirmation timed out, proceeding anyway")


def arm(conn, name):
    conn.mav.command_long_send(
        conn.target_system, conn.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
        1, 0, 0, 0, 0, 0, 0
    )
    deadline = time.time() + 15
    while time.time() < deadline:
        msg = conn.recv_match(type='HEARTBEAT', blocking=True, timeout=2)
        if msg and (msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED):
            print(f"  [+] {name} → ARMED")
            return
    print(f"  [!] {name}: arm timed out — trying force-arm ...")
    conn.mav.command_long_send(
        conn.target_system, conn.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
        1, 21196, 0, 0, 0, 0, 0
    )
    time.sleep(2)


def send_takeoff(conn, name, alt):
    conn.mav.command_long_send(
        conn.target_system, conn.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0,
        0, 0, 0, 0, 0, 0, float(alt)
    )
    print(f"  [+] {name} → TAKEOFF to {alt}m")


def wait_altitude(conn, name, target_alt, tolerance=2.0):
    print(f"  [*] {name}: climbing to {target_alt}m ...")
    deadline = time.time() + 90
    while time.time() < deadline:
        msg = conn.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=2)
        if msg:
            alt_rel = msg.relative_alt / 1000.0
            if alt_rel >= target_alt - tolerance:
                print(f"  [+] {name} reached {alt_rel:.1f}m")
                return True
    print(f"  [!] {name}: altitude timeout")
    return False


def start_leader_mission(conn, name):
    conn.mav.command_long_send(
        conn.target_system, conn.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        AUTO_MODE, 0, 0, 0, 0, 0
    )
    deadline = time.time() + 10
    while time.time() < deadline:
        msg = conn.recv_match(type='HEARTBEAT', blocking=True, timeout=2)
        if msg and msg.custom_mode == AUTO_MODE:
            print(f"  [+] {name} → AUTO mode")
            break
    else:
        print(f"  [!] {name}: AUTO mode confirmation timed out, proceeding")
    time.sleep(0.5)
    conn.mav.command_long_send(
        conn.target_system, conn.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
        1, 0, 0, 0, 0, 0, 0
    )
    deadline = time.time() + 15
    while time.time() < deadline:
        msg = conn.recv_match(type='HEARTBEAT', blocking=True, timeout=2)
        if msg and (msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED):
            print(f"  [+] {name} → ARMED — mission started")
            return
    print(f"  [!] {name}: arm timed out — trying force-arm")
    conn.mav.command_long_send(
        conn.target_system, conn.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
        1, 21196, 0, 0, 0, 0, 0
    )
    time.sleep(2)


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    print("=== Swarm Launch ===\n")

    leader = None

    # ── [optional] Upload mission to Drone 1 ──────────────────────────────────
    if UPLOAD_MISSION:
        plan_path = sys.argv[1] if len(sys.argv) > 1 else PLAN_FILE
        if not os.path.exists(plan_path):
            print(f"[!] Plan file not found: {plan_path}")
            print(f"     Run: python3 scripts/kml_to_wpl.py  to generate it first")
            sys.exit(1)
        print("[*] Uploading mission to Drone 1 ...")
        try:
            leader = connect(LEADER_URI, "Drone 1 (Leader)")
        except Exception as e:
            print(f"  [!] Cannot connect to Drone 1: {e}")
            sys.exit(1)
        if not upload_mission(leader, plan_path):
            print("  [!] Mission upload failed — aborting")
            sys.exit(1)
    else:
        print("[~] Mission upload skipped — upload manually via QGC before continuing")

    # ── Connect to followers ───────────────────────────────────────────────────
    print("\n[1/3] Connecting to followers ...")
    follower_conns = []
    for uri, sid in FOLLOWERS:
        try:
            c = connect(uri, f"Drone {sid}")
            follower_conns.append((c, f"Drone {sid}"))
        except Exception as e:
            print(f"  [!] Cannot connect to Drone {sid}: {e}")
            print("       Is SITL running?  Try: bash scripts/launch_sitl.sh")
            sys.exit(1)

    # ── GUIDED → Arm → Takeoff followers ──────────────────────────────────────
    print(f"\n[2/3] Arming followers and taking off to {TAKEOFF_ALT}m ...")
    for conn, name in follower_conns:
        set_guided(conn, name)
    time.sleep(1)

    for conn, name in follower_conns:
        arm(conn, name)
    time.sleep(2)

    for conn, name in follower_conns:
        send_takeoff(conn, name, TAKEOFF_ALT)

    for conn, name in follower_conns:
        wait_altitude(conn, name, TAKEOFF_ALT)

    # ── [optional] Start leader mission ───────────────────────────────────────
    if AUTO_START_LEADER:
        if leader is None:
            try:
                leader = connect(LEADER_URI, "Drone 1 (Leader)")
            except Exception as e:
                print(f"  [!] Cannot connect to Drone 1 for auto-start: {e}")
        if leader:
            print("\n[*] Starting Drone 1 mission (AUTO mode + arm) ...")
            start_leader_mission(leader, "Drone 1 (Leader)")
    else:
        print("\n[~] Leader auto-start skipped — arm and start mission manually in QGC")

    # ── Start follow loop ──────────────────────────────────────────────────────
    print("\n[3/3] All followers airborne. Launching swarm_follow.py  (Ctrl+C to stop)\n")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    subprocess.run([sys.executable, os.path.join(script_dir, 'swarm_follow.py')])


if __name__ == '__main__':
    main()

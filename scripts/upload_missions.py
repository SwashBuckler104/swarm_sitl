#!/usr/bin/env python3
"""
Usage: python3 upload_mission.py --port 14550 --file missions/drone1.wpl
Uploads a QGC WPL file to the connected vehicle via pymavlink mission protocol.
"""

import argparse
from pymavlink import mavutil

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', required=True, help='UDP port to connect (e.g. 14550)')
    parser.add_argument('--file', required=True, help='WPL file to upload')
    args = parser.parse_args()

    # Parse WPL mission file
    missions = []
    with open(args.file) as f:
        header = f.readline()  # skip header line
        for line in f:
            if not line.strip():
                continue
            parts = line.strip().split('\t')
            seq = int(parts[0])
            current = int(parts[1])
            frame = int(parts[2])
            command = int(parts[3])
            p1 = float(parts[4])
            p2 = float(parts[5])
            p3 = float(parts[6])
            p4 = float(parts[7])
            x = float(parts[8])
            y = float(parts[9])
            z = float(parts[10])
            auto = int(parts[11]) if len(parts) > 11 else 1

            missions.append({
                'seq': seq, 'frame': frame, 'command': command,
                'p1': p1, 'p2': p2, 'p3': p3, 'p4': p4,
                'x': x, 'y': y, 'z': z, 'auto': auto
            })

    print(f'Connecting to udp:127.0.0.1:{args.port}')
    mav = mavutil.mavlink_connection(f'udp:127.0.0.1:{args.port}')

    print('Waiting for heartbeat...')
    mav.wait_heartbeat()
    print(f'Heartbeat from system {mav.target_system}, component {mav.target_component}')

    # Send mission count
    count = len(missions)
    print(f'Sending MISSION_COUNT = {count}')
    mav.mav.mission_count_send(mav.target_system, mav.target_component, count)

    # Serve requests from autopilot to upload mission items
    while True:
        msg = mav.recv_match(type=['MISSION_REQUEST', 'MISSION_ACK'], blocking=True, timeout=10)
        if not msg:
            print('Timeout waiting for mission request/ack')
            break

        msg_type = msg.get_type()
        if msg_type == 'MISSION_REQUEST':
            seq = msg.seq
            print(f'MISSION_REQUEST for seq {seq}')
            wp = missions[seq]
            # mav.mav.mission_item_send(
            #     mav.target_system, mav.target_component,
            #     seq,
            #     wp['frame'], wp['command'], 0, wp['auto'],
            #     wp['p1'], wp['p2'], wp['p3'], wp['p4'],
            #     wp['x'], wp['y'], wp['z']
            # )
            mav.mav.mission_item_int_send(mav.target_system, mav.target_component,
                seq,
                wp['frame'], wp['command'], 0, wp['auto'],
                wp['p1'], wp['p2'], wp['p3'], wp['p4'],
                int(wp['x'] * 1e7),  # latitude in degrees * 1e7 (int32)
                int(wp['y'] * 1e7),  # longitude in degrees * 1e7 (int32)
                wp['z']
                )
            
            print(f'Sent mission item {seq}')
        elif msg_type == 'MISSION_ACK':
            print('MISSION_ACK received, mission upload complete')
            break

    print('Done')

if __name__ == '__main__':
    main()

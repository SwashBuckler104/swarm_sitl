# swarm_sitl
4 swarm drone simulation following .XML

# SetUp 

# Start Cmds_Demo

<!-- In ardupilot folder -->
./Tools/autotest/sim_vehicle.py -v ArduCopter -f quad --out=udp:127.0.0.1:14550 --console

<!-- In swarm_sitl folder -->
python3 scripts/upload_missions.py --port 14550 --file missions/drone1.wpl


# Error decoding Tips

Error : Got MISSION_ACK: TYPE_MISSION: INVALID_SEQUENCE
The issue is likely this mav.mav.mission_count_send(...) running before the autopilot asks for the mission:
This causes a mismatch in mission protocol sequence (you send mission count before the autopilot has even started the request cycle), and it ends in an INVALID_SEQUENCE error.
Fix :
// Wait for MISSION_REQUEST_LIST from the vehicle
print("Waiting for MISSION_REQUEST_LIST...")
msg = mav.recv_match(type='MISSION_REQUEST_LIST', blocking=True, timeout=10)
if not msg:
    print("Timeout waiting for MISSION_REQUEST_LIST")
    return

// Send mission count after receiving MISSION_REQUEST_LIST
count = len(missions)
print(f"MISSION_REQUEST_LIST received, sending MISSION_COUNT = {count}")
mav.mav.mission_count_send(mav.target_system, mav.target_component, count)

// Also, set the target component explicitly, in case the autopilot expects 1:
mav.target_component = 1

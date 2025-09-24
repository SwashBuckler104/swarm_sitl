# swarm_sitl
4 swarm drone simulation following .XML

# SetUp 

# Start Cmds_Demo

<!-- In ardupilot folder -->
./Tools/autotest/sim_vehicle.py -v ArduCopter -f quad --out=udp:127.0.0.1:14550 --console

<!-- In swarm_sitl folder -->
python3 scripts/upload_missions.py --port 14550 --file missions/drone1.wpl

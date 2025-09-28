# swarm_sitl
4 swarm drone simulation following .XML

# SetUp 

# Start Cmds_Demo

<!-- In ardupilot folder -->
./Tools/autotest/sim_vehicle.py -v ArduCopter -f quad --out=udp:127.0.0.1:14550 --console

./Tools/autotest/sim_vehicle.py -v Copter --console --map --count 4 --auto-sysid --location CMAC --auto-offset-line 90,10

<!-- In swarm_sitl folder -->
python3 scripts/upload_missions.py --port 14550 --file missions/drone1.wpl

# Kill Instances 
pkill -f sim_vehicle.py
pkill -f mavproxy.py
pkill -f arducopter

# Steps :
~/.config/ardupilot/locations.txt
MySpot=12.934,77.61,30,0
MySpot1=12.935,77.61,30,0
MySpot2=12.936,77.61,30,0
MySpot3=12.937,77.61,30,0

# Drone 1
./Tools/autotest/sim_vehicle.py -v ArduCopter -f quad --instance 0 --sysid 1 -L MySpot   --out=udp:127.0.0.1:14550 --no-rebuild --no-mavproxy &

# Drone 2
./Tools/autotest/sim_vehicle.py -v ArduCopter -f quad --instance 1 --sysid 2 -L MySpot1  --out=udp:127.0.0.1:14551 --no-rebuild --no-mavproxy &

# Drone 3
./Tools/autotest/sim_vehicle.py -v ArduCopter -f quad --instance 2 --sysid 3 -L MySpot2  --out=udp:127.0.0.1:14552 --no-rebuild --no-mavproxy &

# Drone 4
./Tools/autotest/sim_vehicle.py -v ArduCopter -f quad --instance 3 --sysid 4 -L MySpot3  --out=udp:127.0.0.1:14553 --no-rebuild --no-mavproxy &

mavproxy.py \
  --master=udp:127.0.0.1:14550 \
  --master=udp:127.0.0.1:14551 \
  --master=udp:127.0.0.1:14552 \
  --master=udp:127.0.0.1:14553 \
  --out=udp:127.0.0.1:14554 \
  --map

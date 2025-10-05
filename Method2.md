## Using a swarm drone launch git repo::

ap-swarm-launcher is a solid SITL orchestration base, and layering a mission-upload pipeline on top is feasible with a clean separation of concerns: launcher handles process/ports/offsets; uploader handles MAVLink readiness, mission transfer, and mode/arming control.

### To launch 1 sitl instance -- Success
```bash
uv run ap-sitl-swarm -n 1 \
  --param RC7_OPTION=0 \
  /home/swashbuckler/ardupilot/build/sitl/bin/arducopter
```

### To launch 4 sitl instances -- Success
```bash
uv run ap-sitl-swarm -n 4 \
     --param RC7_OPTION=0 \
    /home/swashbuckler/ardupilot/build/sitl/bin/arducopter
```

```bash
./Tools/autotest/sim_vehicle.py -v ArduCopter --sysid 1 --out=udp:127.0.0.1:14550 --console



# cmd that send info on two ports, can directly be run on user terminal,, Hell yeah fkiing worksssss(Note keep the ports 10 units apart)

# Instance 1
sim_vehicle.py -v ArduCopter --sysid 1 -I 0 --out udp:127.0.0.1:14550 --out udp:127.0.0.1:14551

# Instance 2
sim_vehicle.py -v ArduCopter --sysid 2 -I 1 --out udp:127.0.0.1:14560 --out udp:127.0.0.1:14561

# Instance 3
sim_vehicle.py -v ArduCopter --sysid 3 -I 2 --out udp:127.0.0.1:14570 --out udp:127.0.0.1:14571

# Instance 4
sim_vehicle.py -v ArduCopter --sysid 4 -I 3 --out udp:127.0.0.1:14580 --out udp:127.0.0.1:14581

# Worksssssss!!!!!! swarm_follower.py
```
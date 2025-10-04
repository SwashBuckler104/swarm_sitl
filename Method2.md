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





```
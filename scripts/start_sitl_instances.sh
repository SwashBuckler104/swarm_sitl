#!/usr/bin/env bash
set -e

# Paths
ARDUPILOT_ROOT=~/ardupilot
cd "$ARDUPILOT_ROOT"

# Ports and SYSIDs
PORTS=(14550 14551 14552 14553)
SYSIDS=(1 2 3 4)
HOMES=("MySpot" "MySpot1" "MySpot2" "MySpot3")

for i in ${!PORTS[@]}; do
    port=${PORTS[$i]}
    sysid=${SYSIDS[$i]}
    home=${HOMES[$i]}
    echo "[INFO] Starting SITL instance $i (SYSID=$sysid) -> udp:$port"
    
    ./Tools/autotest/sim_vehicle.py -v ArduCopter -f quad \
        --instance $i --sysid $sysid \
        -L $home \
        --sim_vehicle_sh_compatible \
        --out=udp:127.0.0.1:$port \
        --no-rebuild &
    sleep 1
done

echo "[INFO] All SITL instances launched"

#!/usr/bin/env bash
set -e

# Adjust these paths to your environment
ARDUPILOT_ROOT=~/ardupilot

# Ports and SYSIDs for each drone
PORTS=(14550 14551 14552 14553)
SYSIDS=(1 2 3 4)

# Home locations: lat,lon,alt_m,heading
HOMES=("12.934000,77.610000,0,0" "12.935000,77.610000,0,0" "12.936000,77.610000,0,0" "12.937000,77.610000,0,0")

cd "$ARDUPILOT_ROOT"

for i in ${!PORTS[@]}; do
    port=${PORTS[$i]}
    sysid=${SYSIDS[$i]}
    home=${HOMES[$i]}
    echo "Starting SITL instance $i (SYSID=$sysid) -> udp:$port"
    ./Tools/autotest/sim_vehicle.py -v ArduCopter -f quad --instance $i --sysid $sysid \
    --home=$home --out=udp:127.0.0.1:$port --no-rebuild --console --map &
    sleep 1
done

echo "All SITL instances started."

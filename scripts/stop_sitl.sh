#!/bin/bash
# Stops all SITL instances started by launch_sitl.sh (both modes).

echo "[*] Stopping SITL instances..."

# Quit droneN screen sessions (headless mode)
screen -ls 2>/dev/null | awk '/\.drone[0-9]+/ {print $1}' | while read -r s; do
    echo "    closing screen session $s"
    screen -S "$s" -X quit 2>/dev/null
done

# Kill remaining processes (covers xterm mode too).
# -x / full-path patterns so we never match unrelated processes that
# merely mention these names on their command line.
pkill -x "arducopter" 2>/dev/null
pkill -f "Tools/autotest/sim_vehicle.py" 2>/dev/null
pkill -f "bin/mavproxy.py" 2>/dev/null

sleep 1
echo "[+] Done."

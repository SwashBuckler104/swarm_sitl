#!/bin/bash
# Opens 4 separate xterm windows, one per SITL instance — same as running manually.

export PATH="$HOME/ardupilot/Tools/autotest:$PATH"

if [ -z "$DISPLAY" ]; then
    echo "[!] No DISPLAY found. Run this from a desktop session."
    exit 1
fi

# --- Kill any leftover processes from a previous run ---
echo "[*] Cleaning up existing SITL processes..."
pkill -f "arducopter" 2>/dev/null
pkill -f "sim_vehicle.py" 2>/dev/null
sleep 2

# --- Pre-configure waf ONCE before launching instances ---
# Without this, all 4 sim_vehicle.py processes race to run waf configure
# simultaneously and corrupt each other's temp files (exit code 512 error).
echo "[*] Pre-configuring ArduPilot build..."
(cd ~/ardupilot && ./waf configure --board sitl) || {
    echo "[!] waf configure failed. Check your ArduPilot build setup."
    exit 1
}
echo "[+] Build configured."
echo ""

# --- Launch each instance with a small stagger ---
echo "[*] Launching SITL instances..."

xterm -T "SITL Drone 1 - Leader" -e bash -c \
    "cd ~ && sim_vehicle.py -v ArduCopter --sysid 1 -I 0 --out udp:127.0.0.1:14550 --out udp:127.0.0.1:14551; exec bash" &
sleep 5

xterm -T "SITL Drone 2 - Follower" -e bash -c \
    "cd ~ && sim_vehicle.py -v ArduCopter --sysid 2 -I 1 --out udp:127.0.0.1:14560 --out udp:127.0.0.1:14561; exec bash" &
sleep 5

xterm -T "SITL Drone 3 - Follower" -e bash -c \
    "cd ~ && sim_vehicle.py -v ArduCopter --sysid 3 -I 2 --out udp:127.0.0.1:14570 --out udp:127.0.0.1:14571; exec bash" &
sleep 5

xterm -T "SITL Drone 4 - Follower" -e bash -c \
    "cd ~ && sim_vehicle.py -v ArduCopter --sysid 4 -I 3 --out udp:127.0.0.1:14580 --out udp:127.0.0.1:14581; exec bash" &

echo "[+] All 4 SITL instances launched."
echo "    Wait ~30s for all to fully initialise."
echo "    Next: upload mission to Drone 1 in QGC, then run arm_followers.py"

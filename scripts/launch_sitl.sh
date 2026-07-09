#!/bin/bash
# Launches 4 SITL instances, one per drone.
#
# Two modes, picked automatically:
#   * Desktop (DISPLAY set + xterm installed) — one xterm window per
#     drone, exactly like running each instance manually.
#   * Docker / headless (no display)          — one detached `screen`
#     session per drone. Attach with `screen -r drone1` (detach: Ctrl-A, D),
#     logs in /tmp/droneN.log. Stop everything with scripts/stop_sitl.sh.
#
# Port map (same in both modes):
#   Drone 1 (Leader)    → 14550 (QGC) / 14551 (scripts)
#   Drone 2 (Follower)  → 14560 (QGC) / 14561 (scripts)
#   Drone 3 (Follower)  → 14570 (QGC) / 14571 (scripts)
#   Drone 4 (Follower)  → 14580 (QGC) / 14581 (scripts)
#
# In headless mode every drone additionally streams to the host machine
# (udp:$GCS_ADDR:14550, default host.docker.internal) so QGroundControl
# outside the container shows all 4 vehicles on its default UDP link.

export PATH="$HOME/ardupilot/Tools/autotest:$PATH"

NUM_DRONES=4
GCS="${GCS_ADDR:-host.docker.internal}"

# --- Pick launch mode ---
if [ -n "$DISPLAY" ] && command -v xterm >/dev/null 2>&1; then
    MODE=xterm
else
    MODE=screen
    if ! command -v screen >/dev/null 2>&1; then
        echo "[!] Neither a display (for xterm) nor 'screen' is available."
        echo "    Install screen, or run from a desktop session."
        exit 1
    fi
fi
echo "[*] Launch mode: $MODE"

# --- Kill any leftover processes from a previous run ---
echo "[*] Cleaning up existing SITL processes..."
pkill -x "arducopter" 2>/dev/null
pkill -f "Tools/autotest/sim_vehicle.py" 2>/dev/null
sleep 2

# --- Build setup ---
# With a prebuilt SITL binary (e.g. the ardupilot-docker image) we pass
# --no-rebuild, which also removes the need to pre-run waf configure.
# Otherwise pre-configure waf ONCE before launching instances: without
# this, all 4 sim_vehicle.py processes race to run waf configure
# simultaneously and corrupt each other's temp files (exit code 512).
if [ -x "$HOME/ardupilot/build/sitl/bin/arducopter" ]; then
    echo "[+] Prebuilt SITL binary found — skipping build."
    BUILD_ARGS="--no-rebuild"
else
    echo "[*] Pre-configuring ArduPilot build..."
    (cd ~/ardupilot && ./waf configure --board sitl) || {
        echo "[!] waf configure failed. Check your ArduPilot build setup."
        exit 1
    }
    echo "[+] Build configured."
    BUILD_ARGS=""
fi
echo ""

# --- Launch each instance with a small stagger ---
echo "[*] Launching SITL instances..."

for i in $(seq 1 "$NUM_DRONES"); do
    idx=$((i - 1))
    qgc_port=$((14540 + i * 10))
    script_port=$((14541 + i * 10))
    role="Follower"; [ "$i" -eq 1 ] && role="Leader"

    cmd="cd ~ && sim_vehicle.py -v ArduCopter --sysid $i -I $idx $BUILD_ARGS \
--out udp:127.0.0.1:$qgc_port --out udp:127.0.0.1:$script_port"

    if [ "$MODE" = "xterm" ]; then
        xterm -T "SITL Drone $i - $role" -e bash -c "$cmd; exec bash" &
    else
        # Headless: also stream to the GCS on the host machine
        cmd="$cmd --out udp:$GCS:14550"
        screen -S "drone$i" -X quit >/dev/null 2>&1
        screen -dmS "drone$i" bash -c "$cmd 2>&1 | tee /tmp/drone$i.log"
        echo "    Drone $i ($role): screen -r drone$i   log: /tmp/drone$i.log"
    fi

    [ "$i" -lt "$NUM_DRONES" ] && sleep 5
done

echo "[+] All $NUM_DRONES SITL instances launched."
echo "    Wait ~30s for all to fully initialise."
echo "    Next: python3 scripts/swarm_launch.py"
[ "$MODE" = "screen" ] && echo "    Stop everything: bash scripts/stop_sitl.sh"

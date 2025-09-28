#!/usr/bin/env bash
set -e

# Forward telemetry from 4 SITLs to single UDP for QGC
mavproxy.py \
    --master=udp:127.0.0.1:14550 \
    --master=udp:127.0.0.1:14551 \
    --master=udp:127.0.0.1:14552 \
    --master=udp:127.0.0.1:14553 \
    --out=udp:127.0.0.1:14554 &

echo "[INFO] MAVProxy forwarding 4 SITL ports to 14554"
echo "[INFO] Connect QGC to udp://127.0.0.1:14554 to visualize all drones"

#!/usr/bin/env bash
set -e

# Kill old processes first
pkill -9 sim_vehicle.py || true
pkill -9 mavproxy.py || true

echo "[INFO] Starting SITL instances..."
./scripts/start_sitl_instances.sh

sleep 3

echo "[INFO] Starting MAVProxy for QGC visualization..."
./scripts/start_mavproxy.sh

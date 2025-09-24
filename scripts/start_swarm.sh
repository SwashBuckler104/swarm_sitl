#!/usr/bin/env bash
set -e

# start SITL instances then MAVProxy
scripts/start_sitl_instances.sh
sleep 3
scripts/start_mavproxy.sh

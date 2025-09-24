#!/usr/bin/env bash
set -e

# Connect MAVProxy to each SITL instance and forward aggregated telemetry to port 14554
mavproxy.py \
  --master=udp:127.0.0.1:14550 \
  --master=udp:127.0.0.1:14551 \
  --master=udp:127.0.0.1:14552 \
  --master=udp:127.0.0.1:14553 \
  --out=udp:127.0.0.1:14554 \
  --map --console

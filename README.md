# Swarm SITL Simulation

A multi-drone swarm simulation using ArduPilot SITL and PyMAVLink. One leader drone follows a predefined KML mission path; three follower drones autonomously mirror its movements via MAVLink.

Integrates with QGroundControl (QGC) for mission planning and visualization.

---

## Features

- Multi-drone SITL setup (1 Leader + 3 Followers)
- KML-to-Waypoint (.txt) mission conversion
- QGroundControl integration for mission planning and upload
- PyMAVLink-based swarm coordination
- Automated mission upload, follower arming, takeoff, and swarm launch
- Fully local simulation — no real drones required

---

## Dependencies

- Python 3.8+
- ArduPilot SITL
- QGroundControl (QGC)
- PyMAVLink
- lxml

---

## Python Environment Setup

Run these commands once from the project root before using any scripts:

```bash
# Create a virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install all Python dependencies
pip install -r requirements.txt
```

> Activate the venv (`source .venv/bin/activate`) in every new terminal before running the scripts.

To deactivate when done:
```bash
deactivate
```

---

## Installing ArduPilot

```bash
sudo apt update
sudo apt install -y git python3 python3-pip

# Clone ArduPilot
git clone --recurse-submodules https://github.com/ArduPilot/ardupilot.git
cd ardupilot

# Install dependencies
Tools/environment_install/install-prereqs-ubuntu.sh -y

# Reload environment (run in every new terminal)
. ~/.profile
```

**Pin to a stable release (recommended):**
```bash
git fetch --all --tags
git checkout Copter-4.6.3
git submodule update --init --recursive
# Should show: HEAD detached at Copter-4.6.3
```

**Build and verify SITL:**
```bash
# From ardupilot/ root
./waf configure --board sitl
./waf copter

# Quick test (single instance)
./Tools/autotest/sim_vehicle.py -v ArduCopter -f quad --console
```

---

## Project Structure

```
swarm_sitl/
├── kml/                    # Place your QGC-exported .kml files here
├── missions/               # Generated waypoint files (.txt) go here
└── scripts/
    ├── kml_to_wpl.py       # Converts QGC KML to a QGC .plan file
    ├── launch_sitl.sh      # Launches all 4 SITL instances (via xterm)
    ├── swarm_launch.py     # Uploads mission, arms/takes off followers, starts swarm
    └── swarm_follow.py     # MAVLink follower relay loop
```

---

## Execution

### Step 1 — Convert KML to Waypoints

Export your mission from QGC Plan view as a `.kml` file, place it in `kml/`, then run:

```bash
cd swarm_sitl/scripts
python3 kml_to_wpl.py
```

The script auto-detects the `.kml` file in `kml/` and writes a `.plan` file to `missions/`.
You can also pass paths explicitly:

```bash
python3 kml_to_wpl.py ../kml/MyMission.kml ../missions/MyMission.plan [altitude_override_m]
```

---

### Step 2 — Launch 4 SITL Instances

```bash
bash scripts/launch_sitl.sh
```

This opens 4 separate `xterm` windows (one per drone), equivalent to running each instance manually in its own terminal. Each window runs independently so the instances don't conflict.

```
Drone 1 (Leader)    → ports 14550 / 14551
Drone 2 (Follower)  → ports 14560 / 14561
Drone 3 (Follower)  → ports 14570 / 14571
Drone 4 (Follower)  → ports 14580 / 14581
```

> Requires an active desktop session (`DISPLAY` must be set).

Wait ~30 seconds for all instances to initialise before continuing.
**Hard FallBAck**
```bash
# Run each instance in a separate terminal (from the home directory).
# Instance 1
sim_vehicle.py -v ArduCopter --sysid 1 -I 0 --out udp:127.0.0.1:14550 --out udp:127.0.0.1:14551

# Instance 2
sim_vehicle.py -v ArduCopter --sysid 2 -I 1 --out udp:127.0.0.1:14560 --out udp:127.0.0.1:14561

# Instance 3
sim_vehicle.py -v ArduCopter --sysid 3 -I 2 --out udp:127.0.0.1:14570 --out udp:127.0.0.1:14571

# Instance 4
sim_vehicle.py -v ArduCopter --sysid 4 -I 3 --out udp:127.0.0.1:14580 --out udp:127.0.0.1:14581
```

---

### Step 3 — Launch Swarm

```bash
python3 scripts/swarm_launch.py
```

This script handles everything automatically:
1. **Uploads** `missions/Aerophile.plan` to Drone 1 via MAVLink
2. **Connects** to follower Drones 2, 3, 4
3. Sets each follower to **GUIDED** mode, **arms** it, and sends a **TAKEOFF** command
4. Waits for all three to reach altitude
5. Launches `swarm_follow.py` (the follower relay loop)

To use a different plan file:
```bash
python3 scripts/swarm_launch.py missions/MyOtherMission.plan
```

---

### Step 3 is fully autonomous — no further action needed.

`swarm_launch.py` arms and takes off the followers first, then sets Drone 1 to **AUTO** mode and arms it so the mission starts automatically. QGC can be used to monitor progress.

---

## Port Reference

| Drone | SYSID | QGC / MAVProxy port | Script port |
|-------|-------|----------------------|-------------|
| 1 (Leader)   | 1 | 14550 | 14551 |
| 2 (Follower) | 2 | 14560 | 14561 |
| 3 (Follower) | 3 | 14570 | 14571 |
| 4 (Follower) | 4 | 14580 | 14581 |

---

## Future Improvements

- Automate mission upload to Drone 1 via MAVLink (skip QGC for upload)
- Add configurable formation offsets via CLI arguments
- Change default SITL home location
- Integrate with ROS 2 for advanced swarm autonomy

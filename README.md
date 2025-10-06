# Swarm SITL Simulation

This project demonstrates a swarm drone simulation using ArduPilot SITL and PyMAVLink, where one leader drone follows a predefined mission path (.KML), and three follower drones autonomously mirror the leader’s movements.  
The setup integrates with QGroundControl (QGC) for visualization, mission upload, and manual control.  

The system enables rapid prototyping and testing of swarm coordination, path following, and MAVLink-based communication — all in a simulated environment.

---

## 🚀 Features

- Multi-drone SITL setup (1 Leader + 3 Followers)
- KML-to-Waypoint (.WPL) mission conversion
- QGroundControl integration for mission planning
- PyMAVLink-based swarm coordination
- Fully local simulation — no real drones required

---

## ⚙️ Dependencies

- **Python 3.8+**
- **ArduPilot SITL**
- **QGroundControl (QGC)**
- **PyMAVLink** 

---

## 📝 Execution Steps
**Step 1: Launch 4 ArduPilot SITL Instances**
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

**Step 2: Convert KML to WPL**
```bash
#💡 Place your .kml file inside swarm_sitl/kml/ before running the script.
# The generated .txt waypoint file will be stored in swarm_sitl/missions/.
cd swarm_sitl/scripts
python3 kml_to_wpl.py
```

**Step 3: Upload Mission to Leader Drone**
- Open QGroundControl
- Go to the Plan view and upload the generated .txt waypoint file to Vehicle 1 (Leader)
- Take off Vehicles 2, 3, and 4 — this ensures they are in GUIDED mode and ready to follow

**Step 4: Run the Swarm Script**
```bash
# Run the following command in the swarm_sitl/scripts directory.
python3 swarm_follow.py
# Then, in QGC, take off and start the mission for Vehicle 1.
# The follower drones will automatically track and follow the leader.
```

## 🎯 Outcome
Add Photos and Videos here.......

## Future Improvements
- Build a bash script that automates the entire Execution Process
- Add feature to change default sethome location of QGC
- Integrate with ROS 2 for advanced swarm autonomy.

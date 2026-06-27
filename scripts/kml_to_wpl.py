#!/usr/bin/env python3
"""
Converts a QGC-exported KML file to a QGroundControl .plan file.

QGC does NOT export TAKEOFF (cmd=22) or RTL (cmd=20) as Point placemarks —
they have no unique geographic position so they're omitted from the KML.
This script injects both automatically around the waypoints.

Usage (auto-detect KML in kml/ folder):
    python3 kml_to_wpl.py

Usage (explicit paths):
    python3 kml_to_wpl.py <input.kml> <output.plan> [altitude_override_m]
"""
import json
import os
import sys
from lxml import etree


def extract_qgc_items(path):
    """Extract mission Points from the QGC KML 'Items' folder."""
    ns = {'k': 'http://www.opengis.net/kml/2.2'}
    tree = etree.parse(path)
    items = []

    for folder in tree.xpath('//k:Folder', namespaces=ns):
        name_el = folder.find('k:name', ns)
        if name_el is None or (name_el.text or '').strip() != 'Items':
            continue
        for pm in folder.xpath('k:Placemark', namespaces=ns):
            coord_el = pm.find('.//k:Point/k:coordinates', ns)
            if coord_el is None:
                continue
            parts = coord_el.text.strip().split(',')
            lon = float(parts[0])
            lat = float(parts[1])
            amsl = float(parts[2]) if len(parts) > 2 else None
            name_el2 = pm.find('k:name', ns)
            idx = -1
            if name_el2 is not None:
                try:
                    idx = int(name_el2.text.strip())
                except (ValueError, AttributeError):
                    pass
            items.append((idx, lat, lon, amsl))

    if not items:
        return None
    items.sort(key=lambda x: x[0])
    return items


def extract_coords_fallback(path):
    """Fallback: extract from LineString only (no Items folder found)."""
    ns = {'k': 'http://www.opengis.net/kml/2.2'}
    tree = etree.parse(path)
    coords = []
    for elem in tree.xpath('//k:LineString/k:coordinates', namespaces=ns):
        for token in elem.text.strip().split():
            parts = token.split(',')
            if len(parts) >= 2:
                coords.append((float(parts[1]), float(parts[0]), None))
    return coords


def find_default_kml():
    kml_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'kml')
    for f in sorted(os.listdir(kml_dir)):
        if f.lower().endswith('.kml'):
            return os.path.join(kml_dir, f)
    return None


def default_output_path(infile):
    base = os.path.splitext(os.path.basename(infile))[0]
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'missions', base + '.plan')


def build_plan(home_lat, home_lon, home_amsl, waypoints, takeoff_alt):
    """Build a QGC .plan JSON structure matching QGC's native format."""
    items = []
    jump_id = 1

    # Takeoff
    items.append({
        "AMSLAltAboveTerrain": None,
        "Altitude": takeoff_alt,
        "AltitudeMode": 1,
        "autoContinue": True,
        "command": 22,
        "doJumpId": jump_id,
        "frame": 3,
        "params": [0, 0, 0, 0, home_lat, home_lon, takeoff_alt],
        "type": "SimpleItem"
    })
    jump_id += 1

    # Waypoints
    for lat, lon, rel_alt in waypoints:
        items.append({
            "AMSLAltAboveTerrain": None,
            "Altitude": rel_alt,
            "AltitudeMode": 1,
            "autoContinue": True,
            "command": 16,
            "doJumpId": jump_id,
            "frame": 3,
            "params": [0, 0, 0, 0, lat, lon, rel_alt],
            "type": "SimpleItem"
        })
        jump_id += 1

    # RTL
    items.append({
        "autoContinue": True,
        "command": 20,
        "doJumpId": jump_id,
        "frame": 0,
        "params": [0, 0, 0, 0, 0, 0, 0],
        "type": "SimpleItem"
    })

    return {
        "fileType": "Plan",
        "geoFence": {"circles": [], "polygons": [], "version": 2},
        "groundStation": "QGroundControl",
        "mission": {
            "cruiseSpeed": 15,
            "firmwareType": 3,
            "globalPlanAltitudeMode": 1,
            "hoverSpeed": 5,
            "items": items,
            "plannedHomePosition": [home_lat, home_lon, home_amsl],
            "vehicleType": 2,
            "version": 2
        },
        "rallyPoints": {"points": [], "version": 2},
        "version": 1
    }


def main():
    if len(sys.argv) < 3:
        infile = find_default_kml()
        if not infile:
            print("Usage: kml_to_wpl.py <input.kml> <output.plan> [altitude_override_m]")
            print("Or place a .kml file in kml/ and run without args.")
            sys.exit(1)
        outfile = default_output_path(infile)
        alt_override = None
        print(f"Auto-detected: {os.path.basename(infile)} -> {os.path.relpath(outfile)}")
    else:
        infile = sys.argv[1]
        outfile = sys.argv[2]
        alt_override = float(sys.argv[3]) if len(sys.argv) > 3 else None

    items = extract_qgc_items(infile)

    if items:
        home_item = next((it for it in items if it[0] == 0), items[0])
        _, home_lat, home_lon, home_amsl = home_item

        # Deduplicate mission waypoints; skip home (idx=0) and any duplicate lat/lon
        seen = {(round(home_lat, 7), round(home_lon, 7))}
        unique_wps = []
        for idx, lat, lon, amsl in items:
            if idx == 0:
                continue
            key = (round(lat, 7), round(lon, 7))
            if key not in seen:
                seen.add(key)
                if alt_override is not None:
                    rel_alt = alt_override
                elif amsl is not None and home_amsl is not None:
                    rel_alt = round(amsl - home_amsl, 2)
                else:
                    rel_alt = 30.0
                unique_wps.append((lat, lon, rel_alt))

        takeoff_alt = unique_wps[0][2] if unique_wps else 30.0

        plan = build_plan(home_lat, home_lon, home_amsl, unique_wps, takeoff_alt)
        with open(outfile, 'w') as f:
            json.dump(plan, f, indent=4)

        print(f"Wrote {outfile}")
        print(f"  [T]   Takeoff: {takeoff_alt}m relative")
        for i, (lat, lon, rel_alt) in enumerate(unique_wps, start=1):
            print(f"  [WP{i}]  {lat}, {lon}  @ {rel_alt}m rel")
        print(f"  [RTL] Return to Launch")

    else:
        # Fallback for non-QGC KML
        coords = extract_coords_fallback(infile)
        if not coords:
            print('No coordinates found in KML')
            sys.exit(1)
        alt = alt_override if alt_override is not None else 30.0
        home_lat, home_lon, _ = coords[0]
        waypoints = [(lat, lon, alt) for lat, lon, _ in coords[1:]]
        plan = build_plan(home_lat, home_lon, 0.0, waypoints, alt)
        with open(outfile, 'w') as f:
            json.dump(plan, f, indent=4)
        print(f"Wrote {outfile} (fallback mode, {len(waypoints)} waypoints at {alt}m rel)")


if __name__ == '__main__':
    main()

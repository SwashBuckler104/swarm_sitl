#!/usr/bin/env python3

import sys
from lxml import etree

def extract_coords_from_kml(path):
    ns = {'k': 'http://www.opengis.net/kml/2.2'}
    tree = etree.parse(path)
    coords = []

    # LineString
    for elem in tree.xpath('//k:LineString/k:coordinates', namespaces=ns):
        raw = elem.text.strip()
        for token in raw.split():
            parts = token.split(',')
            if len(parts) >= 2:
                lon = float(parts[0])
                lat = float(parts[1])
                coords.append((lat, lon))

    # Points
    for elem in tree.xpath('//k:Point/k:coordinates', namespaces=ns):
        parts = elem.text.strip().split(',')
        lon = float(parts[0])
        lat = float(parts[1])
        coords.append((lat, lon))

    # Polygons (outerBoundaryIs -> LinearRing)
    for elem in tree.xpath('//k:Polygon/k:outerBoundaryIs/k:LinearRing/k:coordinates', namespaces=ns):
        raw = elem.text.strip()
        ring = []
        for token in raw.split():
            parts = token.split(',')
            if len(parts) >= 2:
                lon = float(parts[0])
                lat = float(parts[1])
                ring.append((lat, lon))
        # add ring points (skip duplicate last if same as first)
        if ring:
            if ring[0] == ring[-1]:
                ring = ring[:-1]
            coords.extend(ring)

    return coords

def main():
    if len(sys.argv) < 3:
        print("Usage: kml_to_wpl.py <input.kml> <output.wpl> [altitude]")
        sys.exit(1)

    infile = sys.argv[1]
    outfile = sys.argv[2]
    alt_override = float(sys.argv[3]) if len(sys.argv) > 3 else None

    coords = extract_coords_from_kml(infile)
    if not coords:
        print('No coordinates parsed from KML')
        sys.exit(1)

    alt = alt_override if alt_override is not None else 30.0

    with open(outfile, 'w') as f:
        f.write('QGC WPL 110\n')
        for i, (lat, lon) in enumerate(coords):
            current = 1 if i == 0 else 0
            frame = 0
            command = 16  # MAV_CMD_NAV_WAYPOINT
            p1 = 0
            p2 = 0
            p3 = 0
            p4 = 0
            x = lat
            y = lon
            z = alt
            auto = 1
            line = f"{i}\t{current}\t{frame}\t{command}\t{p1}\t{p2}\t{p3}\t{p4}\t{x}\t{y}\t{z}\t{auto}\n"
            f.write(line)

    print(f"Wrote {len(coords)} waypoints to {outfile}")

if __name__ == '__main__':
    main()

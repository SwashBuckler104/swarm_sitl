#!/usr/bin/env python3
import os
import subprocess

KML_DIR = 'kml'
OUT_DIR = 'missions'
ALT = 30  

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    kml_files = sorted(f for f in os.listdir(KML_DIR) if f.lower().endswith('.kml'))
    if not kml_files:
        print(f"[ERROR] No KML files found in {KML_DIR}/")
        return

    for i, fname in enumerate(kml_files):
        inpath = os.path.join(KML_DIR, fname)
        outpath = os.path.join(OUT_DIR, f"drone{i+1}.wpl")
        print(f"[INFO] Converting {inpath} → {outpath}")

        # Call your KML → WPL script
        try:
            subprocess.check_call([
                'python3', 'scripts/kml_to_wpl.py',
                inpath, outpath, str(ALT)
            ])
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Conversion failed for {fname}: {e}")
            continue

    print(f"[DONE] Missions generated in {OUT_DIR}/")

if __name__ == "__main__":
    main()

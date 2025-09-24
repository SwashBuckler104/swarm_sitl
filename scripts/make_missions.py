#!/usr/bin/env python3

import os
import subprocess

KML_DIR = 'kml'
OUT_DIR = 'missions'
ALT = 30

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    for i, fname in enumerate(sorted(os.listdir(KML_DIR))):
        if not fname.lower().endswith('.kml'):
            continue

        inpath = os.path.join(KML_DIR, fname)
        outpath = os.path.join(OUT_DIR, f'drone{i+1}.wpl')
        print(f'Converting {inpath} -> {outpath}')
        subprocess.check_call(['python3', 'scripts/kml_to_wpl.py', inpath, outpath, str(ALT)])

    print('Done')

if __name__ == '__main__':
    main()

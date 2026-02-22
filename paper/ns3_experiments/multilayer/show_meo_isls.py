#!/usr/bin/env python3
"""
Show only MEO–MEO ISL links (both endpoints are MEO satellites).
Uses the multi-layer constellation isls.txt and description.txt.
Prints all MEO sat A, MEO sat B pairs.

Usage:
    python3 show_meo_isls.py
"""

import os
import sys

def read_description(description_file_path):
    d = {}
    with open(description_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if '=' in line:
                key, value = line.split('=', 1)
                key, value = key.strip(), value.strip()
                try:
                    d[key] = int(value) if '.' not in value else float(value)
                except ValueError:
                    d[key] = value
    return d

def read_isls(isls_file_path):
    isls = []
    with open(isls_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                isls.append((int(parts[0]), int(parts[1])))
    return isls

def main():
    base_dir = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        '../../satellite_networks_state/gen_data/kuiper_630_meo_isls_plus_grid_with_cross_layer_ground_stations_top_100_algorithm_free_one_multi_layer'
    ))
    description_file = os.path.join(base_dir, 'description.txt')
    isls_file = os.path.join(base_dir, 'isls.txt')

    if not os.path.exists(description_file):
        print(f"ERROR: Not found: {description_file}")
        return 1
    if not os.path.exists(isls_file):
        print(f"ERROR: Not found: {isls_file}")
        return 1

    description = read_description(description_file)
    leo_num_sats = int(description.get('leo_num_sats', 1156))
    all_isls = read_isls(isls_file)
    max_sat = max(max(a, b) for a, b in all_isls)
    total_sats = max_sat + 1
    meo_num_sats = total_sats - leo_num_sats

    meo_isls = [(a, b) for a, b in all_isls if a >= leo_num_sats and b >= leo_num_sats]
    meo_isls.sort(key=lambda x: (x[0], x[1]))

    print("=" * 60)
    print("MEO–MEO ISL links only")
    print("=" * 60)
    print(f"LEO satellites: 0 .. {leo_num_sats - 1}  ({leo_num_sats} sats)")
    print(f"MEO satellites: {leo_num_sats} .. {total_sats - 1}  ({meo_num_sats} sats)")
    print(f"Total MEO–MEO ISLs: {len(meo_isls)}")
    print()

    if not meo_isls:
        print("No MEO–MEO ISLs in this constellation.")
        print("=" * 60)
        return 0

    print("MEO sat A   MEO sat B")
    print("-" * 25)
    for a, b in meo_isls:
        print(f"{a:<10} {b}")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Show all ground station (GS) and LEO satellite GSL links.
For a given time step, lists every GS and each satellite in range (GSL link).
By default shows only LEO; use --meo to include MEO. By default shows a summary
(one line per GS with count); use --full for the full link table.

Usage:
    python3 show_gs_leo_path.py [time_s] [--meo] [--full]
    time_s optional: 0, 1, 2, 3, 4, 5 - default: 0
    --meo: include MEO satellites (default: LEO only)
    --full: print every GSL link with distance (default: summary per GS)

Example:
    python3 show_gs_leo_path.py           # t=0s, LEO only, summary
    python3 show_gs_leo_path.py 2 --full  # t=2s, full table
    python3 show_gs_leo_path.py 0 --meo   # t=0s, LEO+MEO summary
"""

import os
import sys
from collections import defaultdict

# Add satgenpy to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../satgenpy')))
from satgen.tles import read_tles
from satgen.ground_stations import read_ground_stations_extended
from satgen.description import read_description
from satgen.distance_tools import distance_m_ground_station_to_satellite
from astropy import units as u


def compute_gsl_links(ground_stations, satellites, epoch, time_since_epoch_ns, max_gsl_length_m, leo_num_sats, include_meo):
    """
    Compute (gid, sat_id, distance_m) for every GS and satellite in range.
    If include_meo is False, only satellites with sat_id < leo_num_sats (LEO) are included.
    """
    time = epoch + time_since_epoch_ns * u.ns
    links = []
    for gid, ground_station in enumerate(ground_stations):
        for sid in range(len(satellites)):
            if not include_meo and sid >= leo_num_sats:
                continue
            distance_m = distance_m_ground_station_to_satellite(
                ground_station,
                satellites[sid],
                str(epoch),
                str(time),
            )
            if distance_m <= max_gsl_length_m:
                links.append((gid, sid, distance_m))
    return links


def main():
    base_dir = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        '../../satellite_networks_state/gen_data/kuiper_630_meo_isls_plus_grid_with_cross_layer_ground_stations_top_100_algorithm_free_one_multi_layer'
    ))
    constellation_dir = base_dir

    if not os.path.exists(constellation_dir):
        print(f"ERROR: Constellation directory not found: {constellation_dir}")
        return 1

    description = read_description(os.path.join(constellation_dir, 'description.txt'))
    max_gsl_length_m = description.get('max_gsl_length_m')
    if max_gsl_length_m is None:
        print("ERROR: description.txt missing max_gsl_length_m")
        return 1
    leo_num_sats = int(description.get('leo_num_sats', 1122))
    total_sats = len(read_tles(os.path.join(constellation_dir, 'tles.txt'))["satellites"])

    ground_stations = read_ground_stations_extended(os.path.join(constellation_dir, 'ground_stations.txt'))
    tles = read_tles(os.path.join(constellation_dir, 'tles.txt'))
    satellites = tles["satellites"]
    epoch = tles["epoch"]

    args = [a for a in sys.argv[1:] if a not in ('--meo', '--full')]
    include_meo = '--meo' in sys.argv
    full_table = '--full' in sys.argv
    time_s = 0.0
    if args:
        try:
            time_s = float(args[0])
        except ValueError:
            pass
    time_since_epoch_ns = int(time_s * 1e9)

    links = compute_gsl_links(
        ground_stations, satellites, epoch, time_since_epoch_ns,
        max_gsl_length_m, leo_num_sats, include_meo
    )

    layer = "LEO + MEO" if include_meo else "LEO only"
    print("=" * 80)
    print(f"All GS – {layer} GSL links at t = {time_s:.1f}s")
    print("=" * 80)
    print(f"Max GSL length: {max_gsl_length_m:,.0f} m ({max_gsl_length_m/1e6:.2f} Mm)")
    print(f"Total links: {len(links)}")
    print()

    if full_table:
        print(f"{'GS gid':<6} {'GS name':<35} {'Sat ID':<8} {'Layer':<6} {'Distance (m)':<18} {'Distance (km)'}")
        print("-" * 90)
        for gid, sat_id, distance_m in sorted(links, key=lambda x: (x[0], x[1])):
            name = ground_stations[gid]["name"]
            if len(name) > 33:
                name = name[:30] + "..."
            layer_str = "MEO" if sat_id >= leo_num_sats else "LEO"
            print(f"{gid:<6} {name:<35} {sat_id:<8} {layer_str:<6} {distance_m:<18,.0f} {distance_m/1000:,.2f}")
    else:
        # Summary: one line per GS with count and sample of sat IDs
        print(f"{'GS gid':<6} {'GS name':<38} {'# links':<8} {'Sample LEO/MEO sat IDs'}")
        print("-" * 80)
        by_gs = defaultdict(list)
        for gid, sat_id, distance_m in links:
            by_gs[gid].append((sat_id, distance_m))
        for gid in range(len(ground_stations)):
            name = ground_stations[gid]["name"]
            if len(name) > 36:
                name = name[:33] + "..."
            sat_list = by_gs.get(gid, [])
            sat_list.sort(key=lambda x: x[1])  # by distance
            count = len(sat_list)
            sample = [s[0] for s in sat_list[:5]]
            sample_str = ", ".join(map(str, sample)) if sample else "-"
            if count > 5:
                sample_str += f" ... (+{count - 5} more)"
            print(f"{gid:<6} {name:<38} {count:<8} {sample_str}")

    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())

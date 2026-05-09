#!/usr/bin/env python3
"""
Show all satellites coverage for every time step.
For each time step (0s, 1s, 2s, ...), lists every GS and each satellite in range (GSL link).
By default shows only LEO; use --meo to include MEO. By default shows a summary
(one line per GS with count); use --full for the full link table per time step.

Usage:
    python3 show_all_satellites_coverage_per_timestep.py [--meo] [--full] [--steps 1]
    By default prints only t=1.0s block (one table). Use --steps 0,1,2,3,4,5 for all steps.
    --meo: include MEO satellites (default: LEO only)
    --full: print every GSL link with distance (default: summary per GS)
    --steps: comma-separated time steps in seconds (default: 1)

Example:
    python3 show_all_satellites_coverage_per_timestep.py              # only t=1.0s block
    python3 show_all_satellites_coverage_per_timestep.py --steps 0,1,2,3,4,5  # all steps
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

    include_meo = '--meo' in sys.argv
    full_table = '--full' in sys.argv

    # Parse --steps (default: only 1.0s so output is a single block)
    time_steps = [1]
    for i, arg in enumerate(sys.argv):
        if arg == '--steps' and i + 1 < len(sys.argv):
            try:
                time_steps = [float(x.strip()) for x in sys.argv[i + 1].split(',')]
            except ValueError:
                pass
            break

    for time_s in time_steps:
        time_since_epoch_ns = int(time_s * 1e9)
        links = compute_gsl_links(
            ground_stations, satellites, epoch, time_since_epoch_ns,
            max_gsl_length_m, leo_num_sats, include_meo
        )

        print(f"t = {time_s:.1f}s   Total links: {len(links)}")
        print("-" * 80)
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
            # Summary: one line per GS with count and sample of sat IDs (0 links -> "-")
            by_gs = defaultdict(list)
            for gid, sat_id, distance_m in links:
                by_gs[gid].append((sat_id, distance_m))
            print(f"{'GS gid':<6} {'GS name':<38} {'# links':<8} {'Sample sat IDs'}")
            print("-" * 80)
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
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())

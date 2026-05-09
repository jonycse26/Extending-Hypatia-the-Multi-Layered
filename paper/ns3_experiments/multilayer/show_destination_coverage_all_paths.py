#!/usr/bin/env python3
"""
Show destination-side coverage for all paths (from run_list).
For each path (e.g. Mumbai → Lima), shows the destination GS and how many LEO sats
are in range at each time step. Use this to see why "No path" at 1s/3s (destination has 0).

Usage:
    python3 show_destination_coverage_all_paths.py [--meo] [--steps 0,1,2,3,4,5]
    By default prints one block per path: destination name, gid, and # links at each time step.
    --meo: include MEO satellites in count (default: LEO only)
    --steps: comma-separated time steps in seconds (default: 0,1,2,3,4,5)
"""

import os
import sys
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '../../../satgenpy')))
sys.path.insert(0, SCRIPT_DIR)

from satgen.tles import read_tles
from satgen.ground_stations import read_ground_stations_extended
from satgen.description import read_description
from satgen.distance_tools import distance_m_ground_station_to_satellite
from astropy import units as u


def compute_gsl_links(ground_stations, satellites, epoch, time_since_epoch_ns, max_gsl_length_m, leo_num_sats, include_meo):
    """Compute (gid, sat_id, distance_m) for every GS and satellite in range."""
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


def find_dest_gid(ground_stations, dest_name):
    """Find GS gid whose name contains or starts with dest_name (e.g. 'Lima')."""
    dest_lower = dest_name.strip().lower()
    for gid, gs in enumerate(ground_stations):
        name = gs.get("name", "")
        if dest_lower in name.lower() or name.lower().startswith(dest_lower):
            return gid
    return None


def main():
    import run_list

    base_dir = os.path.abspath(os.path.join(
        SCRIPT_DIR,
        '../../satellite_networks_state/gen_data/' + run_list.multilayer_satellite_network
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

    ground_stations = read_ground_stations_extended(os.path.join(constellation_dir, 'ground_stations.txt'))
    tles = read_tles(os.path.join(constellation_dir, 'tles.txt'))
    satellites = tles["satellites"]
    epoch = tles["epoch"]

    include_meo = '--meo' in sys.argv
    time_steps = [0, 1, 2, 3, 4, 5]
    for i, arg in enumerate(sys.argv):
        if arg == '--steps' and i + 1 < len(sys.argv):
            try:
                time_steps = [float(x.strip()) for x in sys.argv[i + 1].split(',')]
            except ValueError:
                pass
            break

    # Paths from run_list (from_sat_id, to_sat_id, description e.g. "Mumbai to Lima")
    pairs = run_list.experiment1_pairs_multilayer

    # For each path, resolve destination GS gid from description
    path_info = []
    for from_id, to_id, desc in pairs:
        if " to " in desc:
            dest_name = desc.split(" to ")[-1].strip()
        else:
            dest_name = desc
        dest_gid = find_dest_gid(ground_stations, dest_name)
        if dest_gid is None:
            dest_gid = -1
            dest_label = dest_name + " (gid not found)"
        else:
            dest_label = ground_stations[dest_gid]["name"]
            if len(dest_label) > 36:
                dest_label = dest_label[:33] + "..."
        path_info.append((from_id, to_id, desc, dest_gid, dest_label))

    # Compute coverage per (time_s, gid) for destination GSs only
    dest_gids = {p[3] for p in path_info if p[3] >= 0}
    coverage = {}  # (time_s, gid) -> (count, sample_list)
    for time_s in time_steps:
        time_ns = int(time_s * 1e9)
        links = compute_gsl_links(
            ground_stations, satellites, epoch, time_ns,
            max_gsl_length_m, leo_num_sats, include_meo
        )
        by_gs = defaultdict(list)
        for gid, sat_id, distance_m in links:
            by_gs[gid].append((sat_id, distance_m))
        for gid in dest_gids:
            sat_list = by_gs.get(gid, [])
            sat_list.sort(key=lambda x: x[1])
            count = len(sat_list)
            sample = [s[0] for s in sat_list[:5]]
            sample_str = ", ".join(map(str, sample)) if sample else "-"
            if count > 5:
                sample_str += " ... (+%d more)" % (count - 5)
            coverage[(time_s, gid)] = (count, sample_str)

    # Print one block per path: destination side coverage at each time step
    layer = "LEO + MEO" if include_meo else "LEO only"
    print("Destination-side coverage for all paths (%s)" % layer)
    print("(No path when destination # links = 0 at that time step)")
    print()

    for from_id, to_id, desc, dest_gid, dest_label in path_info:
        print("--------------------------------------------------------------------------------")
        print("Path: %s (%d -> %d)  |  Destination: %s (gid %s)" % (
            desc, from_id, to_id, dest_label, dest_gid if dest_gid >= 0 else "?"))
        print("--------------------------------------------------------------------------------")
        print("%-8s  %-8s  %s" % ("Time", "# links", "Sample sat IDs"))
        print("--------------------------------------------------------------------------------")
        if dest_gid < 0:
            print("  (destination GS not found)")
        else:
            for time_s in time_steps:
                count, sample_str = coverage.get((time_s, dest_gid), (0, "-"))
                print("  %-6.1fs   %-8s  %s" % (time_s, count, sample_str))
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())

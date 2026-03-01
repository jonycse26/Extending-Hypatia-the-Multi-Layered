#!/usr/bin/env python3
"""
Show hop counts for ground station pairs from run_list.py.
Hop count = number of satellites in the path (excluding GS).
GS is only connected to LEO; path is always ... → MEO → LEO → GS (never MEO → GS directly).
E.g. GS→LEO→GS = 1 hop; GS→LEO→MEO→LEO→GS = 3 hops (LEO, MEO, LEO).
"""

import os
import glob
import sys

# Add paths for run_list and satgenpy
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '../../../satgenpy')))
sys.path.insert(0, SCRIPT_DIR)
from satgen.tles import read_tles
from satgen.ground_stations import read_ground_stations_extended
from satgen.description import read_description

def get_hop_count_for_pair(from_id, to_id, fstate_file, leo_num_sats, total_sats):
    """Get hop count for a specific pair at a specific time.
    Hop count = number of satellites in the path (excluding GS).
    """
    # Read forwarding state
    fstate_dict = {}
    with open(fstate_file, 'r') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 3:
                try:
                    src = int(parts[0])
                    dst = int(parts[1])
                    next_hop = int(parts[2])
                    fstate_dict[(src, dst)] = next_hop
                except (ValueError, IndexError):
                    continue

    if (from_id, to_id) not in fstate_dict or fstate_dict[(from_id, to_id)] == -1:
        return None, None, None, False

    path_nodes = [from_id]
    current = fstate_dict[(from_id, to_id)]
    max_hops = 25
    hops = 0

    while current != to_id and current != -1 and hops < max_hops:
        path_nodes.append(current)
        if (current, to_id) in fstate_dict:
            next_hop = fstate_dict[(current, to_id)]
            if next_hop == to_id:
                path_nodes.append(to_id)
                break
            elif next_hop != -1:
                current = next_hop
                hops += 1
            else:
                break
        else:
            break

    if path_nodes[-1] != to_id:
        path_nodes.append(to_id)

    # Hop count = number of satellites in path (excluding GS)
    hop_count = len([n for n in path_nodes if isinstance(n, int) and n < total_sats])

    meo_nodes = [n for n in path_nodes if isinstance(n, int) and leo_num_sats <= n < total_sats]
    uses_meo = len(meo_nodes) > 0

    # Sanity: GS is only connected to LEO; path must be ...→MEO→LEO→GS (never MEO→GS)
    gs_id = total_sats  # first GS node id
    invalid_meo_to_gs = False
    for i in range(len(path_nodes) - 1):
        a, b = path_nodes[i], path_nodes[i + 1]
        if isinstance(a, int) and isinstance(b, int) and leo_num_sats <= a < total_sats and b >= gs_id:
            invalid_meo_to_gs = True
            break

    return hop_count, uses_meo, path_nodes, invalid_meo_to_gs

def show_hop_counts():
    """Show hop counts for all pairs from run_list.py."""
    import run_list

    base_dir = os.path.abspath(os.path.join(
        SCRIPT_DIR,
        '../../satellite_networks_state/gen_data/' + run_list.multilayer_satellite_network
    ))
    constellation_dir = base_dir
    dynamic_state_dir = os.path.join(base_dir, 'dynamic_state_1000ms_for_5s')

    if not os.path.exists(dynamic_state_dir):
        print(f"ERROR: Dynamic state directory not found: {dynamic_state_dir}")
        return 1

    tles = read_tles(os.path.join(constellation_dir, 'tles.txt'))
    satellites = tles["satellites"]
    total_sats = len(satellites)
    description = read_description(os.path.join(constellation_dir, 'description.txt'))
    leo_num_sats = int(description.get('leo_num_sats', total_sats))

    # Pairs from run_list.py experiment1_pairs_multilayer (from_id, to_id, description)
    pairs_raw = run_list.experiment1_pairs_multilayer
    ground_stations = read_ground_stations_extended(os.path.join(constellation_dir, 'ground_stations.txt'))
    gs_start_id = run_list.MULTILAYER_OFFSET

    def short_name(gs_id, desc):
        gid = gs_id - gs_start_id
        if 0 <= gid < len(ground_stations):
            return ground_stations[gid]["name"][:12]
        return desc.split(" to ")[0] if " to " in desc else desc[:12]

    pairs = [(f, t, short_name(f, d), short_name(t, d)) for (f, t, d) in pairs_raw]

    fstate_files = sorted(glob.glob(os.path.join(dynamic_state_dir, 'fstate_*.txt')))[:6]

    print("=" * 80)
    print("Hop Count Analysis (from run_list.experiment1_pairs_multilayer)")
    print("=" * 80)
    print("Hop count = number of satellites in path (GS→LEO→GS = 1; GS→LEO→MEO→LEO→GS = 3)")
    print()

    for from_id, to_id, from_name, to_name in pairs:
        print(f"{from_name} → {to_name} ({from_id} → {to_id})")
        print("-" * 80)
        print(f"{'Time':<8} {'Hops':<6} {'MEO':<8} {'Path'}")
        print("-" * 80)

        for fstate_file in fstate_files:
            hop_count, uses_meo, path_nodes, invalid_meo_to_gs = get_hop_count_for_pair(
                from_id, to_id, fstate_file, leo_num_sats, total_sats
            )
            time_str = os.path.basename(fstate_file).replace('fstate_', '').replace('.txt', '')
            time_s = int(time_str) / 1e9

            if hop_count is not None:
                meo_str = "Yes" if uses_meo else "No"
                path_str = " → ".join(map(str, path_nodes))
                print(f"{time_s:>6.1f}s  {hop_count:<6} {meo_str:<8} {path_str}")
                if invalid_meo_to_gs:
                    print("         ^ WARNING: path has MEO→GS (invalid). Regenerate dynamic state with current algorithm.")
            else:
                print(f"{time_s:>6.1f}s  {'N/A':<6} {'N/A':<8} No path")

        print()

    print("=" * 80)
    print("Note: Hop count = number of satellites (excluding GS). GS only connects to LEO; path is ...→MEO→LEO→GS.")
    print("=" * 80)

    return 0

if __name__ == "__main__":
    sys.exit(show_hop_counts())


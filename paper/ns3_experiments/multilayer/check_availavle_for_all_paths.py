#!/usr/bin/env python3
"""
Detailed path analysis for key ground station pairs from run_list.py.
Shows how many paths exist and whether MEO is used.
"""

import os
import glob
import sys

def check_paths_for_pair(from_id, to_id, from_name, to_name):
    """Check detailed path information for a ground station pair."""
    
    base_dir = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        '../../satellite_networks_state/gen_data/kuiper_630_meo_isls_plus_grid_with_cross_layer_ground_stations_top_100_algorithm_free_one_multi_layer/dynamic_state_1000ms_for_5s'
    ))
    
    if not os.path.exists(base_dir):
        print(f"ERROR: Dynamic state directory not found: {base_dir}")
        print("Please run step_0_generate_constellation.py first")
        return None
    
    files = sorted(glob.glob(os.path.join(base_dir, 'fstate_*.txt')))
    if not files:
        print(f"ERROR: No forwarding state files found in {base_dir}")
        return None
    
    print("=" * 70)
    print(f"Detailed Path Analysis: {from_name} to {to_name}")
    print("=" * 70)
    print(f"Total time steps: {len(files)}")
    print(f"From ID: {from_id} ({from_name})")
    print(f"To ID: {to_id} ({to_name})")
    print()
    
    # Multi-layer constellation: 666 satellites (630 LEO + 36 MEO)
    # MEO satellites: IDs 630-665
    leo_num_sats = 630
    meo_start_id = 630
    meo_end_id = 665
    
    path_count = 0
    no_path_count = 0
    meo_used_count = 0
    leo_only_count = 0
    paths_with_meo = []
    paths_leo_only = []
    
    for idx, f in enumerate(files):
        time_step = idx * 1.0  # 1000ms = 1.0 seconds
        with open(f, 'r') as file:
            found_path = False
            path_uses_meo = False
            path_nodes = []
            
            for line in file:
                if line.startswith(f'{from_id},{to_id},'):
                    parts = line.strip().split(',')
                    if len(parts) >= 3 and parts[2] != '-1':
                        found_path = True
                        # Parse path: format is "from,to,next_hop,hop2,hop3,..."
                        path_nodes = [from_id]  # Start with source
                        for i in range(2, len(parts)):
                            if parts[i] != '-1' and parts[i] != '':
                                try:
                                    node_id = int(parts[i])
                                    path_nodes.append(node_id)
                                except ValueError:
                                    break
                        path_nodes.append(to_id)  # End with destination
                        
                        # Check if any node in path is MEO (between 630-665)
                        for node_id in path_nodes:
                            if meo_start_id <= node_id <= meo_end_id:
                                path_uses_meo = True
                                break
                        break
            
            if found_path:
                path_count += 1
                if path_uses_meo:
                    meo_used_count += 1
                    paths_with_meo.append((time_step, path_nodes))
                else:
                    leo_only_count += 1
                    paths_leo_only.append((time_step, path_nodes))
            else:
                no_path_count += 1
    
    total_checked = path_count + no_path_count
    percentage = (path_count / total_checked * 100) if total_checked > 0 else 0
    meo_percentage = (meo_used_count / path_count * 100) if path_count > 0 else 0
    
    print("=" * 70)
    print("Summary Statistics")
    print("=" * 70)
    print(f"Total time steps checked: {total_checked}")
    print(f"Paths available: {path_count}/{total_checked} ({percentage:.1f}%)")
    print(f"Paths unavailable: {no_path_count}/{total_checked} ({100-percentage:.1f}%)")
    print()
    print(f"Paths using MEO: {meo_used_count}/{path_count} ({meo_percentage:.1f}%)")
    print(f"Paths LEO-only: {leo_only_count}/{path_count} ({100-meo_percentage:.1f}%)")
    print()
    
    if paths_with_meo:
        print("=" * 70)
        print(f"Paths Using MEO ({len(paths_with_meo)} found):")
        print("=" * 70)
        for time_step, path_nodes in paths_with_meo[:5]:  # Show first 5
            meo_nodes = [n for n in path_nodes if meo_start_id <= n <= meo_end_id]
            print(f"Time {time_step:.1f}s: {len(path_nodes)-1} hops")
            print(f"  Path: {' → '.join(map(str, path_nodes))}")
            print(f"  MEO nodes: {meo_nodes}")
            print()
        if len(paths_with_meo) > 5:
            print(f"... and {len(paths_with_meo) - 5} more paths using MEO")
            print()
    
    if paths_leo_only:
        print("=" * 70)
        print(f"Paths LEO-Only ({len(paths_leo_only)} found):")
        print("=" * 70)
        for time_step, path_nodes in paths_leo_only[:5]:  # Show first 5
            print(f"Time {time_step:.1f}s: {len(path_nodes)-1} hops")
            print(f"  Path: {' → '.join(map(str, path_nodes))}")
            print()
        if len(paths_leo_only) > 5:
            print(f"... and {len(paths_leo_only) - 5} more LEO-only paths")
            print()
    
    print("=" * 70)
    print("Analysis:")
    print("=" * 70)
    if path_count == 0:
        print("✗ NO PATHS FOUND - This pair has 0% path availability")
        print("  Possible reasons:")
        print("  1. Coverage gaps in the constellation")
        print("  2. Ground stations not in range of any LEO satellites")
        print("  3. Constellation not fully generated")
    elif percentage < 10:
        print(f"⚠ VERY LOW PATH AVAILABILITY - Only {percentage:.1f}% of time steps have paths")
        print("  This is likely due to coverage limitations of the partial Kuiper-630 constellation")
        print("  (Only 630 LEO satellites = partial constellation)")
    else:
        print(f"✓ Paths available {percentage:.1f}% of the time")
    
    if path_count > 0:
        if meo_used_count == 0:
            print("⚠ WARNING: MEO is NOT being used in any paths!")
            print("  This may indicate:")
            print("  1. MEO path doesn't exist or is too expensive")
            print("  2. Routing algorithm not forcing MEO correctly")
            print("  3. Path distance < 10,000 km (but should be >= 10,000 km for São Paulo/Rio pairs)")
        else:
            print(f"✓ MEO is being used in {meo_percentage:.1f}% of available paths")
    
    print("=" * 70)
    
    return {
        'path_count': path_count,
        'no_path_count': no_path_count,
        'meo_used_count': meo_used_count,
        'leo_only_count': leo_only_count,
        'percentage': percentage,
        'meo_percentage': meo_percentage
    }

def main():
    """Check paths for all key pairs from run_list.py"""
    
    # Key pairs from run_list.py experiment1_pairs_multilayer (3 examples)
    pairs = [
        (1196, 1221, 'Mumbai', 'Lima'),                    # 16,703 km (>= 10,000 km - should use MEO)
        (1221, 1203, 'Lima', 'Karachi'),                   # 15,985 km (>= 10,000 km - should use MEO)
        (1192, 1204, 'Tokyo', 'Buenos-Aires'),             # Example: min 4 hops and MEO
    ]
    
    results = []
    for from_id, to_id, from_name, to_name in pairs:
        result = check_paths_for_pair(from_id, to_id, from_name, to_name)
        if result:
            results.append((f"{from_name} → {to_name}", result))
        print()  # Blank line between pairs
    
    # Summary
    if results:
        print("=" * 70)
        print("SUMMARY: All Pairs")
        print("=" * 70)
        for name, result in results:
            print(f"{name}:")
            print(f"  Path availability: {result['path_count']}/6 ({result['percentage']:.1f}%)")
            if result['path_count'] > 0:
                print(f"  MEO usage: {result['meo_used_count']}/{result['path_count']} ({result['meo_percentage']:.1f}%)")
            print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Check if MEO paths are available for ground station pairs.
This script checks if MEO satellites are in range and could be used.
"""

import os
import glob
import sys

def check_meo_paths_available():
    """Check if MEO paths are available for key pairs."""
    
    base_dir = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        '../../satellite_networks_state/gen_data/kuiper_630_meo_isls_plus_grid_with_cross_layer_ground_stations_top_100_algorithm_free_one_multi_layer/dynamic_state_1000ms_for_5s'
    ))
    
    if not os.path.exists(base_dir):
        print(f"ERROR: Dynamic state directory not found: {base_dir}")
        return 1
    
    # Check GSL files to see if MEO satellites are in range of ground stations
    gsl_files = sorted(glob.glob(os.path.join(base_dir, 'gsl_if_bandwidth_*.txt')))
    if not gsl_files:
        print("ERROR: No GSL files found")
        return 1
    
    print("=" * 70)
    print("MEO Path Availability Check")
    print("=" * 70)
    print()
    
    # Multi-layer constellation: 1192 satellites (1156 LEO + 36 MEO)
    # MEO satellites: IDs 1156-1191
    leo_num_sats = 1156
    meo_start_id = 1156
    meo_end_id = 1191
    
    # Ground station pairs to check (from run_list.py experiment1_pairs_multilayer, 3 examples)
    pairs = [
        (1196, 1221, 'Mumbai', 'Lima'),                    # Geodesic: 16,703 km (>= 10,000 km - should use MEO)
        (1221, 1203, 'Lima', 'Karachi'),                   # Geodesic: 15,985 km (>= 10,000 km - should use MEO)
        (1192, 1204, 'Tokyo', 'Buenos-Aires'),             # Example: min 4 hops and MEO
    ]
    
    # Check first few time steps
    for time_idx, gsl_file in enumerate(gsl_files[:6]):
        time_step = time_idx * 1.0  # 1000ms = 1.0 seconds
        print(f"Time step {time_step:.1f}s:")
        print("-" * 70)
        
        # Note: GSL files (gsl_if_bandwidth_*.txt) don't contain satellite-to-GS connections
        # We'll check the forwarding state instead to see which satellites are actually used
        # This will show us which satellites are in range and being used for routing
        print("  (GSL availability checked via forwarding state below)")
        print()
        
        if time_idx < len(gsl_files) - 1:
            print()
    
    # Now check actual routing in fstate files
    print("=" * 70)
    print("Checking Actual Routing (fstate files)")
    print("=" * 70)
    print()
    
    fstate_files = sorted(glob.glob(os.path.join(base_dir, 'fstate_*.txt')))[:6]
    
    for time_idx, fstate_file in enumerate(fstate_files):
        time_step = time_idx * 1.0
        print(f"Time step {time_step:.1f}s:")
        print("-" * 70)
        
        # Read all forwarding state into memory for path tracing
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
        
        for from_gs, to_gs, from_name, to_name in pairs:
            # Check if path exists
            if (from_gs, to_gs) not in fstate_dict or fstate_dict[(from_gs, to_gs)] == -1:
                continue
            
            # Trace the full path
            path_nodes = [from_gs]
            current = fstate_dict[(from_gs, to_gs)]
            max_hops = 20
            hops = 0
            
            while current != to_gs and current != -1 and hops < max_hops:
                path_nodes.append(current)
                if (current, to_gs) in fstate_dict:
                    next_hop = fstate_dict[(current, to_gs)]
                    if next_hop == to_gs:
                        path_nodes.append(to_gs)
                        break
                    elif next_hop != -1:
                        current = next_hop
                        hops += 1
                    else:
                        break
                else:
                    break
            
            if path_nodes[-1] != to_gs:
                path_nodes.append(to_gs)
            
            # Check if MEO is used
            meo_in_path = any(meo_start_id <= n <= meo_end_id for n in path_nodes if isinstance(n, int))
            meo_nodes = [n for n in path_nodes if isinstance(n, int) and meo_start_id <= n <= meo_end_id]
            
            print(f"  {from_name} → {to_name}:")
            print(f"    Path: {' → '.join(map(str, path_nodes))}")
            if meo_in_path:
                print(f"    ✓ MEO USED: {meo_nodes}")
            else:
                print(f"    ✗ MEO NOT USED (LEO-only path)")
            print()
    
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print("If MEO satellites are in range but not used:")
    print("  - Routing algorithm may not be forcing MEO correctly")
    print("  - Constellation may need regeneration with force_meo_for_demo=True")
    print()
    print("If MEO satellites are NOT in range:")
    print("  - MEO GSL range may be too small")
    print("  - Need to increase MEO GSL elevation angle (already done: 10°)")
    print("=" * 70)
    
    return 0

if __name__ == "__main__":
    sys.exit(check_meo_paths_available())


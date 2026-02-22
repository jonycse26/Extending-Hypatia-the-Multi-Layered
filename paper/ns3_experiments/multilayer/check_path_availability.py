#!/usr/bin/env python3
"""
Check path availability for ground station pairs in the multi-layer constellation.
This script helps diagnose routing issues.
"""

import os
import glob
import sys

def check_path_availability():
    """Check if paths exist for key ground station pairs."""
    
    base_dir = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        '../../satellite_networks_state/gen_data/kuiper_630_meo_isls_plus_grid_with_cross_layer_ground_stations_top_100_algorithm_free_one_multi_layer/dynamic_state_500ms_for_25s'
    ))
    
    if not os.path.exists(base_dir):
        print(f"ERROR: Dynamic state directory not found: {base_dir}")
        print("Please run step_0_generate_constellation.py first")
        return 1
    
    files = sorted(glob.glob(os.path.join(base_dir, 'fstate_*.txt')))
    if not files:
        print(f"ERROR: No forwarding state files found in {base_dir}")
        return 1
    
    print("="*70)
    print("Path Availability Check for Multi-Layer Constellation")
    print("="*70)
    print(f"Total state files: {len(files)}")
    print()
    
    # Check key pairs (matching run_list.py experiment1_pairs_multilayer, 3 examples)
    pairs = [
        (1196, 1221, 'Mumbai to Lima'),                     # 16,703 km (>= 10,000 km - should use MEO)
        (1221, 1203, 'Lima to Karachi'),                    # 15,985 km (>= 10,000 km - should use MEO)
        (1192, 1204, 'Tokyo to Buenos-Aires'),              # Example: min 4 hops and MEO
    ]
    
    print("Checking path availability across time steps:")
    print()
    
    for from_id, to_id, name in pairs:
        path_count = 0
        no_path_count = 0
        
        # Check all files (all time steps)
        for f in files:
            with open(f, 'r') as file:
                found = False
                for line in file:
                    if line.startswith(f'{from_id},{to_id},'):
                        parts = line.strip().split(',')
                        if len(parts) >= 3 and parts[2] != '-1':
                            found = True
                            break
                if found:
                    path_count += 1
                else:
                    no_path_count += 1
        
        total_checked = path_count + no_path_count
        percentage = (path_count / total_checked * 100) if total_checked > 0 else 0
        
        status = "✓ OK" if percentage > 50 else "✗ PROBLEM" if percentage < 10 else "⚠ WARNING"
        
        print(f"{status} {name} ({from_id} → {to_id}):")
        print(f"  Paths available: {path_count}/{total_checked} ({percentage:.1f}%)")
        print()
    
    print("="*70)
    print("Recommendations:")
    print("="*70)
    print("If paths are available < 10% of the time:")
    print("  1. Regenerate constellation state: python step_0_generate_constellation.py")
    print("  2. This may indicate a bug in the routing algorithm")
    print()
    print("If paths are available > 50% of the time:")
    print("  - Simulations should work, but may fail at times when no path exists")
    print("  - Consider increasing simulation duration or checking specific time steps")
    
    return 0

if __name__ == "__main__":
    sys.exit(check_path_availability())


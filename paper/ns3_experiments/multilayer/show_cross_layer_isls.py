#!/usr/bin/env python3
"""
Display all cross-layer ISLs (LEO ↔ MEO links) in the multi-layer constellation.
"""

import os
import sys

def read_description(description_file_path):
    """Read description file and return as dictionary."""
    description = {}
    with open(description_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # Try to convert to int or float
                try:
                    if '.' in value:
                        description[key] = float(value)
                    else:
                        description[key] = int(value)
                except ValueError:
                    description[key] = value
    return description

def read_isls(isls_file_path):
    """Read ISL file and return list of tuples (sat_a, sat_b)."""
    isls = []
    with open(isls_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    sat_a = int(parts[0])
                    sat_b = int(parts[1])
                    isls.append((sat_a, sat_b))
    return isls

def main():
    """Display all cross-layer ISLs."""
    
    # Path to constellation data
    base_dir = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        '../../satellite_networks_state/gen_data/kuiper_630_meo_isls_plus_grid_with_cross_layer_ground_stations_top_100_algorithm_free_one_multi_layer'
    ))
    
    description_file = os.path.join(base_dir, 'description.txt')
    isls_file = os.path.join(base_dir, 'isls.txt')
    
    if not os.path.exists(description_file):
        print(f"ERROR: Description file not found: {description_file}")
        return 1
    
    if not os.path.exists(isls_file):
        print(f"ERROR: ISL file not found: {isls_file}")
        return 1
    
    # Read description to get leo_num_sats
    description = read_description(description_file)
    leo_num_sats = description.get('leo_num_sats', 1156)  # Default fallback
    
    # Count total satellites from ISL file
    all_isls = read_isls(isls_file)
    max_sat_id = 0
    for sat_a, sat_b in all_isls:
        max_sat_id = max(max_sat_id, sat_a, sat_b)
    total_sats = max_sat_id + 1
    meo_num_sats = total_sats - leo_num_sats
    
    print("=" * 70)
    print("Cross-Layer ISL Analysis")
    print("=" * 70)
    print(f"LEO satellites: 0 to {leo_num_sats - 1} ({leo_num_sats} total)")
    print(f"MEO satellites: {leo_num_sats} to {total_sats - 1} ({meo_num_sats} total)")
    print(f"Total satellites: {total_sats}")
    print()
    
    # Note: all_isls already read above
    print(f"Total ISLs: {len(all_isls)}")
    print()
    
    # Filter cross-layer ISLs (LEO ↔ MEO)
    cross_layer_isls = []
    leo_leo_isls = []
    meo_meo_isls = []
    
    for sat_a, sat_b in all_isls:
        a_is_leo = sat_a < leo_num_sats
        b_is_leo = sat_b < leo_num_sats
        
        if a_is_leo and not b_is_leo:
            # LEO → MEO
            cross_layer_isls.append((sat_a, sat_b, 'LEO', 'MEO'))
        elif not a_is_leo and b_is_leo:
            # MEO → LEO
            cross_layer_isls.append((sat_a, sat_b, 'MEO', 'LEO'))
        elif a_is_leo and b_is_leo:
            # LEO → LEO
            leo_leo_isls.append((sat_a, sat_b))
        else:
            # MEO → MEO
            meo_meo_isls.append((sat_a, sat_b))
    
    # Display results
    print("=" * 70)
    print("Cross-Layer ISLs (LEO ↔ MEO)")
    print("=" * 70)
    print(f"Total cross-layer ISLs: {len(cross_layer_isls)}")
    print()
    
    if len(cross_layer_isls) > 0:
        # Sort by LEO satellite ID
        cross_layer_isls.sort(key=lambda x: (x[0] if x[2] == 'LEO' else x[1], x[0], x[1]))
        
        # Show first 100
        print("Cross-layer ISLs (showing first 100):")
        print(f"{'LEO Sat':<10} {'MEO Sat':<10} {'Type':<15}")
        print("-" * 40)
        for i, (sat_a, sat_b, type_a, type_b) in enumerate(cross_layer_isls[:100]):
            if type_a == 'LEO':
                leo_sat = sat_a
                meo_sat = sat_b
            else:
                leo_sat = sat_b
                meo_sat = sat_a
            print(f"{leo_sat:<10} {meo_sat:<10} {type_a} ↔ {type_b}")
        
        if len(cross_layer_isls) > 100:
            print(f"... ({len(cross_layer_isls) - 100} more cross-layer ISLs)")
        
        print()
        print("Summary by LEO satellite:")
        leo_to_meo_count = {}
        for sat_a, sat_b, type_a, type_b in cross_layer_isls:
            if type_a == 'LEO':
                leo_sat = sat_a
            else:
                leo_sat = sat_b
            leo_to_meo_count[leo_sat] = leo_to_meo_count.get(leo_sat, 0) + 1
        
        print(f"LEO satellites with cross-layer ISLs: {len(leo_to_meo_count)}")
        print(f"Average cross-layer ISLs per LEO: {len(cross_layer_isls) / len(leo_to_meo_count):.2f}")
        
        print()
        print("Summary by MEO satellite:")
        meo_to_leo_count = {}
        for sat_a, sat_b, type_a, type_b in cross_layer_isls:
            if type_a == 'MEO':
                meo_sat = sat_a
            else:
                meo_sat = sat_b
            meo_to_leo_count[meo_sat] = meo_to_leo_count.get(meo_sat, 0) + 1
        
        print(f"MEO satellites with cross-layer ISLs: {len(meo_to_leo_count)}")
        print(f"Average cross-layer ISLs per MEO: {len(cross_layer_isls) / len(meo_to_leo_count):.2f}")
    else:
        print("⚠ WARNING: No cross-layer ISLs found!")
        print("This may indicate an issue with ISL generation.")
    
    print()
    print("=" * 70)
    print("Other ISLs")
    print("=" * 70)
    print(f"LEO-LEO ISLs: {len(leo_leo_isls)}")
    print(f"MEO-MEO ISLs: {len(meo_meo_isls)}")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())


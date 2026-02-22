#!/usr/bin/env python3
"""
Check path distances (distance_to_ground_station_m) for ground station pairs.
This shows the actual path distance via ISLs that the algorithm uses for MEO threshold decisions.

Usage:
    python3 check_path_distances.py [from_id] [to_id] [pair_name]
    
Example:
    python3 check_path_distances.py 1221 1203 "Lima to Karachi"
"""

import os
import glob
import sys
import json

# Add satgenpy to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../satgenpy')))
from satgen.distance_tools import distance_m_between_satellites, distance_m_ground_station_to_satellite
from satgen.tles import read_tles
from satgen.ground_stations import read_ground_stations_extended
from satgen.isls import read_isls
from astropy import units as u

def load_isl_distances(constellation_dir):
    """Load ISL distances from constellation files."""
    isl_file = os.path.join(constellation_dir, 'isls.txt')
    if not os.path.exists(isl_file):
        return None
    
    # ISL file format: satellite_a, satellite_b, distance_m
    isl_distances = {}
    with open(isl_file, 'r') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 3:
                try:
                    sat_a = int(parts[0])
                    sat_b = int(parts[1])
                    distance = float(parts[2])
                    isl_distances[(sat_a, sat_b)] = distance
                    isl_distances[(sat_b, sat_a)] = distance  # Bidirectional
                except ValueError:
                    continue
    return isl_distances

def load_gsl_distances(constellation_dir, time_since_epoch_ns):
    """Load GSL distances from dynamic state files."""
    # GSL distances are in the ground_station_satellites_in_range data
    # We need to check the constellation generation files
    gsl_file = os.path.join(
        constellation_dir,
        f'../dynamic_state_{time_since_epoch_ns}ms_for_5s/gsl_if_bandwidth_{time_since_epoch_ns}.txt'
    )
    
    # Actually, GSL distances are in the constellation topology files
    # Let's check the ground_stations.txt and satellites.txt to compute GSL distances
    return None  # Will compute from coordinates if needed

def calculate_path_distance_from_fstate(fstate_file, from_id, to_id, isl_distances, leo_num_sats=630):
    """
    Calculate path distance by tracing the forwarding state path.
    This gives us the distance_to_ground_station_m for each satellite.
    """
    path_distances = {}  # (sat_id, dst_gs_id) -> distance
    
    with open(fstate_file, 'r') as f:
        # First, find all satellite-to-ground-station entries
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 5:
                try:
                    src_id = int(parts[0])
                    dst_id = int(parts[1])
                    next_hop = int(parts[2])
                    
                    # If this is a satellite-to-ground-station entry
                    if src_id < leo_num_sats and dst_id >= leo_num_sats:
                        # Trace the path to calculate distance
                        path_nodes = [src_id]
                        current = src_id
                        total_distance = 0.0
                        
                        while current != dst_id and current != -1:
                            # Find next hop in forwarding state
                            f.seek(0)  # Reset to beginning
                            found_next = False
                            for line2 in f:
                                parts2 = line2.strip().split(',')
                                if len(parts2) >= 3:
                                    if int(parts2[0]) == current and int(parts2[1]) == dst_id:
                                        next_hop_id = int(parts2[2])
                                        if next_hop_id == dst_id:
                                            # Reached ground station
                                            # GSL distance (approximate: ~500-2000 km)
                                            total_distance += 1000000.0  # ~1000 km GSL
                                            found_next = True
                                            break
                                        elif next_hop_id != -1:
                                            # ISL hop
                                            if (current, next_hop_id) in isl_distances:
                                                total_distance += isl_distances[(current, next_hop_id)]
                                            else:
                                                # Estimate: ~2000 km average ISL
                                                total_distance += 2000000.0
                                            path_nodes.append(next_hop_id)
                                            current = next_hop_id
                                            found_next = True
                                            break
                            
                            if not found_next:
                                break
                        
                        path_distances[(src_id, dst_id)] = total_distance
                except (ValueError, IndexError):
                    continue
    
    return path_distances

def check_path_distances_for_pair(from_id, to_id, pair_name):
    """Check path distances for a specific ground station pair."""
    
    base_dir = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        '../../satellite_networks_state/gen_data/kuiper_630_meo_isls_plus_grid_with_cross_layer_ground_stations_top_100_algorithm_free_one_multi_layer'
    ))
    
    constellation_dir = base_dir
    dynamic_state_dir = os.path.join(base_dir, 'dynamic_state_1000ms_for_5s')
    
    if not os.path.exists(dynamic_state_dir):
        print(f"ERROR: Dynamic state directory not found: {dynamic_state_dir}")
        print("Please run step_0_generate_constellation.py first")
        return
    
    # Load constellation data
    tles = read_tles(os.path.join(constellation_dir, 'tles.txt'))
    satellites = tles["satellites"]
    epoch = tles["epoch"]
    ground_stations = read_ground_stations_extended(os.path.join(constellation_dir, 'ground_stations.txt'))
    list_isls = read_isls(os.path.join(constellation_dir, 'isls.txt'), len(satellites))
    
    # Multi-layer constellation: 1192 satellites (1156 LEO + 36 MEO)
    # Based on run_list.py: MULTILAYER_OFFSET = 1192
    leo_num_sats = 1156
    total_sats = 1192
    gs_start_id = total_sats
    
    # Convert GS IDs to indices
    from_gid = from_id - gs_start_id
    to_gid = to_id - gs_start_id
    
    if from_gid < 0 or from_gid >= len(ground_stations):
        print(f"ERROR: Invalid from_id {from_id} (GS index {from_gid})")
        return
    if to_gid < 0 or to_gid >= len(ground_stations):
        print(f"ERROR: Invalid to_id {to_id} (GS index {to_gid})")
        return
    
    print("=" * 70)
    print(f"Path Distance Analysis: {pair_name}")
    print("=" * 70)
    print(f"From GS ID: {from_id}")
    print(f"To GS ID: {to_id}")
    print(f"MEO Threshold: 10,000 km (10,000,000 m)")
    print()
    
    # Check first few time steps
    fstate_files = sorted(glob.glob(os.path.join(dynamic_state_dir, 'fstate_*.txt')))[:6]
    
    for fstate_file in fstate_files:
        time_str = os.path.basename(fstate_file).replace('fstate_', '').replace('.txt', '')
        time_ns = int(time_str)
        time_s = time_ns / 1e9
        
        print(f"Time: {time_s:.1f}s ({time_str})")
        print("-" * 70)
        
        # Find GS-to-GS path
        with open(fstate_file, 'r') as f:
            gs_to_gs_path = None
            for line in f:
                if line.startswith(f'{from_id},{to_id},'):
                    parts = line.strip().split(',')
                    if len(parts) >= 3 and parts[2] != '-1':
                        src_sat_id = int(parts[2])
                        gs_to_gs_path = src_sat_id
                        break
        
        if gs_to_gs_path is None:
            print("  No path found")
            print()
            continue
        
        print(f"  Source satellite: {src_sat_id}")
        
        # Find satellite-to-ground-station distance
        # Look for entries: (src_sat_id, to_id)
        with open(fstate_file, 'r') as f:
            sat_to_gs_distance = None
            path_trace = []
            for line in f:
                if line.startswith(f'{src_sat_id},{to_id},'):
                    parts = line.strip().split(',')
                    if len(parts) >= 3:
                        # Trace path to calculate distance
                        current = src_sat_id
                        total_dist = 0.0
                        path_trace = [current]
                        
                        # Reset file and trace path with actual distances
                        f.seek(0)
                        max_hops = 20  # Safety limit
                        hops = 0
                        time_ns = int(time_str)
                        time = epoch + time_ns * u.ns
                        
                        while current != to_id and hops < max_hops:
                            found = False
                            for line2 in f:
                                parts2 = line2.strip().split(',')
                                if len(parts2) >= 3:
                                    try:
                                        if int(parts2[0]) == current and int(parts2[1]) == to_id:
                                            next_hop = int(parts2[2])
                                            if next_hop == to_id:
                                                # Reached GS, calculate actual GSL distance
                                                dst_gs = ground_stations[to_gid]
                                                gsl_distance = distance_m_ground_station_to_satellite(
                                                    dst_gs, satellites[current], str(epoch), str(time)
                                                )
                                                total_dist += gsl_distance
                                                path_trace.append(to_id)
                                                found = True
                                                break
                                            elif next_hop != -1 and next_hop < total_sats:
                                                # ISL hop - calculate actual distance
                                                isl_distance = distance_m_between_satellites(
                                                    satellites[current], satellites[next_hop], str(epoch), str(time)
                                                )
                                                total_dist += isl_distance
                                                path_trace.append(next_hop)
                                                current = next_hop
                                                hops += 1
                                                found = True
                                                break
                                    except (ValueError, IndexError):
                                        continue
                            
                            if not found:
                                break
                        
                        sat_to_gs_distance = total_dist
                        break
        
        if sat_to_gs_distance is not None:
            distance_km = sat_to_gs_distance / 1000.0
            exceeds_threshold = sat_to_gs_distance > 10000000.0  # 10,000 km
            
            # Check if MEO satellites are in the path
            meo_start_id = leo_num_sats
            meo_end_id = total_sats - 1
            meo_nodes_in_path = [n for n in path_trace if meo_start_id <= n < total_sats]
            uses_meo = len(meo_nodes_in_path) > 0
            
            # Calculate hop count (excluding source GS and destination GS)
            # Path: GS → sat1 → sat2 → ... → satN → GS
            # Hops = number of satellite nodes in path
            hop_count = len([n for n in path_trace if isinstance(n, int) and n < total_sats])
            
            print(f"  Path distance (distance_to_ground_station_m): {sat_to_gs_distance:,.0f} m ({distance_km:,.2f} km)")
            print(f"  Hop count: {hop_count} (satellites in path)")
            print(f"  Path trace: {' → '.join(map(str, path_trace))}")
            
            if uses_meo:
                print(f"  ✓ MEO USED: {meo_nodes_in_path}")
            else:
                print(f"  ✗ MEO NOT USED (LEO-only path)")
            
            if exceeds_threshold:
                if uses_meo:
                    print(f"  ✓ EXCEEDS MEO THRESHOLD (>10,000 km) - MEO correctly used")
                else:
                    print(f"  ⚠ EXCEEDS MEO THRESHOLD (>10,000 km) - BUT MEO NOT USED! (Algorithm issue?)")
            else:
                print(f"  ℹ Below MEO threshold - MEO not required")
        else:
            print("  Could not calculate path distance")
        
        print()
    
    print("=" * 70)
    print("Note: Path distances are calculated by tracing forwarding state paths.")
    print("GSL distances are estimated at ~1000 km if not found in ISL data.")
    print("=" * 70)

if __name__ == "__main__":
    # Check all pairs from run_list.py experiment1_pairs_multilayer (3 examples)
    pairs = [
        (1196, 1221, "Mumbai to Lima"),                    # Geodesic: 16,703 km
        (1221, 1203, "Lima to Karachi"),                   # Geodesic: 15,985 km
        (1192, 1204, "Tokyo to Buenos-Aires"),             # Example: min 4 hops and MEO
    ]
    
    for from_id, to_id, pair_name in pairs:
        check_path_distances_for_pair(from_id, to_id, pair_name)
        print()  # Blank line between pairs


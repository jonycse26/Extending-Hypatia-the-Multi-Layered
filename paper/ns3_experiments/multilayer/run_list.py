# This file is used to generate the run list for the multilayer experiments.

# Core values - MATCH step_0_generate_constellation.py parameters
dynamic_state_update_interval_ms = 1000                         # 1000 millisecond update interval (matches time_step_ms)
simulation_end_time_s = 5                                       # 5 seconds (matches duration_s)
pingmesh_interval_ns = 1 * 1000 * 1000                          # A ping every 1ms
enable_isl_utilization_tracking = True                          # Enable utilization tracking
isl_utilization_tracking_interval_ns = 1 * 1000 * 1000 * 1000   # 1 second utilization intervals

# Derivatives
dynamic_state_update_interval_ns = dynamic_state_update_interval_ms * 1000 * 1000
simulation_end_time_ns = simulation_end_time_s * 1000 * 1000 * 1000
dynamic_state = "dynamic_state_" + str(dynamic_state_update_interval_ms) + "ms_for_" + str(simulation_end_time_s) + "s"

# Multi-layer constellation
multilayer_satellite_network = "kuiper_630_meo_isls_plus_grid_with_cross_layer_ground_stations_top_100_algorithm_free_one_multi_layer"
# LEO-only baseline (for comparison)
leo_only_satellite_network = "kuiper_630_isls_plus_grid_ground_stations_top_100_algorithm_free_one_only_over_isls"

# Ground station node ID offset
# Original kuiper_630: 1156 satellites, so ground stations start at node ID 1156
# Multi-layer kuiper_630_meo: 1192 satellites (1156 LEO + 36 MEO), so ground stations start at node ID 1192
# Difference: 36 (number of MEO satellites)
LEO_ONLY_OFFSET = 1156
MULTILAYER_OFFSET = 1192
OFFSET_DIFF = MULTILAYER_OFFSET - LEO_ONLY_OFFSET  # 36

# Ground station indices (in ground_stations.txt file)
# Mumbai: index 4, Lima: index 29, Karachi: index 11
# Tokyo: index 0, Buenos-Aires: index 12

# Example: minimum 4 hops and MEO
EXAMPLE_4HOP_MEO_LEO = (1156, 1168, "Tokyo to Buenos-Aires")       # LEO-only: 1156+0, 1156+12
EXAMPLE_4HOP_MEO_MULTILAYER = (1192, 1204, "Tokyo to Buenos-Aires")  # Multi-layer: 1192+0, 1192+12

# Experiment 1: Multi-layer vs LEO-only comparison (3 examples)
# Format: (from_id_leo_only, to_id_leo_only, description)
# NOTE: MEO threshold is based on path distance via ISLs (distance_to_ground_station_m),
# NOT geodesic distance. The geodesic distances shown are for reference only.
experiment1_pairs_leo = [
    (1160, 1185, "Mumbai to Lima"),                    # Geodesic: 16,703 km (path > 10,000 km - should use MEO)
    (1185, 1167, "Lima to Karachi"),                   # Geodesic: 15,985 km (path > 10,000 km - should use MEO)
    (1156, 1168, "Tokyo to Buenos-Aires"),             # Example: minimum 4 hops and MEO (long path)
]

# Multi-layer versions (add OFFSET_DIFF = 36)
# Mumbai (4): 1160→1196, Lima (29): 1185→1221, Karachi (11): 1167→1203
# Tokyo (0): 1156→1192, Buenos-Aires (12): 1168→1204
# NOTE: MEO when path distance > 10,000 km or estimated hops > 3.
experiment1_pairs_multilayer = [
    (1196, 1221, "Mumbai to Lima"),                    # (path > 10,000 km - should use MEO)
    (1221, 1203, "Lima to Karachi"),                   # (path > 10,000 km - should use MEO)
    (1192, 1204, "Tokyo to Buenos-Aires"),             # Example: minimum 4 hops and MEO
]

# Experiment 2: Different MEO threshold parameters
experiment2_pairs_leo = [
    (1174, 1229, "Very long distance"),  # Should always use MEO
    (1173, 1241, "Medium distance"),     # May or may not use MEO depending on threshold
    (1180, 1177, "Shorter distance"),    # May not use MEO
]

experiment2_pairs_multilayer = [
    (1174 + OFFSET_DIFF, 1229 + OFFSET_DIFF, "Very long distance"),
    (1173 + OFFSET_DIFF, 1241 + OFFSET_DIFF, "Medium distance"),
    (1180 + OFFSET_DIFF, 1177 + OFFSET_DIFF, "Shorter distance"),
]

# Experiment 3: Different traffic loads
experiment3_pairs_leo = [
    (1174, 1229, "High load"),
    (1170, 1252, "Medium load"),
    (1180, 1177, "Low load"),
]

experiment3_pairs_multilayer = [
    (1174 + OFFSET_DIFF, 1229 + OFFSET_DIFF, "High load"),
    (1170 + OFFSET_DIFF, 1252 + OFFSET_DIFF, "Medium load"),
    (1180 + OFFSET_DIFF, 1177 + OFFSET_DIFF, "Low load"),
]


def get_experiment1_comparison_run_list():
    """
    Experiment 1: Compare multi-layer vs LEO-only for long-distance traffic.
    This demonstrates the benefit of MEO backhaul for long-distance communication.
    """
    run_list = []
    # Multi-layer pairs
    for pair in experiment1_pairs_multilayer:
        from_id, to_id, description = pair
        
        # Multi-layer configuration
        run_list.append({
            "name": "multilayer_" + str(from_id) + "_to_" + str(to_id) + "_tcp",
            "satellite_network": multilayer_satellite_network,
            "dynamic_state": dynamic_state,
            "dynamic_state_update_interval_ns": dynamic_state_update_interval_ns,
            "simulation_end_time_ns": simulation_end_time_ns,
            "data_rate_megabit_per_s": 10.0,
            "queue_size_pkt": 100,
            "enable_isl_utilization_tracking": enable_isl_utilization_tracking,
            "isl_utilization_tracking_interval_ns": isl_utilization_tracking_interval_ns,
            "from_id": from_id,
            "to_id": to_id,
            "tcp_socket_type": "TcpNewReno",
            "description": description + " (Multi-layer)",
        })
        
    # LEO-only pairs (use original IDs)
    for pair in experiment1_pairs_leo:
        from_id, to_id, description = pair
        
        # LEO-only baseline
        run_list.append({
            "name": "leo_only_" + str(from_id) + "_to_" + str(to_id) + "_tcp",
            "satellite_network": leo_only_satellite_network,
            "dynamic_state": dynamic_state,
            "dynamic_state_update_interval_ns": dynamic_state_update_interval_ns,
            "simulation_end_time_ns": simulation_end_time_ns,
            "data_rate_megabit_per_s": 10.0,
            "queue_size_pkt": 100,
            "enable_isl_utilization_tracking": enable_isl_utilization_tracking,
            "isl_utilization_tracking_interval_ns": isl_utilization_tracking_interval_ns,
            "from_id": from_id,
            "to_id": to_id,
            "tcp_socket_type": "TcpNewReno",
            "description": description + " (LEO-only)",
        })
    
    # Ping measurements for multi-layer
    for pair in experiment1_pairs_multilayer:
        from_id, to_id, description = pair
        run_list.append({
            "name": "multilayer_" + str(from_id) + "_to_" + str(to_id) + "_pings",
            "satellite_network": multilayer_satellite_network,
            "dynamic_state": dynamic_state,
            "dynamic_state_update_interval_ns": dynamic_state_update_interval_ns,
            "simulation_end_time_ns": simulation_end_time_ns,
            "data_rate_megabit_per_s": 10000.0,
            "queue_size_pkt": 100000,
            "enable_isl_utilization_tracking": enable_isl_utilization_tracking,
            "isl_utilization_tracking_interval_ns": isl_utilization_tracking_interval_ns,
            "from_id": from_id,
            "to_id": to_id,
            "pingmesh_interval_ns": pingmesh_interval_ns,
            "description": description + " (Multi-layer pings)",
        })
    
    # Ping measurements for LEO-only
    for pair in experiment1_pairs_leo:
        from_id, to_id, description = pair
        run_list.append({
            "name": "leo_only_" + str(from_id) + "_to_" + str(to_id) + "_pings",
            "satellite_network": leo_only_satellite_network,
            "dynamic_state": dynamic_state,
            "dynamic_state_update_interval_ns": dynamic_state_update_interval_ns,
            "simulation_end_time_ns": simulation_end_time_ns,
            "data_rate_megabit_per_s": 10000.0,
            "queue_size_pkt": 100000,
            "enable_isl_utilization_tracking": enable_isl_utilization_tracking,
            "isl_utilization_tracking_interval_ns": isl_utilization_tracking_interval_ns,
            "from_id": from_id,
            "to_id": to_id,
            "pingmesh_interval_ns": pingmesh_interval_ns,
            "description": description + " (LEO-only pings)",
        })
    
    return run_list


def get_experiment2_threshold_run_list():
    """
    Experiment 2: Test different distance scenarios to understand MEO threshold behavior.
    Tests pairs at different distances to see when MEO is used.
    """
    run_list = []
    for pair in experiment2_pairs_multilayer:
        from_id, to_id, description = pair
        
        # Multi-layer with TCP
        run_list.append({
            "name": "threshold_test_" + str(from_id) + "_to_" + str(to_id) + "_tcp",
            "satellite_network": multilayer_satellite_network,
            "dynamic_state": dynamic_state,
            "dynamic_state_update_interval_ns": dynamic_state_update_interval_ns,
            "simulation_end_time_ns": simulation_end_time_ns,
            "data_rate_megabit_per_s": 10.0,
            "queue_size_pkt": 100,
            "enable_isl_utilization_tracking": enable_isl_utilization_tracking,
            "isl_utilization_tracking_interval_ns": isl_utilization_tracking_interval_ns,
            "from_id": from_id,
            "to_id": to_id,
            "tcp_socket_type": "TcpNewReno",
            "description": description,
        })
        
        # Ping measurements
        run_list.append({
            "name": "threshold_test_" + str(from_id) + "_to_" + str(to_id) + "_pings",
            "satellite_network": multilayer_satellite_network,
            "dynamic_state": dynamic_state,
            "dynamic_state_update_interval_ns": dynamic_state_update_interval_ns,
            "simulation_end_time_ns": simulation_end_time_ns,
            "data_rate_megabit_per_s": 10000.0,
            "queue_size_pkt": 100000,
            "enable_isl_utilization_tracking": enable_isl_utilization_tracking,
            "isl_utilization_tracking_interval_ns": isl_utilization_tracking_interval_ns,
            "from_id": from_id,
            "to_id": to_id,
            "pingmesh_interval_ns": pingmesh_interval_ns,
            "description": description,
        })
    
    return run_list


def get_experiment3_load_run_list():
    """
    Experiment 3: Test multi-layer performance under different traffic loads.
    Same pairs with different data rates to evaluate MEO utilization efficiency.
    """
    run_list = []
    data_rates = [5.0, 10.0, 20.0]  # Different load levels
    load_names = ["low_load", "medium_load", "high_load"]
    
    for pair in experiment3_pairs_multilayer:
        from_id, to_id, description = pair
        for data_rate, load_name in zip(data_rates, load_names):
            # TCP runs
            run_list.append({
                "name": "load_test_" + load_name + "_" + str(from_id) + "_to_" + str(to_id) + "_tcp",
                "satellite_network": multilayer_satellite_network,
                "dynamic_state": dynamic_state,
                "dynamic_state_update_interval_ns": dynamic_state_update_interval_ns,
                "simulation_end_time_ns": simulation_end_time_ns,
                "data_rate_megabit_per_s": data_rate,
                "queue_size_pkt": 100,
                "enable_isl_utilization_tracking": enable_isl_utilization_tracking,
                "isl_utilization_tracking_interval_ns": isl_utilization_tracking_interval_ns,
                "from_id": from_id,
                "to_id": to_id,
                "tcp_socket_type": "TcpNewReno",
                "description": description + " (" + load_name + ")",
            })
    
    return run_list


def get_all_runs():
    """Get all experiment runs."""
    runs = []
    runs.extend(get_experiment1_comparison_run_list())
    runs.extend(get_experiment2_threshold_run_list())
    runs.extend(get_experiment3_load_run_list())
    return runs


def get_tcp_run_list():
    """Get TCP runs only."""
    return [r for r in get_all_runs() if "tcp" in r["name"]]


def get_pings_run_list():
    """Get ping runs only."""
    return [r for r in get_all_runs() if "pings" in r["name"]]


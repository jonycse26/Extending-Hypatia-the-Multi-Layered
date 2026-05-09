# This file is used to generate the run list for the multilayer experiments.
# Core values - MATCH step_0_generate_constellation.py parameters

dynamic_state_update_interval_ms = 1000
simulation_end_time_s = 25
pingmesh_interval_ns = 1 * 1000 * 1000                          
enable_isl_utilization_tracking = True                         
isl_utilization_tracking_interval_ns = 1 * 1000 * 1000 * 1000   

# Derivatives
dynamic_state_update_interval_ns = dynamic_state_update_interval_ms * 1000 * 1000
simulation_end_time_ns = simulation_end_time_s * 1000 * 1000 * 1000
dynamic_state = "dynamic_state_" + str(dynamic_state_update_interval_ms) + "ms_for_" + str(simulation_end_time_s) + "s"

# Multi-layer constellation
multilayer_satellite_network = "kuiper_630_meo_isls_plus_grid_with_cross_layer_ground_stations_top_100_algorithm_free_one_multi_layer"


def multilayer_satellite_network_xlm(max_leo_per_meo):
    """
    Constellation folder name when MainHelperMultiLayer(..., max_leo_per_meo=N) was used
    (suffix _xlmN under gen_data / ns-3 [SATELLITE-NETWORK]).
    """
    return multilayer_satellite_network + "_xlm%d" % int(max_leo_per_meo)


# LEO-only baseline (for comparison)
leo_only_satellite_network = "kuiper_630_isls_plus_grid_ground_stations_top_100_algorithm_free_one_only_over_isls"

# Ground station node ID offset
LEO_ONLY_OFFSET = 1156
MULTILAYER_OFFSET = 1192
OFFSET_DIFF = MULTILAYER_OFFSET - LEO_ONLY_OFFSET  # 36


# Example: minimum 4 hops and MEO
EXAMPLE_4HOP_MEO_LEO = (1156, 1168, "Tokyo to Buenos-Aires")       
EXAMPLE_4HOP_MEO_MULTILAYER = (1192, 1204, "Tokyo to Buenos-Aires")  

# Experiment 1: Multi-layer vs LEO-only comparison (3 examples)
experiment1_pairs_leo = [
    (1160, 1185, "Mumbai to Lima"),
    (1185, 1167, "Lima to Karachi"),
    (1156, 1168, "Tokyo to Buenos-Aires"),
]

# Multi-layer versions (add OFFSET_DIFF = 36)
experiment1_pairs_multilayer = [
    (1196, 1221, "Mumbai to Lima"),
    (1221, 1203, "Lima to Karachi"),
    (1192, 1204, "Tokyo to Buenos-Aires"),
]

# Aliases for the three example scripts (example_1 = example_1_threshold_sensitivity.py)
example_three_pairs_leo = experiment1_pairs_leo
example_three_pairs_multilayer = experiment1_pairs_multilayer

# Experiment 2: MEO threshold / distance scenarios 

experiment2_pairs_leo = [
    (1156, 1168, "Very long distance (Tokyo to Buenos-Aires)"),
    (1160, 1185, "Long distance (Mumbai to Lima)"),
    (1185, 1167, "Shorter distance (Lima to Karachi)"),
]

experiment2_pairs_multilayer = [
    (1192, 1204, "Very long distance (Tokyo to Buenos-Aires)"),
    (1196, 1221, "Long distance (Mumbai to Lima)"),
    (1221, 1203, "Shorter distance (Lima to Karachi)"),
]

# Experiment 3: Geographic distance tiers (short / medium / long) — README-aligned pairs;
# see example_3_distance_based_scenario_analysis.py (default dynamic_state, no md sweep).
experiment3_distance_tiers = ("short", "medium", "long")

experiment3_pairs_multilayer = [
    (1209, 1277, "Short distance (Manila to Dalian, ~2,800 km)"),
    (1206, 1288, "Medium distance (Istanbul to Nairobi, ~4,500 km)"),
    (1210, 1265, "Long distance (Rio de Janeiro to St. Petersburg, ~11,000 km)"),
]

experiment3_pairs_leo = [
    (1173, 1241, "Short distance (Manila to Dalian, ~2,800 km)"),
    (1170, 1252, "Medium distance (Istanbul to Nairobi, ~4,500 km)"),
    (1174, 1229, "Long distance (Rio de Janeiro to St. Petersburg, ~11,000 km)"),
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


def example3_tcp_run_name(distance_tier_slug, from_id, to_id):
    """e.g. example3_distance_short_1209_to_1277_tcp"""
    return "example3_distance_%s_%d_to_%d_tcp" % (distance_tier_slug, from_id, to_id)


def get_experiment3_distance_based_scenario_run_list():
    """
    Experiment 3: Distance-based scenario analysis — same as
    ``example_3_distance_based_scenario_analysis.py``.

    Six TCP runs (short / medium / long × LEO-only vs multilayer) using the default
    ``dynamic_state`` (no ``_mh3_md*`` suffix). Fixed 10 Mbps; LEO uses
    ``experiment3_pairs_leo``, multilayer uses ``experiment3_pairs_multilayer``
    (same geography; different ground node IDs). Names look like
    ``example3_distance_short_1173_to_1241_tcp`` (LEO) and
    ``example3_distance_short_1209_to_1277_tcp`` (multilayer).
    """
    run_list = []
    data_rate = 10.0

    for tier, pair in zip(experiment3_distance_tiers, experiment3_pairs_multilayer):
        from_id, to_id, description = pair
        run_list.append({
            "name": example3_tcp_run_name(tier, from_id, to_id),
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
            "description": description + " (Multilayer)",
            "distance_tier": tier,
        })

    for tier, pair in zip(experiment3_distance_tiers, experiment3_pairs_leo):
        from_id, to_id, description = pair
        run_list.append({
            "name": example3_tcp_run_name(tier, from_id, to_id),
            "satellite_network": leo_only_satellite_network,
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
            "description": description + " (LEO-only)",
            "distance_tier": tier,
        })

    return run_list


def get_experiment3_cross_layer_connectivity_run_list():
    """Deprecated alias for ``get_experiment3_distance_based_scenario_run_list()``."""
    return get_experiment3_distance_based_scenario_run_list()


def get_all_runs():
    """
    Core run definitions (experiments 1–2) used to build ``get_tcp_run_list()`` and ping lists.

    For the full step_1 / step_2 / step_3 TCP pipeline (including experiment 3), use
    ``get_tcp_run_list_for_step3_plots()`` — same as ``get_tcp_run_list()`` plus
    experiment 3 TCP runs (default ``dynamic_state`` only; no extra fstate trees).

    ``get_all_runs_with_experiment3()`` = these runs + experiment 3 TCP dicts (for tooling).
    """
    runs = []
    runs.extend(get_experiment1_comparison_run_list())
    runs.extend(get_experiment2_threshold_run_list())
    return runs


def get_all_runs_with_experiment3():
    """All runs including experiment 3 distance-scenario TCP (for custom tooling, not default step_2/3)."""
    runs = get_all_runs()
    runs.extend(get_experiment3_distance_based_scenario_run_list())
    return runs


def get_all_runs_with_cross_layer():
    """Deprecated alias for ``get_all_runs_with_experiment3()`` (old cross-layer naming)."""
    return get_all_runs_with_experiment3()


# Deprecated aliases
get_experiment3_load_run_list = get_experiment3_distance_based_scenario_run_list


def get_tcp_run_list():
    """Get TCP runs for the default pipeline (core experiments only)."""
    return [r for r in get_all_runs() if "tcp" in r["name"]]


def get_tcp_run_list_for_step3_plots():
    """
    Full TCP list for ``step_1_generate_runs.py``, ``step_2_run.py``, and ``step_3_generate_plots.py``:

    - Experiments 1–2: same as ``get_tcp_run_list()`` — **multilayer vs LEO-only** comparison
      (``multilayer_*`` / ``leo_only_*``), plus ``threshold_test_*`` (experiment 2).
    - Experiment 3: ``example3_distance_{short,medium,long}_*_tcp`` (multilayer, distance tiers).

    Use ``get_tcp_run_list()`` alone only when you need the core list without experiment 3.
    """
    return get_tcp_run_list() + get_experiment3_distance_based_scenario_run_list()


def get_pings_run_list():
    """Get ping runs only."""
    return [r for r in get_all_runs() if "pings" in r["name"]]


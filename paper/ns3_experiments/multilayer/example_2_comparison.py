#!/usr/bin/env python3
"""
Example 2: Multi-Layer vs LEO-Only Performance Comparison

This example compares the performance of multi-layer (LEO + MEO) vs LEO-only
constellations for the same three city pairs as run_list.experiment1_pairs_*:
Mumbai–Lima, Lima–Karachi, Tokyo–Buenos-Aires.

It demonstrates:
- Reduced latency for long-distance pairs via MEO backhaul (where applicable)
- Lower LEO ISL utilization (traffic offloaded to MEO)
- Path efficiency differences between multi-layer and LEO-only

Note: step_1_generate_runs.py already creates the same multilayer + LEO-only TCP and ping
runs (experiment 1). Use this script for the six TCP configs only, or when step_1 would wipe
runs/ and you want to add just these. main() chdirs to this directory so templates/ resolve.
"""

import exputil
import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Add parent directory to path for imports
sys.path.insert(0, _SCRIPT_DIR)

try:
    from run_list import *
except ImportError:
    print("Error: Could not import run_list. Make sure you're running from the multilayer directory.")
    sys.exit(1)

local_shell = exputil.LocalShell()

# Same three pairs as run_list.experiment1_pairs_leo / experiment1_pairs_multilayer
COMPARISON_PAIRS = [
    {
        "from_id_leo": f_leo,
        "to_id_leo": t_leo,
        "from_id_multilayer": f_ml,
        "to_id_multilayer": t_ml,
        "description": desc,
    }
    for (f_leo, t_leo, desc), (f_ml, t_ml, _) in zip(
        experiment1_pairs_leo, experiment1_pairs_multilayer
    )
]

def create_run_config(pair, is_multilayer):
    """
    Create a run configuration for a given pair.
    
    Args:
        pair: Dictionary with from_id, to_id, description
        is_multilayer: True for multi-layer, False for LEO-only
    """
    if is_multilayer:
        from_id = pair["from_id_multilayer"]
        to_id = pair["to_id_multilayer"]
        prefix = "multilayer"
        satellite_network = multilayer_satellite_network
    else:
        from_id = pair["from_id_leo"]
        to_id = pair["to_id_leo"]
        prefix = "leo_only"
        satellite_network = leo_only_satellite_network
    
    run_name = "%s_%d_to_%d_tcp" % (prefix, from_id, to_id)
    run_dir = "runs/" + run_name
    local_shell.remove_force_recursive(run_dir)
    local_shell.make_full_dir(run_dir)
    
    # Copy and configure template
    local_shell.copy_file("templates/template_tcp_a_b_config_ns3.properties", 
                          run_dir + "/config_ns3.properties")
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[SATELLITE-NETWORK]", 
                                          satellite_network)
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[DYNAMIC-STATE]", 
                                          dynamic_state)
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[DYNAMIC-STATE-UPDATE-INTERVAL-NS]", 
                                          str(dynamic_state_update_interval_ns))
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[SIMULATION-END-TIME-NS]", 
                                          str(simulation_end_time_ns))
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[ISL-DATA-RATE-MEGABIT-PER-S]", 
                                          "10.0")
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[GSL-DATA-RATE-MEGABIT-PER-S]", 
                                          "10.0")
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[ISL-MAX-QUEUE-SIZE-PKTS]", 
                                          "100")
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[GSL-MAX-QUEUE-SIZE-PKTS]", 
                                          "100")
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[ENABLE-ISL-UTILIZATION-TRACKING]", 
                                          "true")
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[ISL-UTILIZATION-TRACKING-INTERVAL-NS-COMPLETE]",
                                          "isl_utilization_tracking_interval_ns=" + 
                                          str(isl_utilization_tracking_interval_ns))
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[TCP-SOCKET-TYPE]", 
                                          "TcpNewReno")
    
    # Create schedule.csv
    local_shell.copy_file("templates/template_tcp_a_b_schedule.csv", 
                          run_dir + "/schedule.csv")
    local_shell.sed_replace_in_file_plain(run_dir + "/schedule.csv", 
                                          "[FROM]", 
                                          str(from_id))
    local_shell.sed_replace_in_file_plain(run_dir + "/schedule.csv", 
                                          "[TO]", 
                                          str(to_id))
    # Remove any trailing empty lines
    local_shell.perfect_exec("sed -i '/^$/d' " + run_dir + "/schedule.csv",
                             output_redirect=exputil.OutputRedirect.CONSOLE)
    
    return run_name, run_dir

def main():
    """
    Generate run configurations for multi-layer vs LEO-only comparison.
    """
    os.chdir(_SCRIPT_DIR)
    print("=" * 70)
    print("Example 2: Multi-Layer vs LEO-Only Performance Comparison")
    print("=" * 70)
    print()
    print("This example compares multi-layer (LEO + MEO) vs LEO-only")
    print("constellations for long-distance communication.")
    print()
    print("Test pairs:")
    for i, pair in enumerate(COMPARISON_PAIRS, 1):
        print("  %d. %s" % (i, pair["description"]))
    print()
    
    runs_created = []
    
    for pair in COMPARISON_PAIRS:
        print("Creating configurations for: %s" % pair["description"])
        
        # Multi-layer configuration
        run_name_ml, run_dir_ml = create_run_config(pair, is_multilayer=True)
        runs_created.append((run_name_ml, "Multi-layer"))
        print("  ✓ Multi-layer: %s" % run_name_ml)
        
        # LEO-only configuration
        run_name_leo, run_dir_leo = create_run_config(pair, is_multilayer=False)
        runs_created.append((run_name_leo, "LEO-only"))
        print("  ✓ LEO-only: %s" % run_name_leo)
        print()
    
    print("=" * 70)
    print("Configuration Summary")
    print("=" * 70)
    print()
    print("Created %d run configurations:" % len(runs_created))
    for run_name, config_type in runs_created:
        print("  - %s (%s)" % (run_name, config_type))
    print()
    print("To simulate:")
    print("  - Full pipeline (exp 1–2 + 3 TCP + pings): from this dir, python step_2_run.py")
    print("  - Or: evaluation_utils.run_ns3(\"runs/<name>\") after chdir to this directory")
    print("  - Or one-off waf (from ns3-sat-sim/simulator):")
    print("    ./waf --run \"main_satnet --run_dir=../../paper/ns3_experiments/multilayer/runs/<run_name>\"")
    print()
    print("After simulations, compare results:")
    print("  - RTT: Compare pingmesh results between multi-layer and LEO-only")
    print("  - Throughput: Compare TCP flow progress")
    print("  - ISL utilization: Compare LEO ISL usage (should be lower in multi-layer)")
    print("  - Path length: Check routing paths (multi-layer should use MEO)")
    print()
    print("Expected results:")
    print("  - Multi-layer often lower latency / better goodput on long paths when MEO backhaul helps")
    print("  - Multi-layer may show lower LEO ISL utilization when traffic uses MEO ISLs")
    print("  - MEO node ID range: between LEO shell and GS (see evaluation_utils.get_meo_node_id_range())")
    print()
    
    return 0

if __name__ == "__main__":
    exit(main())


#!/usr/bin/env python3
"""
Example 2: Multi-Layer vs LEO-Only Performance Comparison

This example compares the performance of multi-layer (LEO + MEO) vs LEO-only
constellations for long-distance communication. It demonstrates:
- Reduced latency for long-distance pairs via MEO backhaul
- Lower LEO ISL utilization (traffic offloaded to MEO)
- Improved path efficiency for distances > 10,000 km

This experiment evaluates the benefit of adding MEO satellites as backhaul.
"""

import exputil
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from run_list import *
except ImportError:
    print("Error: Could not import run_list. Make sure you're running from the multilayer directory.")
    sys.exit(1)

local_shell = exputil.LocalShell()

# Test pairs for comparison (long-distance pairs that benefit from MEO)
COMPARISON_PAIRS = [
    {
        "from_id_leo": 1174,
        "to_id_leo": 1229,
        "from_id_multilayer": 1174 + OFFSET_DIFF,
        "to_id_multilayer": 1229 + OFFSET_DIFF,
        "description": "Rio de Janeiro to St. Petersburg (~11,000 km)"
    },
    {
        "from_id_leo": 1173,
        "to_id_leo": 1241,
        "from_id_multilayer": 1173 + OFFSET_DIFF,
        "to_id_multilayer": 1241 + OFFSET_DIFF,
        "description": "Manila to Dalian (~2,800 km)"
    },
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
    print("To run all simulations:")
    print("  python step_2_run.py")
    print()
    print("Or run individually:")
    for run_name, config_type in runs_created:
        print("  cd ../../../ns3-sat-sim/simulator")
        print("  ./waf --run \"main_satnet --run_dir=../../paper/ns3_experiments/multilayer/runs/%s\"" % run_name)
        print()
    print("After simulations, compare results:")
    print("  - RTT: Compare pingmesh results between multi-layer and LEO-only")
    print("  - Throughput: Compare TCP flow progress")
    print("  - ISL utilization: Compare LEO ISL usage (should be lower in multi-layer)")
    print("  - Path length: Check routing paths (multi-layer should use MEO)")
    print()
    print("Expected results:")
    print("  - Multi-layer should show lower latency for long-distance pairs")
    print("  - Multi-layer should have lower LEO ISL utilization")
    print("  - Multi-layer paths should include MEO satellites (node IDs 1156-1191)")
    print()
    
    return 0

if __name__ == "__main__":
    exit(main())


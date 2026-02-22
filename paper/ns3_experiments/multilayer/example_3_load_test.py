#!/usr/bin/env python3
"""
Example 3: Load Performance Evaluation

This example evaluates multi-layer constellation performance under different
traffic loads. It tests:
- Low load (5 Mbps)
- Medium load (10 Mbps)
- High load (20 Mbps)

This demonstrates how MEO backhaul helps under different load conditions and
shows the scalability benefits of multi-layer constellations.
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

# Test pair for load evaluation
LOAD_TEST_PAIR = {
    "from_id": 1210,  # Rio de Janeiro (multilayer offset applied)
    "to_id": 1265,    # St. Petersburg (multilayer offset applied)
    "description": "Rio de Janeiro to St. Petersburg (~11,000 km)"
}

# Different load levels to test
LOAD_LEVELS = [
    {"name": "low", "rate_mbps": 5.0, "description": "Low load (5 Mbps)"},
    {"name": "medium", "rate_mbps": 10.0, "description": "Medium load (10 Mbps)"},
    {"name": "high", "rate_mbps": 20.0, "description": "High load (20 Mbps)"},
]

def create_run_config(load_level):
    """
    Create a run configuration for a given load level.
    
    Args:
        load_level: Dictionary with name, rate_mbps, description
    """
    run_name = "load_test_%s_load_%d_to_%d_tcp" % (
        load_level["name"],
        LOAD_TEST_PAIR["from_id"],
        LOAD_TEST_PAIR["to_id"]
    )
    run_dir = "runs/" + run_name
    local_shell.remove_force_recursive(run_dir)
    local_shell.make_full_dir(run_dir)
    
    # Copy and configure template
    local_shell.copy_file("templates/template_tcp_a_b_config_ns3.properties", 
                          run_dir + "/config_ns3.properties")
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[SATELLITE-NETWORK]", 
                                          multilayer_satellite_network)
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
                                          str(load_level["rate_mbps"]))
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[GSL-DATA-RATE-MEGABIT-PER-S]", 
                                          str(load_level["rate_mbps"]))
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
                                          str(LOAD_TEST_PAIR["from_id"]))
    local_shell.sed_replace_in_file_plain(run_dir + "/schedule.csv", 
                                          "[TO]", 
                                          str(LOAD_TEST_PAIR["to_id"]))
    # Remove any trailing empty lines
    local_shell.perfect_exec("sed -i '/^$/d' " + run_dir + "/schedule.csv",
                             output_redirect=exputil.OutputRedirect.CONSOLE)
    
    return run_name, run_dir

def main():
    """
    Generate run configurations for load performance evaluation.
    """
    print("=" * 70)
    print("Example 3: Load Performance Evaluation")
    print("=" * 70)
    print()
    print("This example evaluates multi-layer constellation performance")
    print("under different traffic loads.")
    print()
    print("Test pair: %s" % LOAD_TEST_PAIR["description"])
    print()
    print("Load levels:")
    for load_level in LOAD_LEVELS:
        print("  - %s: %.1f Mbps" % (load_level["description"], load_level["rate_mbps"]))
    print()
    
    runs_created = []
    
    for load_level in LOAD_LEVELS:
        print("Creating configuration for: %s" % load_level["description"])
        run_name, run_dir = create_run_config(load_level)
        runs_created.append((run_name, load_level))
        print("  ✓ Created: %s" % run_name)
        print()
    
    print("=" * 70)
    print("Configuration Summary")
    print("=" * 70)
    print()
    print("Created %d run configurations:" % len(runs_created))
    for run_name, load_level in runs_created:
        print("  - %s (%s)" % (run_name, load_level["description"]))
    print()
    print("To run all simulations:")
    print("  python step_2_run.py")
    print()
    print("Or run individually:")
    for run_name, load_level in runs_created:
        print("  cd ../../../ns3-sat-sim/simulator")
        print("  ./waf --run \"main_satnet --run_dir=../../paper/ns3_experiments/multilayer/runs/%s\"" % run_name)
        print()
    print("After simulations, analyze results:")
    print("  - Throughput: Compare TCP flow progress across load levels")
    print("  - Latency: Compare RTT under different loads")
    print("  - Queue utilization: Check queue sizes in ISL utilization logs")
    print("  - MEO efficiency: Compare MEO ISL usage across load levels")
    print()
    print("Expected results:")
    print("  - Multi-layer should maintain better performance under high load")
    print("  - MEO backhaul should help distribute load across layers")
    print("  - Lower queue buildup in LEO ISLs due to MEO offloading")
    print("  - More consistent latency under varying load conditions")
    print()
    
    return 0

if __name__ == "__main__":
    exit(main())


#!/usr/bin/env python3
"""
Example 1: Proof-of-Concept MEO Routing Demonstration

This example demonstrates that the multi-layer constellation can route traffic
via MEO satellites. It shows:
- Ground stations connect to LEO satellites
- Long-distance traffic (>10,000 km or >3 hops) is routed via MEO backhaul
- MEO satellites act as backhaul to relieve LEO ISL congestion

This is a minimal proof-of-concept that verifies MEO routing capability.
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

# Configuration for proof-of-concept
PROOF_OF_CONCEPT_PAIR = {
    "from_id": 1210,  # Rio de Janeiro (multilayer offset applied)
    "to_id": 1265,    # St. Petersburg (multilayer offset applied)
    "description": "Rio de Janeiro to St. Petersburg (~11,000 km - should use MEO)"
}

def main():
    """
    Run a single proof-of-concept simulation demonstrating MEO routing.
    """
    print("=" * 70)
    print("Example 1: Proof-of-Concept MEO Routing")
    print("=" * 70)
    print()
    print("This example demonstrates traffic routing via MEO satellites.")
    print("Pair: %s" % PROOF_OF_CONCEPT_PAIR["description"])
    print("Distance: ~11,000 km (should trigger MEO backhaul)")
    print()

    # Create run directory
    run_name = "example1_meo_routing_%d_to_%d_tcp" % (
        PROOF_OF_CONCEPT_PAIR["from_id"],
        PROOF_OF_CONCEPT_PAIR["to_id"]
    )
    run_dir = "runs/" + run_name
    local_shell.remove_force_recursive(run_dir)
    local_shell.make_full_dir(run_dir)
    local_shell.make_full_dir(run_dir + "/logs_ns3")

    print("Creating run configuration: %s" % run_name)

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
                                          str(PROOF_OF_CONCEPT_PAIR["from_id"]))
    local_shell.sed_replace_in_file_plain(run_dir + "/schedule.csv", 
                                          "[TO]", 
                                          str(PROOF_OF_CONCEPT_PAIR["to_id"]))
    # Remove any trailing empty lines
    local_shell.perfect_exec("sed -i '/^$/d' " + run_dir + "/schedule.csv",
                             output_redirect=exputil.OutputRedirect.CONSOLE)

    print()
    print("Configuration created successfully!")
    print("Running ns-3 simulation now (this can take several minutes)...")

    # Run the ns-3 simulation automatically, like the other examples
    sim_cmd = (
        "cd ../../../ns3-sat-sim/simulator; "
        "./waf --run=\"main_satnet --run_dir='../../paper/ns3_experiments/multilayer/%s'\" "
        "2>&1 | tee '../../paper/ns3_experiments/multilayer/%s/logs_ns3/console.txt'"
    ) % (run_dir, run_dir)

    try:
        local_shell.perfect_exec(sim_cmd, output_redirect=exputil.OutputRedirect.CONSOLE)
    except Exception as e:
        print("")
        print("ERROR: ns-3 simulation failed to run automatically.")
        print("You can try to run it manually with:")
        print("  cd ../../../ns3-sat-sim/simulator")
        print("  ./waf --run \"main_satnet --run_dir=../../paper/ns3_experiments/multilayer/%s\"" % run_dir)
        print("Exception was: %s" % str(e))
        return 1

    print()
    print("Simulation finished.")
    print()
    print("Generating plots and processed data for Example 1...")

    # Run the plotting helper script (equivalent to step_3 for this single run)
    try:
        local_shell.perfect_exec(
            "bash create_example1_plots.sh",
            output_redirect=exputil.OutputRedirect.CONSOLE
        )
    except Exception as e:
        print("")
        print("WARNING: Automatic plot generation failed.")
        print("You can generate plots manually with:")
        print("  cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/ns3-sat-sim/simulator/contrib/basic-sim/tools/plotting/plot_tcp_flow")
        print("  python plot_tcp_flow.py \\")
        print("    ../../../../../../../paper/ns3_experiments/multilayer/%s/logs_ns3 \\" % run_dir)
        print("    ../../../../../../../paper/ns3_experiments/multilayer/data/%s \\" % run_name)
        print("    ../../../../../../../paper/ns3_experiments/multilayer/pdf/%s \\" % run_name)
        print("    0 1000000000")
        print("Exception was: %s" % str(e))

    print()
    print("Simulation and plotting complete.")
    print()
    print("After simulation, check results:")
    print("  - Routing paths: %s/logs_ns3/console.txt" % run_dir)
    print("  - ISL utilization: %s/logs_ns3/isl_utilization.csv" % run_dir)
    print("  - TCP flow progress: %s/logs_ns3/tcp_flow_0_progress.csv" % run_dir)
    print()
    print("To generate PDF plots and processed data files:")
    print("  After the simulation completes, run:")
    print("  cd ../../../ns3-sat-sim/simulator/contrib/basic-sim/tools/plotting/plot_tcp_flow")
    print("  python plot_tcp_flow.py \\")
    print("    ../../../../../../../paper/ns3_experiments/multilayer/%s/logs_ns3 \\" % run_dir)
    print("    ../../../../../../../paper/ns3_experiments/multilayer/data/%s \\" % run_name)
    print("    ../../../../../../../paper/ns3_experiments/multilayer/pdf/%s \\" % run_name)
    print("    0 1000000000")
    print()
    print("Result file locations:")
    print("  - PDF plots: pdf/%s/" % run_name)
    print("    * plot_tcp_flow_time_vs_progress_0.pdf")
    print("    * plot_tcp_flow_time_vs_rate_0.pdf")
    print("    * plot_tcp_flow_time_vs_cwnd_0.pdf")
    print("    * plot_tcp_flow_time_vs_rtt_0.pdf")
    print("  - Processed data: data/%s/" % run_name)
    print("    * tcp_flow_0_progress.csv")
    print("    * tcp_flow_0_rate_in_intervals.csv")
    print("    * tcp_flow_0_cwnd.csv")
    print("    * tcp_flow_0_rtt.csv")
    print()
    print("Expected behavior:")
    print("  - Traffic should route via MEO satellites (node IDs 1156-1191)")
    print("  - Path should show: LEO -> MEO -> LEO pattern")
    print("  - MEO ISL utilization should be > 0")
    print()
    
    return 0

if __name__ == "__main__":
    exit(main())


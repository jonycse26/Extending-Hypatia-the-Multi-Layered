# this is a script to generate the satellite network state for both
# multilayer and leo-only constellations.


"""
Step 0: Generate multi-layer constellation state.

This script generates the satellite network state for both:
1. Multi-layer constellation (LEO + MEO)
2. LEO-only baseline (for comparison)

Run this before step_1_generate_runs.py
"""

import sys
import os
import subprocess

# Add path to satellite_networks_state
script_dir = os.path.dirname(os.path.abspath(__file__))
satellite_networks_dir = os.path.abspath(os.path.join(script_dir, '../../satellite_networks_state'))
sys.path.insert(0, satellite_networks_dir)

def run_command(cmd, description):
    """Run a command and print status."""
    print("\n" + "="*70)
    print(description)
    print("="*70)
    print("Command: %s" % cmd)
    # Path from multilayer/ to satellite_networks_state/
    # multilayer/ -> ../ -> ns3_experiments/ -> ../ -> paper/ -> satellite_networks_state/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.join(script_dir, '../../satellite_networks_state')
    target_dir = os.path.abspath(target_dir)
    
    if not os.path.exists(target_dir):
        print("ERROR: Target directory does not exist: %s" % target_dir)
        print("Current script location: %s" % script_dir)
        return False
    
    result = subprocess.run(cmd, shell=True, cwd=target_dir)
    if result.returncode != 0:
        print("ERROR: Command failed with return code %d" % result.returncode)
        return False
    print("SUCCESS: %s completed" % description)
    return True

def main():
    print("Generating satellite constellation states for multi-layer experiments...")
    print("\nThis will generate:")
    print("  1. Multi-layer constellation (kuiper_630_meo)")
    print("  2. LEO-only baseline (kuiper_630) for comparison")
    
    # Parameters - OPTIMIZED FOR FAST GENERATION (testing/demo purposes)
    # Reduced duration and increased time step to minimize generation time
    duration_s = 5          # Reduced from 25 to 5 seconds (5x faster)
    time_step_ms = 1000     # Increased from 500 to 1000 ms (2x faster)
    num_threads = 4         # Keep 4 threads for parallel processing
    # Total time steps: (5 * 1000) / 1000 + 1 = 6 time steps
    # Expected time: ~1-2 hours total (instead of 10-21 hours)
    
    # Generate multi-layer constellation
    cmd_multilayer = (
        "python main_kuiper_630_meo.py "
        "%d %d isls_plus_grid_with_cross_layer ground_stations_top_100 "
        "algorithm_free_one_multi_layer %d"
        % (duration_s, time_step_ms, num_threads)
    )
    
    if not run_command(cmd_multilayer, "Generating multi-layer constellation (LEO + MEO)"):
        print("\nERROR: Failed to generate multi-layer constellation")
        return 1
    
    # Generate LEO-only constellation
    cmd_leo = (
        "python main_kuiper_630.py "
        "%d %d isls_plus_grid ground_stations_top_100 "
        "algorithm_free_one_only_over_isls %d"
        % (duration_s, time_step_ms, num_threads)
    )
    
    if not run_command(cmd_leo, "Generating LEO-only constellation"):
        print("\nERROR: Failed to generate LEO-only constellation")
        return 1
    
    print("\n" + "="*70)
    print("SUCCESS: All constellation states generated!")
    print("="*70)
    print("\nYou can now proceed with:")
    print("  python step_1_generate_runs.py")
    return 0

if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3
"""
Check progress of constellation generation.

This script checks how many dynamic state files have been generated
and estimates remaining time.

Defaults match run_list.py (simulation_end_time_s, dynamic_state_update_interval_ms).

Usage:
  python check_progress.py [constellation_prefix] [duration_s] [time_step_ms]

Examples:
  python check_progress.py
  python check_progress.py kuiper_630_meo
  python check_progress.py kuiper_630_meo 25 1000
"""

import os
import sys
import glob
import time

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
try:
    from run_list import simulation_end_time_s as DEFAULT_DURATION_S
    from run_list import dynamic_state_update_interval_ms as DEFAULT_TIME_STEP_MS
except Exception:
    DEFAULT_DURATION_S = 25
    DEFAULT_TIME_STEP_MS = 1000


def check_progress(constellation_name="kuiper_630_meo", duration_s=None, time_step_ms=None):
    """Check generation progress."""
    if duration_s is None:
        duration_s = DEFAULT_DURATION_S
    if time_step_ms is None:
        time_step_ms = DEFAULT_TIME_STEP_MS

    # Calculate expected number of files
    time_step_ns = time_step_ms * 1_000_000
    duration_ns = duration_s * 1_000_000_000
    expected_files = int(duration_ns / time_step_ns) + 1
    
    # Find generated files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    gen_data_dir = os.path.join(script_dir, '../../satellite_networks_state/gen_data')
    
    # The directory name includes the full configuration
    # Look for directories starting with the constellation name
    if os.path.exists(gen_data_dir):
        dirs = [d for d in os.listdir(gen_data_dir) 
                if os.path.isdir(os.path.join(gen_data_dir, d)) and d.startswith(constellation_name)]
        if not dirs:
            print(f"ERROR: No constellation directory found starting with: {constellation_name}")
            print(f"Available directories in {gen_data_dir}:")
            if os.path.exists(gen_data_dir):
                for d in os.listdir(gen_data_dir):
                    if os.path.isdir(os.path.join(gen_data_dir, d)):
                        print(f"  - {d}")
            return
        constellation_dir = os.path.join(gen_data_dir, dirs[0])
    else:
        print(f"ERROR: gen_data directory not found: {gen_data_dir}")
        return
    
    # Find the specific dynamic_state directory matching our parameters
    # Format: dynamic_state_{time_step_ms}ms_for_{duration_s}s
    target_dynamic_state_dir = f"dynamic_state_{time_step_ms}ms_for_{duration_s}s"
    dynamic_state_path = os.path.join(constellation_dir, target_dynamic_state_dir)
    
    # Count generated files from the specific directory
    pattern = os.path.join(dynamic_state_path, "fstate_*.txt")
    generated_files = glob.glob(pattern)
    
    # If not found in specific directory, try to find any dynamic_state directory
    if not generated_files:
        # Try to find any dynamic_state directory
        possible_patterns = [
            os.path.join(constellation_dir, "dynamic_state_ground_stations", "fstate_*.txt"),
            os.path.join(constellation_dir, "dynamic_state_*", "fstate_*.txt"),
        ]
        for pattern in possible_patterns:
            files = glob.glob(pattern, recursive=True)
            if files:
                generated_files = files
                # Extract the actual directory name
                if files:
                    actual_dir = os.path.dirname(files[0])
                    actual_dir_name = os.path.basename(actual_dir)
                    print(f"NOTE: Found files in '{actual_dir_name}' instead of '{target_dynamic_state_dir}'")
                    print(f"      This may be from a different generation with different parameters.")
                    print()
                break
    
    num_generated = len(generated_files)
    
    # Calculate progress
    progress_pct = (num_generated / expected_files) * 100 if expected_files > 0 else 0
    
    print("="*70)
    print("Constellation Generation Progress")
    print("="*70)
    print(f"Constellation: {constellation_name}")
    print(f"dynamic_state: dynamic_state_{time_step_ms}ms_for_{duration_s}s")
    print(f"Expected files: {expected_files}")
    print(f"Generated files: {num_generated}")
    print(f"Progress: {progress_pct:.1f}%")
    print(f"Remaining: {expected_files - num_generated} files")
    
    # Estimate time remaining: wall span from oldest→newest fstate (avg rate); not perfect if files complete out of order.
    if num_generated > 0:
        mtimes = [os.path.getmtime(f) for f in generated_files]
        t_first = min(mtimes)
        t_last = max(mtimes)
        span_s = max(t_last - t_first, 1e-3)
        rate = num_generated / span_s if span_s > 0 else 0.0
        remain_n = max(0, expected_files - num_generated)
        eta_s = (remain_n / rate) if rate > 0 else float("inf")
        wall_since_last = time.time() - t_last

        print("\nRough time estimate (from fstate mtimes; completion order may vary):")
        print("  Wall span (oldest→newest file): %.1f min" % (span_s / 60.0))
        print("  Avg rate: %.3f files/min" % (rate * 60.0))
        print("  Since newest file: %.1f min" % (wall_since_last / 60.0))
        if remain_n > 0 and rate > 0 and eta_s < 1e12:
            print("  Est. remaining (linear): %.1f min (~%d files left)" % (eta_s / 60.0, remain_n))
        if wall_since_last > 300 and remain_n > 0:
            print("  Note: No new fstate in 5+ min — heavy timestep, I/O stall, or check logs.")
    
    # Check if process is running
    print("\n" + "="*70)
    print("Process Status")
    print("="*70)
    import subprocess
    result = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True
    )
    lines = result.stdout.split('\n')
    python_processes = [l for l in lines if 'main_kuiper' in l and 'grep' not in l]
    
    if python_processes:
        print("Generation process is RUNNING:")
        for proc in python_processes:
            print(f"  {proc}")
    else:
        print("Generation process is NOT running (may have completed or crashed)")
    
    # Check for errors
    print("\n" + "="*70)
    print("Recent Files")
    print("="*70)
    if generated_files:
        # Show last 5 files
        sorted_files = sorted(generated_files, key=os.path.getmtime)
        print("Last 5 generated files:")
        for f in sorted_files[-5:]:
            mtime = os.path.getmtime(f)
            print(f"  {os.path.basename(f)} ({time.ctime(mtime)})")
    else:
        print("No files generated yet")

if __name__ == "__main__":
    constellation = sys.argv[1] if len(sys.argv) > 1 else "kuiper_630_meo"
    d_s = int(sys.argv[2]) if len(sys.argv) > 2 else None
    t_ms = int(sys.argv[3]) if len(sys.argv) > 3 else None
    check_progress(constellation, duration_s=d_s, time_step_ms=t_ms)


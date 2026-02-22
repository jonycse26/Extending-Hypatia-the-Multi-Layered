#!/usr/bin/env python3
"""
Check progress of constellation generation.

This script checks how many dynamic state files have been generated
and estimates remaining time.
"""

import os
import sys
import glob
import time

def check_progress(constellation_name="kuiper_630_meo", duration_s=5, time_step_ms=1000):
    """Check generation progress."""
    
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
    print(f"Expected files: {expected_files}")
    print(f"Generated files: {num_generated}")
    print(f"Progress: {progress_pct:.1f}%")
    print(f"Remaining: {expected_files - num_generated} files")
    
    # Estimate time remaining (rough estimate)
    if num_generated > 0:
        # Try to find the latest file timestamp
        latest_file = max(generated_files, key=os.path.getmtime)
        file_time = os.path.getmtime(latest_file)
        elapsed = time.time() - file_time
        
        # Very rough estimate: assume linear progress
        if progress_pct > 0:
            total_estimated_time = (time.time() - file_time) / (progress_pct / 100)
            remaining_time = total_estimated_time - (time.time() - file_time)
            print(f"\nRough time estimate:")
            print(f"  Elapsed: {elapsed/60:.1f} minutes")
            if remaining_time > 0:
                print(f"  Estimated remaining: {remaining_time/60:.1f} minutes")
                print(f"  Estimated total: {total_estimated_time/60:.1f} minutes")
    
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
    check_progress(constellation)


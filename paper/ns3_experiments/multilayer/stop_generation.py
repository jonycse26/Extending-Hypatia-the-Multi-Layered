#!/usr/bin/env python3
"""
Stop running constellation generation processes.

This script finds and stops all running main_kuiper_630_meo.py processes.
"""

import subprocess
import sys

def stop_generation():
    """Stop all running constellation generation processes."""
    
    print("=" * 70)
    print("Stopping Constellation Generation Processes")
    print("=" * 70)
    print()
    
    # Find all running main_kuiper processes
    result = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True
    )
    
    lines = result.stdout.split('\n')
    processes = []
    
    for line in lines:
        if 'main_kuiper' in line and 'grep' not in line and 'stop_generation' not in line:
            parts = line.split()
            if len(parts) >= 2:
                pid = parts[1]
                cmd = ' '.join(parts[10:])  # Command starts at index 10
                processes.append((pid, cmd))
    
    if not processes:
        print("No running generation processes found.")
        return 0
    
    print(f"Found {len(processes)} running process(es):")
    for pid, cmd in processes:
        print(f"  PID {pid}: {cmd[:80]}...")
    print()
    
    # Ask for confirmation
    response = input("Stop these processes? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Cancelled.")
        return 0
    
    # Stop processes
    stopped = 0
    for pid, cmd in processes:
        try:
            print(f"Stopping PID {pid}...")
            subprocess.run(["kill", pid], check=True)
            stopped += 1
        except subprocess.CalledProcessError as e:
            print(f"  Error stopping PID {pid}: {e}")
    
    print()
    print(f"Stopped {stopped} process(es).")
    
    # Wait a moment and verify
    import time
    time.sleep(2)
    
    # Check if processes are still running
    result = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True
    )
    
    remaining = [l for l in result.stdout.split('\n') 
                 if 'main_kuiper' in l and 'grep' not in l and 'stop_generation' not in l]
    
    if remaining:
        print("Warning: Some processes may still be running:")
        for line in remaining:
            print(f"  {line[:80]}...")
        print()
        print("You may need to use 'kill -9 <PID>' to force stop them.")
    else:
        print("All processes stopped successfully.")
    
    return 0

if __name__ == "__main__":
    sys.exit(stop_generation())


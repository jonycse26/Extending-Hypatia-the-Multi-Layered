#!/usr/bin/env python3
"""
Export a single CSV with both:
  - TCP log metrics from evaluation_utils.extract_metrics()
  - reconstructed path-based metrics (avg_hop_count, avg_path_stretch,
    path_stability_ratio, bottleneck_utilization, meo_usage_ratio)

It scans the standard pipeline run directories under `paper/ns3_experiments/multilayer/runs/`.
"""

import argparse
import glob
import os
import re
import sys

from evaluation_utils import export_results_csv, extract_metrics

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RUNS_DIR = os.path.join(SCRIPT_DIR, "runs")


def _parse_run_name(run_name):
    """
    Return a dict of scenario meta fields extracted from run_name.
    """
    # Experiment 1: multilayer vs leo_only (same pair IDs, different prefixes)
    m = re.match(r"^multilayer_(\d+)_to_(\d+)_tcp$", run_name)
    if m:
        return {
            "experiment": 1,
            "scenario_type": "multilayer",
            "from_id": int(m.group(1)),
            "to_id": int(m.group(2)),
        }

    m = re.match(r"^multilayer_(\d+)_to_(\d+)_pings$", run_name)
    if m:
        return {
            "experiment": 1,
            "scenario_type": "multilayer",
            "from_id": int(m.group(1)),
            "to_id": int(m.group(2)),
        }

    m = re.match(r"^leo_only_(\d+)_to_(\d+)_tcp$", run_name)
    if m:
        return {
            "experiment": 1,
            "scenario_type": "leo_only",
            "from_id": int(m.group(1)),
            "to_id": int(m.group(2)),
        }

    m = re.match(r"^leo_only_(\d+)_to_(\d+)_pings$", run_name)
    if m:
        return {
            "experiment": 1,
            "scenario_type": "leo_only",
            "from_id": int(m.group(1)),
            "to_id": int(m.group(2)),
        }

    # Experiment 2 in the step pipeline: threshold_test_* (pair-based scenarios)
    m = re.match(r"^threshold_test_(\d+)_to_(\d+)_tcp$", run_name)
    if m:
        return {
            "experiment": 2,
            "scenario_type": "threshold_test",
            "from_id": int(m.group(1)),
            "to_id": int(m.group(2)),
        }

    m = re.match(r"^threshold_test_(\d+)_to_(\d+)_pings$", run_name)
    if m:
        return {
            "experiment": 2,
            "scenario_type": "threshold_test",
            "from_id": int(m.group(1)),
            "to_id": int(m.group(2)),
        }

    # Experiment 3: example3_distance_{short,medium,long}_*.
    m = re.match(r"^example3_distance_(short|medium|long)_(\d+)_to_(\d+)_tcp$", run_name)
    if m:
        return {
            "experiment": 3,
            "scenario_type": "distance_tier",
            "distance_tier": m.group(1),
            "from_id": int(m.group(2)),
            "to_id": int(m.group(3)),
        }

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Export multilayer metrics table (TCP + reconstructed path metrics)."
    )
    parser.add_argument(
        "--out",
        default=os.path.join(SCRIPT_DIR, "multilayer_all_experiments_metrics.csv"),
        help="Output CSV path",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of runs (0 = no limit)",
    )
    args = parser.parse_args()

    if not os.path.isdir(RUNS_DIR):
        print("ERROR: runs dir not found: %s" % RUNS_DIR)
        return 1

    patterns = [
        os.path.join(RUNS_DIR, "multilayer_*_tcp"),
        os.path.join(RUNS_DIR, "leo_only_*_tcp"),
        os.path.join(RUNS_DIR, "threshold_test_*_tcp"),
        os.path.join(RUNS_DIR, "multilayer_*_pings"),
        os.path.join(RUNS_DIR, "leo_only_*_pings"),
        os.path.join(RUNS_DIR, "threshold_test_*_pings"),
        os.path.join(RUNS_DIR, "example3_distance_*_tcp"),
    ]

    run_dirs = []
    for pat in patterns:
        run_dirs.extend(sorted(glob.glob(pat)))

    # Deterministic ordering
    run_dirs = sorted(set(run_dirs))
    if args.limit and args.limit > 0:
        run_dirs = run_dirs[: args.limit]

    rows = []
    for rd in run_dirs:
        run_name = os.path.basename(rd)
        meta = _parse_run_name(run_name)
        if not meta:
            continue

        met = extract_metrics(rd)
        # Skip runs where logs are missing entirely
        if met.get("error"):
            # Keep row anyway if you want later debugging, but by default we skip.
            print("Skip %s: %s" % (run_name, met["error"]))
            continue

        row = {"run_name": run_name}
        row.update(meta)
        row.update(met)
        rows.append(row)

    if not rows:
        print("No runs found / no metrics extracted.")
        return 1

    export_results_csv(rows, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())


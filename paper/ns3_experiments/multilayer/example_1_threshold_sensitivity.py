#!/usr/bin/env python3
"""
Experiment: Threshold sensitivity (MEO routing — hop & distance thresholds)

Script file: example_1_threshold_sensitivity.py (name kept for imports; this is the
threshold-sweep experiment, not the LEO-vs-multilayer “comparison” example.)

Regenerates multilayer dynamic state (fstate) for each threshold setting, then
runs ns-3 TCP simulations for every pair in run_list.experiment1_pairs_multilayer
so you can compare routing and performance.

Default — hop threshold only (meo_threshold_distance_m = 10,000 km fixed):
  meo_threshold_hops ∈ {2, 3, 4, 5}

Optional — distance threshold (meo_threshold_hops = 3 fixed):
  meo_threshold_distance_m ∈ {8e6, 10e6, 12e6} m
  Enable with:  --distance-threshold-sweep

Usage (from paper/ns3_experiments/multilayer/):
  python3 example_1_threshold_sensitivity.py [--distance-threshold-sweep] [--skip-regenerate] [num_threads]

  --skip-regenerate     Do not rebuild fstate; only create runs & simulate (use existing dirs)
  num_threads           Threads for dynamic-state generation (default 4)

  --skip-ns3            Only prepare runs (and optionally regenerate fstate); does NOT run ns-3
                        and does NOT write a metrics CSV. Afterward, build the table with:
                          python3 example_1_threshold_sensitivity.py --export-csv-from-runs

After each ns-3 run, metrics are extracted and written to threshold_sensitivity_results.csv.
Use --split-sweep-csvs to also write threshold_sensitivity_hops.csv and
threshold_sensitivity_distance.csv (cleaner plots when both sweeps are enabled).

CSV log column assumptions (validate once on your machine, e.g.):
  head runs/<run_name>/logs_ns3/tcp_flow_0_progress.csv
  head runs/<run_name>/logs_ns3/tcp_flow_0_rtt.csv
  head runs/<run_name>/logs_ns3/tcp_flow_0_rate_in_intervals.csv   # optional; may be absent
Progress:  col0=flow_id, col1=time_ns, col2=bytes
RTT:       col0=flow_id, col1=time_ns, col2=rtt_ns
Rate file: col0=flow_id, col1=time_ns, col2=rate_Mbps (from post-process script if generated)

Use --export-csv-from-runs to rebuild CSV from existing runs/example1_threshold_* without re-simulating.

TCP flow plots: not generated inside this script; use ``step_3_generate_plots.py`` (does not include
``example1_threshold_*`` by default) or ``evaluation_utils.run_plot_tcp_flow("<run_name>")`` per run
after ``os.chdir`` to the multilayer directory.

Shared evaluation helpers (metrics, CSV, run_ns3): evaluation_utils.py

Distance sweep: md = 10e6 m at mh = 3 is already part of the hop sweep; the distance sweep
skips that duplicate point. When plotting combined data, avoid double-counting (mh=3, md=10M).

MEO ISL fields in CSV are utilization proxies — see evaluation_utils module docstring for thesis wording.
"""

import argparse
import glob
import math
import os
import re
import shutil
import sys

import exputil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SATELLITE_NETWORKS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '../../satellite_networks_state'))

sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.join(SATELLITE_NETWORKS_DIR, '..', '..', 'satgenpy'))

try:
    from run_list import *
except ImportError:
    print("Error: Could not import run_list. Run from the multilayer directory.")
    sys.exit(1)

try:
    from satgen.description import read_description
    import satgen
except ImportError:
    print("Error: Could not import satgen. Check satgenpy on PYTHONPATH.")
    sys.exit(1)

from evaluation_utils import export_results_csv, extract_metrics, pd, run_ns3

local_shell = exputil.LocalShell()

# Hop sensitivity: vary meo_threshold_hops; keep distance threshold at default (10,000 km)
MEO_THRESHOLD_DISTANCE_DEFAULT_M = 10_000_000.0
HOP_THRESHOLD_VALUES = [2, 3, 4, 5]

# Distance sensitivity: vary meo_threshold_distance_m; keep hop threshold at 3
MEO_THRESHOLD_HOPS_FOR_DISTANCE_SWEEP = 3
# Includes 10e6 for documentation; duplicate (mh=3, md=10M) is skipped vs hop sweep — see main loop
DISTANCE_THRESHOLD_VALUES_M = [8_000_000.0, 10_000_000.0, 12_000_000.0]


def threshold_dir_suffix(meo_threshold_hops, meo_threshold_distance_m):
    """Filesystem-safe subdirectory under constellation (appended to dynamic_state_*)."""
    return "_mh%d_md%d" % (meo_threshold_hops, int(meo_threshold_distance_m))


def regenerate_dynamic_state_for_thresholds(
        meo_threshold_hops,
        meo_threshold_distance_m,
        num_threads,
        skip_regenerate,
):
    """Build gen_data/<network>/dynamic_state_<ms>_for_<s><suffix>/ with given MEO thresholds."""
    output_generated_data_dir = os.path.join(SATELLITE_NETWORKS_DIR, 'gen_data')
    name = multilayer_satellite_network
    constellation_dir = os.path.join(output_generated_data_dir, name)
    description_path = os.path.join(constellation_dir, 'description.txt')

    if not os.path.isdir(constellation_dir):
        print("ERROR: Constellation not found: %s" % constellation_dir)
        return None

    description = read_description(description_path)
    max_gsl_length_m = description.get('max_gsl_length_m')
    max_isl_length_m = description.get('max_isl_length_m')
    if max_gsl_length_m is None or max_isl_length_m is None:
        print("ERROR: description.txt must contain max_gsl_length_m and max_isl_length_m")
        return None

    suffix = threshold_dir_suffix(meo_threshold_hops, meo_threshold_distance_m)
    dynamic_dir = os.path.join(
        constellation_dir,
        "dynamic_state_%dms_for_%ds%s"
        % (dynamic_state_update_interval_ms, simulation_end_time_s, suffix),
    )

    if skip_regenerate:
        if not os.path.isdir(dynamic_dir):
            print("ERROR: --skip-regenerate but directory missing: %s" % dynamic_dir)
            return None
        print("Skip regenerate; using existing: %s" % dynamic_dir)
        return suffix

    if os.path.isdir(dynamic_dir):
        print("Removing existing dynamic state: %s" % dynamic_dir)
        shutil.rmtree(dynamic_dir)

    print("Regenerating dynamic state: meo_threshold_hops=%d meo_threshold_distance_m=%.0f"
          % (meo_threshold_hops, meo_threshold_distance_m))
    print("  Output: .../%s" % os.path.basename(dynamic_dir))

    cwd = os.getcwd()
    try:
        os.chdir(SATELLITE_NETWORKS_DIR)
        satgen.help_dynamic_state(
            "gen_data",
            num_threads,
            name,
            dynamic_state_update_interval_ms,
            simulation_end_time_s,
            float(max_gsl_length_m),
            float(max_isl_length_m),
            "algorithm_free_one_multi_layer",
            True,
            dynamic_state_dir_suffix=suffix,
            meo_threshold_hops=meo_threshold_hops,
            meo_threshold_distance_m=float(meo_threshold_distance_m),
        )
    finally:
        os.chdir(cwd)

    return suffix


def create_ns3_run(dynamic_state_rel_suffix, from_id, to_id, scenario_tag):
    """
    dynamic_state_rel_suffix: e.g. '_mh3_md10000000' (appended to base dynamic_state dir name).
    scenario_tag: short label for run folder, e.g. 'mh3_md10M'
    """
    run_name = "example1_threshold_%s_%d_to_%d_tcp" % (scenario_tag, from_id, to_id)
    run_dir = "runs/" + run_name
    local_shell.remove_force_recursive(run_dir)
    local_shell.make_full_dir(run_dir)
    local_shell.make_full_dir(run_dir + "/logs_ns3")

    dynamic_state_for_ns3 = dynamic_state + dynamic_state_rel_suffix

    local_shell.copy_file("templates/template_tcp_a_b_config_ns3.properties",
                          run_dir + "/config_ns3.properties")
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                            "[SATELLITE-NETWORK]",
                                            multilayer_satellite_network)
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                            "[DYNAMIC-STATE]",
                                            dynamic_state_for_ns3)
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

    local_shell.copy_file("templates/template_tcp_a_b_schedule.csv",
                          run_dir + "/schedule.csv")
    local_shell.sed_replace_in_file_plain(run_dir + "/schedule.csv",
                                          "[FROM]",
                                          str(from_id))
    local_shell.sed_replace_in_file_plain(run_dir + "/schedule.csv",
                                          "[TO]",
                                          str(to_id))
    local_shell.perfect_exec("sed -i '/^$/d' " + run_dir + "/schedule.csv",
                             output_redirect=exputil.OutputRedirect.CONSOLE)

    return run_name, run_dir


def scenario_tag_from_thresholds(mh, md_m):
    """Short tag for run folder names."""
    md_m = int(md_m)
    if md_m % 1_000_000 == 0:
        md_short = "%dM" % (md_m // 1_000_000)
    else:
        md_short = str(md_m)
    return "mh%d_md%s" % (mh, md_short)


def _pair_desc_for_ids(from_id, to_id):
    for fid, tid, desc in experiment1_pairs_multilayer:
        if fid == from_id and tid == to_id:
            return desc
    return "%d_to_%d" % (from_id, to_id)


def infer_sweep_kind(mh, md_m):
    """
    Classify for CSV splitting when re-exporting from run names only.
    Distance-only points: mh=3 with md 8e6 or 12e6 (not the shared 10e6 baseline).
    Hop sweep: md = default 10e6 and mh in {2,3,4,5}. (mh=3, md=10e6) is hop-only.
    """
    if mh == MEO_THRESHOLD_HOPS_FOR_DISTANCE_SWEEP and md_m in (
        8_000_000.0,
        12_000_000.0,
    ):
        return "distance"
    if md_m == MEO_THRESHOLD_DISTANCE_DEFAULT_M and mh in HOP_THRESHOLD_VALUES:
        return "hop"
    return "unknown"


def parse_example1_run_name(run_name):
    """
    Parse example1_threshold_mh3_md10M_1196_to_1221_tcp → hops, distance_m, from, to.
    Returns None if pattern does not match.
    """
    m = re.match(
        r"^example1_threshold_mh(\d+)_md([^_]+)_(\d+)_to_(\d+)_tcp$",
        run_name,
    )
    if not m:
        return None
    mh = int(m.group(1))
    md_s = m.group(2)
    if md_s.endswith("M") and md_s[:-1].isdigit():
        md_m = float(md_s[:-1]) * 1e6
    else:
        try:
            md_m = float(md_s)
        except ValueError:
            return None
    from_id = int(m.group(3))
    to_id = int(m.group(4))
    return mh, md_m, from_id, to_id


def collect_metrics_from_existing_runs():
    """Scan runs/example1_threshold_*_tcp and build result rows (for re-export)."""
    pattern = os.path.join(SCRIPT_DIR, "runs", "example1_threshold_*_*_to_*_tcp")
    paths = sorted(glob.glob(pattern))
    rows = []
    for p in paths:
        run_name = os.path.basename(os.path.normpath(p))
        parsed = parse_example1_run_name(run_name)
        if not parsed:
            print("  Skip (name parse): %s" % run_name)
            continue
        mh, md_m, from_id, to_id = parsed
        pair_desc = _pair_desc_for_ids(from_id, to_id)
        met = extract_metrics(p)
        if met.get("error"):
            print("  Skip %s: %s" % (run_name, met["error"]))
            continue
        rows.append({
            "sweep_kind": infer_sweep_kind(mh, md_m),
            "meo_threshold_hops": mh,
            "meo_threshold_distance_m": md_m,
            "pair": pair_desc,
            "from_id": from_id,
            "to_id": to_id,
            "run_name": run_name,
            "avg_throughput_mbps": met["avg_throughput_mbps"],
            "avg_rtt_ms": met["avg_rtt_ms"],
            "completion_time_s": met["completion_time_s"],
            "transfer_complete": met["transfer_complete"],
            "bytes_transferred_final": met["bytes_transferred_final"],
            "meo_touching_isl_max_util": met["meo_touching_isl_max_util"],
            "meo_meo_isl_max_util": met["meo_meo_isl_max_util"],
            "meo_touching_isl_mean_util_nz": met["meo_touching_isl_mean_util_nz"],
            "meo_used_any": met["meo_used_any"],
            "avg_hop_count": met.get("avg_hop_count", float("nan")),
            "avg_path_stretch": met.get("avg_path_stretch", float("nan")),
            "path_stability_ratio": met.get("path_stability_ratio", float("nan")),
            "bottleneck_utilization": met.get("bottleneck_utilization", float("nan")),
            "meo_usage_ratio": met.get("meo_usage_ratio", float("nan")),
        })
    return rows


def append_result_row(results, sweep_kind, mh, md_m, pair_desc, from_id, to_id, run_name, metrics):
    results.append({
        "sweep_kind": sweep_kind,
        "meo_threshold_hops": mh,
        "meo_threshold_distance_m": md_m,
        "pair": pair_desc,
        "from_id": from_id,
        "to_id": to_id,
        "run_name": run_name,
        "avg_throughput_mbps": metrics["avg_throughput_mbps"],
        "avg_rtt_ms": metrics["avg_rtt_ms"],
        "completion_time_s": metrics["completion_time_s"],
        "transfer_complete": metrics["transfer_complete"],
        "bytes_transferred_final": metrics["bytes_transferred_final"],
        "meo_touching_isl_max_util": metrics["meo_touching_isl_max_util"],
        "meo_meo_isl_max_util": metrics["meo_meo_isl_max_util"],
        "meo_touching_isl_mean_util_nz": metrics["meo_touching_isl_mean_util_nz"],
        "meo_used_any": metrics["meo_used_any"],
        "avg_hop_count": metrics.get("avg_hop_count", float("nan")),
        "avg_path_stretch": metrics.get("avg_path_stretch", float("nan")),
        "path_stability_ratio": metrics.get("path_stability_ratio", float("nan")),
        "bottleneck_utilization": metrics.get("bottleneck_utilization", float("nan")),
        "meo_usage_ratio": metrics.get("meo_usage_ratio", float("nan")),
    })


def main():
    parser = argparse.ArgumentParser(
        description="Threshold sensitivity experiment — same GS pairs, vary MEO hop/distance thresholds.",
    )
    parser.add_argument(
        "--distance-threshold-sweep",
        action="store_true",
        help="Also sweep meo_threshold_distance_m (8e6,10e6,12e6 m) with mh=3; md=10e6 duplicates hop sweep and is skipped",
    )
    parser.add_argument(
        "--skip-regenerate",
        action="store_true",
        help="Skip fstate regeneration; expect dynamic_state_*_mh*_md* dirs to already exist",
    )
    parser.add_argument(
        "--skip-ns3",
        action="store_true",
        help="Only regenerate dynamic state / create run dirs; do not run ns-3",
    )
    parser.add_argument(
        "num_threads",
        nargs="?",
        type=int,
        default=4,
        help="Worker threads for dynamic state generation (default: 4)",
    )
    parser.add_argument(
        "--csv-out",
        default=os.path.join(SCRIPT_DIR, "threshold_sensitivity_results.csv"),
        help="Thesis table output path (default: threshold_sensitivity_results.csv in this dir)",
    )
    parser.add_argument(
        "--export-csv-from-runs",
        action="store_true",
        help="Only scan runs/example1_threshold_* and write CSV (no regenerate / ns-3)",
    )
    parser.add_argument(
        "--split-sweep-csvs",
        action="store_true",
        help="Also write threshold_sensitivity_hops.csv and threshold_sensitivity_distance.csv "
        "(hop vs distance rows by sweep_kind; combined file is still written)",
    )
    args = parser.parse_args()

    if args.export_csv_from_runs:
        if pd is None:
            print("Warning: pandas not installed; writing CSV with stdlib csv module.")
            print("  For DataFrame workflows: pip install pandas")
        rows = collect_metrics_from_existing_runs()
        export_results_csv(rows, args.csv_out)
        if rows and args.split_sweep_csvs:
            hop_rows = [r for r in rows if r.get("sweep_kind") == "hop"]
            dist_rows = [r for r in rows if r.get("sweep_kind") == "distance"]
            export_results_csv(hop_rows, os.path.join(SCRIPT_DIR, "threshold_sensitivity_hops.csv"))
            export_results_csv(dist_rows, os.path.join(SCRIPT_DIR, "threshold_sensitivity_distance.csv"))
        return 0 if rows else 1

    scenarios = []
    # Primary: hop threshold sensitivity (tag sweep_kind=hops for CSV split)
    for mh in HOP_THRESHOLD_VALUES:
        scenarios.append((
            mh,
            MEO_THRESHOLD_DISTANCE_DEFAULT_M,
            "hop sweep (d=%.0f km)" % (MEO_THRESHOLD_DISTANCE_DEFAULT_M / 1000.0),
            "hop",
        ))
    if args.distance_threshold_sweep:
        for md_m in DISTANCE_THRESHOLD_VALUES_M:
            if md_m == MEO_THRESHOLD_DISTANCE_DEFAULT_M:
                # Duplicate of hop sweep (mh=3, md=10 Mm); skip to avoid duplicate runs/plots
                continue
            scenarios.append((
                MEO_THRESHOLD_HOPS_FOR_DISTANCE_SWEEP,
                md_m,
                "distance sweep (hops=%d)" % MEO_THRESHOLD_HOPS_FOR_DISTANCE_SWEEP,
                "distance",
            ))

    if args.skip_ns3:
        print("NOTE: --skip-ns3 — only preparing run directories (and optional fstate).")
        print("      No ns-3 runs → no metrics in memory. To build the thesis CSV after")
        print("      you simulate (or if logs already exist), run:")
        print("      python3 example_1_threshold_sensitivity.py --export-csv-from-runs")
        print()

    print("=" * 70)
    print("Experiment: Threshold sensitivity (MEO routing thresholds)")
    print("=" * 70)
    print()
    print("GS pairs (experiment1_pairs_multilayer):")
    for from_id, to_id, desc in experiment1_pairs_multilayer:
        print("  - %s (%d → %d)" % (desc, from_id, to_id))
    print()
    print("Scenarios (%d):" % len(scenarios))
    for mh, md_m, note, sk in scenarios:
        print("  - [%s] meo_threshold_hops=%d  meo_threshold_distance_m=%.0f m  (%s)"
              % (sk, mh, md_m, note))
    print()

    os.chdir(SCRIPT_DIR)

    results = []

    for mh, md_m, note, sweep_kind in scenarios:
        print("-" * 70)
        print("[%s] Thresholds: hops=%d  distance_m=%.0f  (%s)" % (sweep_kind, mh, md_m, note))
        print("-" * 70)

        suffix = regenerate_dynamic_state_for_thresholds(
            mh, md_m, args.num_threads, args.skip_regenerate,
        )
        if suffix is None:
            return 1

        tag = scenario_tag_from_thresholds(mh, md_m)

        for from_id, to_id, pair_desc in experiment1_pairs_multilayer:
            print()
            print("  Pair: %s  |  run tag: %s" % (pair_desc, tag))
            run_name, run_dir = create_ns3_run(suffix, from_id, to_id, tag)
            print("  Created: runs/%s" % run_name)
            print("  satellite_network_routes_dir → .../%s%s" % (dynamic_state, suffix))

            if args.skip_ns3:
                continue

            print("  Running ns-3...")
            try:
                run_ns3(run_dir)
            except Exception as e:
                print("  ERROR: ns-3 failed: %s" % e)
                return 1

            metrics = extract_metrics(run_dir)
            if metrics.get("error"):
                print("  WARNING: metrics: %s" % metrics["error"])
            else:
                print("  Metrics: avg_throughput=%.4f Mbps  avg_rtt=%.3f ms  completion=%s  transfer_complete=%s"
                      % (
                          metrics["avg_throughput_mbps"]
                          if not math.isnan(metrics["avg_throughput_mbps"])
                          else float("nan"),
                          metrics["avg_rtt_ms"]
                          if not math.isnan(metrics["avg_rtt_ms"])
                          else float("nan"),
                          ("%.4f s" % metrics["completion_time_s"])
                          if not math.isnan(metrics["completion_time_s"])
                          else "nan",
                          metrics["transfer_complete"],
                      ))
                print("  MEO ISL (proxy): meo_touching_max_util=%.6f  meo_used_any=%s"
                      % (
                          metrics["meo_touching_isl_max_util"]
                          if not math.isnan(metrics["meo_touching_isl_max_util"])
                          else float("nan"),
                          metrics["meo_used_any"],
                      ))
            append_result_row(
                results, sweep_kind, mh, md_m, pair_desc, from_id, to_id, run_name, metrics,
            )

    print()
    print("=" * 70)
    print("Done. Compare results across runs under runs/example1_threshold_*")
    print("  - Forwarding differs per dynamic_state_*_mh*_md* → check fstate / console routing")
    print("  - TCP logs: runs/<run_name>/logs_ns3/")
    if results:
        if pd is None:
            print("  - Note: install pandas for DataFrame export: pip install pandas")
        export_results_csv(results, args.csv_out)
        print("  - Thesis plots: threshold vs avg_throughput_mbps, avg_rtt_ms, completion_time_s, MEO ISL util")
        if args.split_sweep_csvs:
            hop_rows = [r for r in results if r.get("sweep_kind") == "hop"]
            dist_rows = [r for r in results if r.get("sweep_kind") == "distance"]
            hop_path = os.path.join(SCRIPT_DIR, "threshold_sensitivity_hops.csv")
            dist_path = os.path.join(SCRIPT_DIR, "threshold_sensitivity_distance.csv")
            export_results_csv(hop_rows, hop_path)
            export_results_csv(dist_rows, dist_path)
    elif args.skip_ns3:
        print("No metrics CSV written (--skip-ns3). Use --export-csv-from-runs after simulations.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())

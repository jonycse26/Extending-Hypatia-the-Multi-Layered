#!/usr/bin/env python3
"""
Example 3: Distance-based scenario analysis

What this experiment highlights
-------------------------------
How end-to-end TCP performance and MEO usage differ across **three geographic distance
tiers** on the same multilayer constellation, using the **default** forwarding state
(``dynamic_state_500ms_for_50s`` from step_0 — no ``meo_threshold_distance_m`` sweep).

Pairs (multilayer node IDs, README-aligned):
  • **Short** (~2,800 km): Manila → Dalian
  • **Medium** (~4,500 km): Istanbul → Nairobi
  • **Long** (~11,000 km): Rio de Janeiro → St. Petersburg

Run folder names encode the tier: ``example3_distance_short_1209_to_1277_tcp``, etc.

Traffic: 10 Mbps TCP per flow (same as other multilayer examples).

Expected qualitative results (interpretation)
----------------------------------------------
Compare multi-layer vs LEO-only using ``example_2_comparison.py`` / experiment 1 runs.

**Short (Manila–Dalian)**
  • LEO-only often efficient; multilayer ≈ same or slightly worse; MEO rarely helps.

**Medium (Istanbul–Nairobi)**
  • Transitional — mixed outcomes depending on topology epoch and load.

**Long (Rio–St. Petersburg)**
  • Multilayer often clearly better when MEO backhaul is used; higher MEO utilization proxies.

Outputs
-------
  • Run directories: ``runs/example3_distance_{short,medium,long}_<from>_to_<to>_tcp``
  • Summary CSV: ``example_3_distance_scenario_results.csv`` (default path)

Re-export metrics without re-simulating::

  python3 example_3_distance_based_scenario_analysis.py --export-csv-from-runs

Per-run TCP plots: after each successful ns-3 run this script calls ``evaluation_utils.run_plot_tcp_flow``
(same gnuplot invocation as ``step_3_generate_plots.py``). Use ``--skip-plots`` to disable.
With ``--export-csv-from-runs --with-plots``, regenerate figures from existing logs.

Shared helpers: ``evaluation_utils.py`` (same as step 3 / example flows).
"""

import argparse
import glob
import math
import os
import re
import sys

import exputil

_SCRIPT = "example_3_distance_based_scenario_analysis.py"
_MULTILAYER_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, _MULTILAYER_DIR)

try:
    from run_list import (
        dynamic_state,
        dynamic_state_update_interval_ns,
        experiment3_distance_tiers,
        experiment3_pairs_multilayer,
        isl_utilization_tracking_interval_ns,
        multilayer_satellite_network,
        simulation_end_time_ns,
    )
except ImportError:
    print("Error: Could not import run_list. Run from the multilayer directory.")
    sys.exit(1)

try:
    from evaluation_utils import export_results_csv, extract_metrics, run_ns3, run_plot_tcp_flow
except ImportError as e:
    print("Error: need evaluation_utils.py in this directory (%s)" % e)
    sys.exit(1)

local_shell = exputil.LocalShell()


def create_ns3_run(from_id, to_id, tier_slug):
    """Run folder example3_distance_short_1209_to_1277_tcp."""
    run_name = "example3_distance_%s_%d_to_%d_tcp" % (tier_slug, from_id, to_id)
    run_dir = "runs/" + run_name
    local_shell.remove_force_recursive(run_dir)
    local_shell.make_full_dir(run_dir)
    local_shell.make_full_dir(run_dir + "/logs_ns3")

    local_shell.copy_file(
        "templates/template_tcp_a_b_config_ns3.properties",
        run_dir + "/config_ns3.properties",
    )
    local_shell.sed_replace_in_file_plain(
        run_dir + "/config_ns3.properties", "[SATELLITE-NETWORK]", multilayer_satellite_network
    )
    local_shell.sed_replace_in_file_plain(
        run_dir + "/config_ns3.properties", "[DYNAMIC-STATE]", dynamic_state
    )
    local_shell.sed_replace_in_file_plain(
        run_dir + "/config_ns3.properties",
        "[DYNAMIC-STATE-UPDATE-INTERVAL-NS]",
        str(dynamic_state_update_interval_ns),
    )
    local_shell.sed_replace_in_file_plain(
        run_dir + "/config_ns3.properties",
        "[SIMULATION-END-TIME-NS]",
        str(simulation_end_time_ns),
    )
    local_shell.sed_replace_in_file_plain(
        run_dir + "/config_ns3.properties", "[ISL-DATA-RATE-MEGABIT-PER-S]", "10.0"
    )
    local_shell.sed_replace_in_file_plain(
        run_dir + "/config_ns3.properties", "[GSL-DATA-RATE-MEGABIT-PER-S]", "10.0"
    )
    local_shell.sed_replace_in_file_plain(
        run_dir + "/config_ns3.properties", "[ISL-MAX-QUEUE-SIZE-PKTS]", "100"
    )
    local_shell.sed_replace_in_file_plain(
        run_dir + "/config_ns3.properties", "[GSL-MAX-QUEUE-SIZE-PKTS]", "100"
    )
    local_shell.sed_replace_in_file_plain(
        run_dir + "/config_ns3.properties", "[ENABLE-ISL-UTILIZATION-TRACKING]", "true"
    )
    local_shell.sed_replace_in_file_plain(
        run_dir + "/config_ns3.properties",
        "[ISL-UTILIZATION-TRACKING-INTERVAL-NS-COMPLETE]",
        "isl_utilization_tracking_interval_ns=" + str(isl_utilization_tracking_interval_ns),
    )
    local_shell.sed_replace_in_file_plain(
        run_dir + "/config_ns3.properties", "[TCP-SOCKET-TYPE]", "TcpNewReno"
    )

    local_shell.copy_file("templates/template_tcp_a_b_schedule.csv", run_dir + "/schedule.csv")
    local_shell.sed_replace_in_file_plain(run_dir + "/schedule.csv", "[FROM]", str(from_id))
    local_shell.sed_replace_in_file_plain(run_dir + "/schedule.csv", "[TO]", str(to_id))
    local_shell.perfect_exec(
        "sed -i '/^$/d' " + run_dir + "/schedule.csv",
        output_redirect=exputil.OutputRedirect.CONSOLE,
    )

    return run_name, run_dir


def _pair_desc_for_ids(from_id, to_id):
    for fid, tid, desc in experiment3_pairs_multilayer:
        if fid == from_id and tid == to_id:
            return desc
    return "%d_to_%d" % (from_id, to_id)


def parse_example3_run_name(run_name):
    """
    New: example3_distance_short_1209_to_1277_tcp → (tier, from_id, to_id)
    Legacy: example3_distance_mh3_md10M_1196_to_1221_tcp → (None, from_id, to_id) + md in dict
    Returns dict with keys: tier (str|None), from_id, to_id, legacy_mh, legacy_md_m
    """
    m = re.match(
        r"^example3_distance_(short|medium|long)_(\d+)_to_(\d+)_tcp$",
        run_name,
    )
    if m:
        return {
            "tier": m.group(1),
            "from_id": int(m.group(2)),
            "to_id": int(m.group(3)),
            "legacy_mh": None,
            "legacy_md_m": None,
        }
    m = re.match(
        r"^example3_distance_mh(\d+)_md([^_]+)_(\d+)_to_(\d+)_tcp$",
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
    return {
        "tier": None,
        "from_id": int(m.group(3)),
        "to_id": int(m.group(4)),
        "legacy_mh": mh,
        "legacy_md_m": md_m,
    }


def collect_metrics_from_existing_runs():
    pattern = os.path.join(_MULTILAYER_DIR, "runs", "example3_distance_*_tcp")
    paths = sorted(glob.glob(pattern))
    rows = []
    for p in paths:
        run_name = os.path.basename(os.path.normpath(p))
        parsed = parse_example3_run_name(run_name)
        if not parsed:
            print("  Skip (name parse): %s" % run_name)
            continue
        from_id = parsed["from_id"]
        to_id = parsed["to_id"]
        pair_desc = _pair_desc_for_ids(from_id, to_id)
        met = extract_metrics(p)
        if met.get("error"):
            print("  Skip %s: %s" % (run_name, met["error"]))
            continue
        row = {
            "distance_tier": parsed["tier"] or "legacy_md_sweep",
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
        }
        if parsed["legacy_mh"] is not None:
            row["legacy_meo_threshold_hops"] = parsed["legacy_mh"]
            row["legacy_meo_threshold_distance_m"] = parsed["legacy_md_m"]
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Example 3: Distance-based scenario analysis (short / medium / long GS pairs, default fstate)",
    )
    parser.add_argument(
        "--skip-ns3",
        action="store_true",
        help="Only create run directories; do not run ns-3",
    )
    parser.add_argument(
        "--skip-plots",
        action="store_true",
        help="Do not run plot_tcp_flow (gnuplot) after each simulation",
    )
    parser.add_argument(
        "--with-plots",
        action="store_true",
        help="With --export-csv-from-runs: also run plot_tcp_flow for each run in the CSV",
    )
    parser.add_argument(
        "--csv-out",
        default=os.path.join(_MULTILAYER_DIR, "example_3_distance_scenario_results.csv"),
        help="Thesis table CSV path",
    )
    parser.add_argument(
        "--export-csv-from-runs",
        action="store_true",
        help="Scan runs/example3_distance_* and write CSV only",
    )
    args = parser.parse_args()

    os.chdir(_MULTILAYER_DIR)

    if args.export_csv_from_runs:
        rows = collect_metrics_from_existing_runs()
        export_results_csv(rows, args.csv_out)
        if args.with_plots and rows:
            print("Generating TCP flow plots (--with-plots)...")
            for r in rows:
                run_plot_tcp_flow(r["run_name"], multilayer_dir=_MULTILAYER_DIR)
        return 0 if rows else 1

    if args.skip_ns3:
        print("NOTE: --skip-ns3 — preparing run dirs only. After simulations:")
        print("  python3 %s --export-csv-from-runs" % _SCRIPT)
        print()

    print("=" * 70)
    print("Example 3: Distance-based scenario analysis")
    print("=" * 70)
    print()
    print("Routing: default multilayer dynamic state (%s)" % dynamic_state)
    print()
    for tier, (from_id, to_id, desc) in zip(experiment3_distance_tiers, experiment3_pairs_multilayer):
        print("  [%s] %s (%d → %d)" % (tier, desc, from_id, to_id))
    print()

    results = []

    for tier, (from_id, to_id, pair_desc) in zip(
        experiment3_distance_tiers, experiment3_pairs_multilayer
    ):
        print("-" * 70)
        print("Tier: %s  |  %s" % (tier, pair_desc))
        print("-" * 70)
        run_name, run_dir = create_ns3_run(from_id, to_id, tier)
        print("  Created: runs/%s" % run_name)

        metrics = {
            "avg_throughput_mbps": float("nan"),
            "avg_rtt_ms": float("nan"),
            "completion_time_s": float("nan"),
            "transfer_complete": False,
            "bytes_transferred_final": float("nan"),
            "meo_touching_isl_max_util": float("nan"),
            "meo_meo_isl_max_util": float("nan"),
            "meo_touching_isl_mean_util_nz": float("nan"),
            "meo_used_any": False,
            "error": "skip",
        }

        if not args.skip_ns3:
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
                print(
                    "  Metrics: avg_throughput=%.4f Mbps  avg_rtt=%.3f ms  completion=%s  transfer_complete=%s"
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
                    )
                )
            if not args.skip_plots:
                print("  plot_tcp_flow → pdf/%s/ ..." % run_name)
                run_plot_tcp_flow(run_name, multilayer_dir=_MULTILAYER_DIR)

        results.append({
            "distance_tier": tier,
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
        print()

    print("=" * 70)
    print("Done. Runs under runs/example3_distance_*")
    if results and not args.skip_ns3:
        export_results_csv(results, args.csv_out)
        if not args.skip_plots:
            print("TCP flow plots under pdf/example3_distance_*_tcp/ (same toolchain as step_3).")
        print("Thesis tables: facet by distance_tier (short / medium / long) vs throughput, RTT, MEO util.")
    elif args.skip_ns3:
        print("No metrics CSV (--skip-ns3). Use --export-csv-from-runs after simulations.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())

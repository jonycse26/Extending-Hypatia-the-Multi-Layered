#!/usr/bin/env python3
"""
Example 2: Multi-Layer vs LEO-Only Performance Comparison

This example compares the performance of multi-layer (LEO + MEO) vs LEO-only
constellations for the same three city pairs as run_list.experiment1_pairs_*:
Mumbai–Lima, Lima–Karachi, Tokyo–Buenos-Aires.

It demonstrates:
- Reduced latency for long-distance pairs via MEO backhaul (where applicable)
- Lower LEO ISL utilization (traffic offloaded to MEO)
- Path efficiency differences between multi-layer and LEO-only

Note: step_1_generate_runs.py creates the same experiment-1 TCP + ping runs but wipes runs/,
pdf/, and data/. For a missing Figure A pair, prefer::

  python3 example_2_comparison.py --only-pair-indices <i> --with-pings --run-ns3

(Indices: 0 Mumbai–Lima, 1 Lima–Karachi, 2 Tokyo–Buenos-Aires.) main() chdirs here so
templates/ resolve.
"""

import exputil
import argparse
import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Add parent directory to path for imports
sys.path.insert(0, _SCRIPT_DIR)

try:
    from run_list import *
except ImportError:
    print("Error: Could not import run_list. Make sure you're running from the multilayer directory.")
    sys.exit(1)

local_shell = exputil.LocalShell()

try:
    from evaluation_utils import (
        extract_metrics,
        export_results_csv,
        run_ns3,
        run_plot_ping,
        run_plot_tcp_flow,
    )
except ImportError:
    extract_metrics = None
    export_results_csv = None
    run_ns3 = None
    run_plot_ping = None
    run_plot_tcp_flow = None

# Same three pairs as run_list.experiment1_pairs_leo / experiment1_pairs_multilayer
COMPARISON_PAIRS = [
    {
        "from_id_leo": f_leo,
        "to_id_leo": t_leo,
        "from_id_multilayer": f_ml,
        "to_id_multilayer": t_ml,
        "description": desc,
    }
    for (f_leo, t_leo, desc), (f_ml, t_ml, _) in zip(
        experiment1_pairs_leo, experiment1_pairs_multilayer
    )
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
    local_shell.make_full_dir(run_dir + "/logs_ns3")
    
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


def create_ping_run_config(pair, is_multilayer):
    """
    Ping run directory for one comparison pair (experiment-1 style; matches step_1 ping runs).
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

    run_name = "%s_%d_to_%d_pings" % (prefix, from_id, to_id)
    run_dir = "runs/" + run_name
    local_shell.remove_force_recursive(run_dir)
    local_shell.make_full_dir(run_dir)

    local_shell.copy_file(
        "templates/template_pings_a_b_config_ns3.properties",
        run_dir + "/config_ns3.properties",
    )
    local_shell.sed_replace_in_file_plain(
        run_dir + "/config_ns3.properties", "[SATELLITE-NETWORK]", satellite_network
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
        run_dir + "/config_ns3.properties", "[ISL-DATA-RATE-MEGABIT-PER-S]", "10000.0"
    )
    local_shell.sed_replace_in_file_plain(
        run_dir + "/config_ns3.properties", "[GSL-DATA-RATE-MEGABIT-PER-S]", "10000.0"
    )
    local_shell.sed_replace_in_file_plain(
        run_dir + "/config_ns3.properties", "[ISL-MAX-QUEUE-SIZE-PKTS]", "100000"
    )
    local_shell.sed_replace_in_file_plain(
        run_dir + "/config_ns3.properties", "[GSL-MAX-QUEUE-SIZE-PKTS]", "100000"
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
        run_dir + "/config_ns3.properties",
        "[PINGMESH-INTERVAL-NS]",
        str(pingmesh_interval_ns),
    )
    local_shell.sed_replace_in_file_plain(
        run_dir + "/config_ns3.properties", "[FROM]", str(from_id)
    )
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties", "[TO]", str(to_id))

    return run_name, run_dir


def main():
    """
    Generate run configurations for multi-layer vs LEO-only comparison.

    By default this script only prepares runs. It can also:
      - run ns-3 (optional)
      - generate TCP pdf/data plots (optional)
      - generate D–G bar charts (optional, requires evaluation_utils)
    """

    parser = argparse.ArgumentParser(description="Example 2: Multilayer vs LEO-only comparison")
    parser.add_argument(
        "--run-ns3",
        action="store_true",
        help="Run ns-3 simulations for the created runs (can be slow).",
    )
    parser.add_argument(
        "--skip-plots",
        action="store_true",
        help="Skip plot_tcp_flow (no pdf/data time-series plots).",
    )
    parser.add_argument(
        "--skip-bar-metrics",
        action="store_true",
        help="Skip hop/stretch/stability/bottleneck/completion bar charts.",
    )
    parser.add_argument(
        "--bar-metrics-out",
        default=os.path.join(_SCRIPT_DIR, "example_2_comparison_bar_metrics"),
        help="Output directory for bar plots (default: example_2_comparison_bar_metrics/).",
    )
    parser.add_argument(
        "--metrics-csv-out",
        default=os.path.join(_SCRIPT_DIR, "example_2_comparison_metrics.csv"),
        help="CSV output path for extracted metrics (default: example_2_comparison_metrics.csv).",
    )
    parser.add_argument(
        "--only-pair-indices",
        type=str,
        default=None,
        help=(
            "Comma-separated 0-based indices of COMPARISON_PAIRS to materialize "
            "(e.g. '1' = Lima–Karachi only). Default: all three pairs."
        ),
    )
    parser.add_argument(
        "--with-pings",
        action="store_true",
        help=(
            "Also create experiment-1 ping runs (multilayer + LEO) for each selected pair; "
            "with --run-ns3 simulate them; with default plots run plot_ping into data/."
        ),
    )
    args = parser.parse_args()

    os.chdir(_SCRIPT_DIR)

    pairs_to_run = COMPARISON_PAIRS
    if args.only_pair_indices is not None and str(args.only_pair_indices).strip() != "":
        idxs = []
        for part in str(args.only_pair_indices).split(","):
            part = part.strip()
            if not part:
                continue
            idxs.append(int(part))
        for i in idxs:
            if i < 0 or i >= len(COMPARISON_PAIRS):
                print("ERROR: pair index %d out of range [0, %d)" % (i, len(COMPARISON_PAIRS)))
                return 1
        pairs_to_run = [COMPARISON_PAIRS[i] for i in idxs]

    print("=" * 70)
    print("Example 2: Multi-Layer vs LEO-Only Performance Comparison")
    print("=" * 70)
    print()
    print("This example compares multi-layer (LEO + MEO) vs LEO-only constellations.")
    print()
    print("Test pairs (this run):")
    for j, pair in enumerate(pairs_to_run, 1):
        print("  %d. %s" % (j, pair["description"]))
    print()

    runs_created = []  # (pair_desc, label, run_name, run_dir)

    for pair in pairs_to_run:
        print("Creating configurations for: %s" % pair["description"])

        # Multi-layer configuration
        run_name_ml, run_dir_ml = create_run_config(pair, is_multilayer=True)
        runs_created.append((pair["description"], "multilayer", run_name_ml, run_dir_ml))
        print("  ✓ Multi-layer: %s" % run_name_ml)

        # LEO-only configuration
        run_name_leo, run_dir_leo = create_run_config(pair, is_multilayer=False)
        runs_created.append((pair["description"], "leo_only", run_name_leo, run_dir_leo))
        print("  ✓ LEO-only: %s" % run_name_leo)

        if args.with_pings:
            pr_ml, pr_d_ml = create_ping_run_config(pair, is_multilayer=True)
            runs_created.append((pair["description"], "multilayer_pings", pr_ml, pr_d_ml))
            print("  ✓ Multi-layer pings: %s" % pr_ml)
            pr_leo, pr_d_leo = create_ping_run_config(pair, is_multilayer=False)
            runs_created.append((pair["description"], "leo_only_pings", pr_leo, pr_d_leo))
            print("  ✓ LEO-only pings: %s" % pr_leo)
        print()

    print("=" * 70)
    print("Configuration Summary")
    print("=" * 70)
    print()
    print("Created %d run configurations:" % len(runs_created))
    for pair_desc, label, run_name, _run_dir in runs_created:
        print("  - %s (%s, %s)" % (run_name, label, pair_desc))
    print()

    if args.run_ns3:
        if run_ns3 is None:
            raise RuntimeError("evaluation_utils not importable; cannot run ns-3")
        for _pair_desc, _label, _run_name, run_dir in runs_created:
            print("Running ns-3: %s ..." % _run_name)
            run_ns3(run_dir)

    if not args.skip_plots:
        if run_plot_tcp_flow is None or (args.with_pings and run_plot_ping is None):
            raise RuntimeError("evaluation_utils not importable; cannot create plots")
        for _pair_desc, _label, run_name, _run_dir in runs_created:
            if run_name.endswith("_tcp"):
                run_plot_tcp_flow(run_name, multilayer_dir=_SCRIPT_DIR)
            elif run_name.endswith("_pings"):
                run_plot_ping(run_name, multilayer_dir=_SCRIPT_DIR)
            else:
                print("WARNING: unknown run type, skip plot: %s" % run_name)

    if not args.skip_bar_metrics:
        if extract_metrics is None or export_results_csv is None:
            raise RuntimeError("evaluation_utils not importable; cannot extract metrics")

        # Build pair order and mapping (subset when --only-pair-indices is used)
        pair_order = [p["description"] for p in pairs_to_run]
        by_pair = {}
        for pair_desc, label, run_name, run_dir in runs_created:
            by_pair.setdefault(pair_desc, {})[label] = (run_name, run_dir)

        metrics_rows = []
        for pair_desc in pair_order:
            ml = by_pair.get(pair_desc, {}).get("multilayer")
            leo = by_pair.get(pair_desc, {}).get("leo_only")
            if not ml or not leo:
                continue
            ml_name, ml_dir = ml
            leo_name, leo_dir = leo

            ml_met = extract_metrics(ml_dir)
            leo_met = extract_metrics(leo_dir)
            if ml_met.get("error") or leo_met.get("error"):
                continue

            for label, run_name, met in [
                ("multilayer", ml_name, ml_met),
                ("leo_only", leo_name, leo_met),
            ]:
                metrics_rows.append(
                    {
                        "pair": pair_desc,
                        "label": label,
                        "run_name": run_name,
                        "completion_time_s": met.get("completion_time_s", float("nan")),
                        "rtt_variation_ms": met.get("rtt_variation_ms", float("nan")),
                        "rtt_variation_ratio": met.get("rtt_variation_ratio", float("nan")),
                        "geodesic_rtt_ms": met.get("geodesic_rtt_ms", float("nan")),
                        "rtt_stretch": met.get("rtt_stretch", float("nan")),
                        "avg_hop_count": met.get("avg_hop_count", float("nan")),
                        "avg_path_stretch": met.get("avg_path_stretch", float("nan")),
                        "path_stability_ratio": met.get("path_stability_ratio", float("nan")),
                        "path_change_count": met.get("path_change_count", float("nan")),
                        "hop_count_variation": met.get("hop_count_variation", float("nan")),
                        "hop_count_ratio": met.get("hop_count_ratio", float("nan")),
                        "bottleneck_utilization": met.get("bottleneck_utilization", float("nan")),
                        "meo_usage_ratio": met.get("meo_usage_ratio", float("nan")),
                        "out_of_order_rate": met.get("out_of_order_rate", float("nan")),
                    }
                )

        if metrics_rows:
            export_results_csv(metrics_rows, args.metrics_csv_out)

        # Plot grouped bars (D–G + completion)
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import numpy as np
        except Exception:
            print("WARNING: matplotlib unavailable; skipping bar charts.")
            plt = None

        if metrics_rows and plt is not None:
            def _get(pair_desc, label, key):
                for r in metrics_rows:
                    if r["pair"] == pair_desc and r["label"] == label:
                        return r.get(key, float("nan"))
                return float("nan")

            x = np.arange(len(pair_order))
            w = 0.4
            fig, axes = plt.subplots(1, 5, figsize=(20, 4.5))
            keys = [
                ("completion_time_s", "Completion time (s)"),
                ("avg_hop_count", "Hop count"),
                ("avg_path_stretch", "Path stretch"),
                ("path_stability_ratio", "Path stability ratio"),
                ("bottleneck_utilization", "Bottleneck utilization"),
            ]
            for i, (k, title) in enumerate(keys):
                axes[i].bar(
                    x - w / 2,
                    [_get(p, "leo_only", k) for p in pair_order],
                    width=w,
                    label="LEO-only",
                )
                axes[i].bar(
                    x + w / 2,
                    [_get(p, "multilayer", k) for p in pair_order],
                    width=w,
                    label="Multilayer",
                )
                axes[i].set_title(title)
                axes[i].set_xticks(x)
                axes[i].set_xticklabels(pair_order, rotation=25, ha="right")
                axes[i].grid(True, axis="y", alpha=0.3)
            axes[0].legend()
            os.makedirs(args.bar_metrics_out, exist_ok=True)
            out_png = os.path.join(args.bar_metrics_out, "example2_bar_metrics.png")
            out_pdf = os.path.join(args.bar_metrics_out, "example2_bar_metrics.pdf")
            fig.tight_layout()
            fig.savefig(out_png)
            fig.savefig(out_pdf)
            print("Wrote bar plots: %s" % out_pdf)

    return 0

if __name__ == "__main__":
    exit(main())


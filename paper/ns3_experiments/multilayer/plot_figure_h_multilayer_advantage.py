#!/usr/bin/env python3
"""
Figure H — Multilayer vs LEO-only scorecard

Goal:
  Provide a clear, thesis-friendly comparison to justify multilayer benefits
  against LEO-only for Kuiper experiment-1 pairs.

Panels (2x2):
  (a) Avg hop count (lower is better)
  (b) Bottleneck utilization (lower is better)
  (c) RTT stretch max/geodesic (lower is better)
  (d) Path stability ratio (higher is better)

Data source: ``multilayer_all_experiments_metrics.csv`` (per-run scalars). ``--duration-s`` /
``--time-step-ms`` annotate the figure for the intended simulation setup (default: ``run_list``:
25 s, 1000 ms → ``dynamic_state_1000ms_for_25s``). Re-export metrics after matching ns-3 runs.
"""

import argparse
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(SCRIPT_DIR, "figure-h multilayer advantage")
DEFAULT_METRICS = os.path.join(SCRIPT_DIR, "multilayer_all_experiments_metrics.csv")
sys.path.insert(0, SCRIPT_DIR)

try:
    from run_list import (
        dynamic_state_update_interval_ms,
        experiment1_pairs_leo,
        experiment1_pairs_multilayer,
        simulation_end_time_s,
    )
except Exception as e:
    raise RuntimeError("Could not import run_list experiment1 pairs / timing defaults: %s" % e)


def _expected_fstate_file_count(duration_s, time_step_ms):
    if duration_s < 0 or time_step_ms <= 0:
        return 0
    return (duration_s * 1000) // time_step_ms + 1


def _to_float(v):
    try:
        return float(v)
    except Exception:
        return float("nan")


def _load_rows(csv_path):
    rows = {}
    with open(csv_path, "r") as f:
        for r in csv.DictReader(f):
            rn = (r.get("run_name") or "").strip()
            if rn.endswith("_tcp"):
                rows[rn] = r
    return rows


def _collect_pairwise(rows):
    pairs = []
    for (f_leo, t_leo, desc), (f_ml, t_ml, _desc2) in zip(experiment1_pairs_leo, experiment1_pairs_multilayer):
        rn_leo = "leo_only_%d_to_%d_tcp" % (f_leo, t_leo)
        rn_ml = "multilayer_%d_to_%d_tcp" % (f_ml, t_ml)
        if rn_leo not in rows or rn_ml not in rows:
            continue
        leo = rows[rn_leo]
        ml = rows[rn_ml]
        pairs.append(
            {
                "pair": desc,
                "leo": {
                    "avg_hop_count": _to_float(leo.get("avg_hop_count")),
                    "bottleneck_utilization": _to_float(leo.get("bottleneck_utilization")),
                    "rtt_stretch": _to_float(leo.get("rtt_stretch")),
                    "path_stability_ratio": _to_float(leo.get("path_stability_ratio")),
                },
                "ml": {
                    "avg_hop_count": _to_float(ml.get("avg_hop_count")),
                    "bottleneck_utilization": _to_float(ml.get("bottleneck_utilization")),
                    "rtt_stretch": _to_float(ml.get("rtt_stretch")),
                    "path_stability_ratio": _to_float(ml.get("path_stability_ratio")),
                },
            }
        )
    return pairs


def _panel(ax, pairs, key, title, lower_better=True):
    labels = [p["pair"] for p in pairs]
    x = np.arange(len(labels))
    w = 0.38
    y_leo = [p["leo"][key] for p in pairs]
    y_ml = [p["ml"][key] for p in pairs]
    ax.bar(x - w / 2, y_leo, w, label="LEO-only", color="#1f77b4")
    ax.bar(x + w / 2, y_ml, w, label="Multilayer", color="#2ca02c")
    ax.set_title(title, fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=9)
    ax.grid(True, axis="y", linestyle=":", alpha=0.6)
    note = "lower better" if lower_better else "higher better"
    ax.text(0.01, 0.96, note, transform=ax.transAxes, fontsize=8, va="top")


def main():
    parser = argparse.ArgumentParser(description="Create Figure H multilayer-vs-LEO scorecard.")
    parser.add_argument("--metrics-csv", default=DEFAULT_METRICS, help="Input metrics CSV.")
    parser.add_argument(
        "--out-prefix",
        default=os.path.join(OUT_DIR, "figure_h_multilayer_advantage"),
        help="Output prefix (without extension).",
    )
    parser.add_argument(
        "--duration-s",
        type=int,
        default=simulation_end_time_s,
        help="Figure annotation: intended simulation length (metrics should match). Default: run_list.",
    )
    parser.add_argument(
        "--time-step-ms",
        type=int,
        default=dynamic_state_update_interval_ms,
        help="Figure annotation: dynamic state interval. Default: run_list.",
    )
    args = parser.parse_args()

    n_fstate = _expected_fstate_file_count(args.duration_s, args.time_step_ms)
    print(
        "Figure H: annotated for %d s sim, %d ms state updates; forwarding-state files ≈ %d."
        % (args.duration_s, args.time_step_ms, n_fstate)
    )
    title_suffix = " — %d s sim, %d ms state updates" % (args.duration_s, args.time_step_ms)

    if not os.path.isfile(args.metrics_csv):
        print("ERROR: missing metrics CSV:", args.metrics_csv)
        return 1

    rows = _load_rows(args.metrics_csv)
    pairs = _collect_pairwise(rows)
    if not pairs:
        print("ERROR: no experiment-1 pair rows found in", args.metrics_csv)
        return 1

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    _panel(axes[0, 0], pairs, "avg_hop_count", "(a) Avg hop count", lower_better=True)
    _panel(axes[0, 1], pairs, "bottleneck_utilization", "(b) Bottleneck utilization", lower_better=True)
    _panel(axes[1, 0], pairs, "rtt_stretch", "(c) RTT stretch (max/geodesic)", lower_better=True)
    _panel(axes[1, 1], pairs, "path_stability_ratio", "(d) Path stability ratio", lower_better=False)
    axes[0, 0].legend(loc="upper right")

    fig.suptitle(
        "Figure H — Multilayer vs LEO-only (Kuiper pairwise scorecard)" + title_suffix,
        fontsize=14,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.96])

    out_png = args.out_prefix + ".png"
    out_pdf = args.out_prefix + ".pdf"
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(out_pdf)), exist_ok=True)
    fig.savefig(out_png, dpi=220)
    fig.savefig(out_pdf)
    plt.close(fig)
    print("Wrote:", out_png)
    print("Wrote:", out_pdf)
    return 0


if __name__ == "__main__":
    sys.exit(main())


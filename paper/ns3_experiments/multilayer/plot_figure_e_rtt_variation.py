#!/usr/bin/env python3
"""
Figure E — RTT variation across pairs

Objective:
  Measure stability of routing delay.

Inputs:
  - max_rtt_ms
  - min_rtt_ms
  - rtt_variation_ms   = max_rtt_ms - min_rtt_ms
  - rtt_variation_ratio = max_rtt_ms / min_rtt_ms

Layout:
  Three panels:
    (a) Max RTT
    (b) Max RTT − Min RTT
    (c) Max RTT / Min RTT

Produces separate figures for Kuiper:
  - LEO-only
  - Multilayer

When ``--duration-s`` is set (default from ``run_list``: 25), only RTT samples at
``t ≤ duration_s`` in ``computed_rtt_ms_ts.csv`` (column 0 = time ns) are used for min/max
and derived variation metrics.
"""

import argparse
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURE_DIR = os.path.join(SCRIPT_DIR, "figure-e rtt variation")
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


def _read_rtt_series_ms(run_name, t_max_s=None):
    path = os.path.join(SCRIPT_DIR, "data", run_name, "computed_rtt_ms_ts.csv")
    vals = []
    if not os.path.isfile(path):
        return vals, path
    with open(path, "r") as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            try:
                t_s = float(row[0]) / 1e9
                rtt = float(row[1])
            except ValueError:
                continue
            if t_max_s is None or t_max_s <= 0 or t_s <= t_max_s:
                vals.append(rtt)
    return vals, path


def _compute_row(run_name, pair_desc, label, t_max_s=None):
    vals, src = _read_rtt_series_ms(run_name, t_max_s=t_max_s)
    if not vals:
        return {
            "pair": pair_desc,
            "label": label,
            "run_name": run_name,
            "max_rtt_ms": float("nan"),
            "min_rtt_ms": float("nan"),
            "rtt_variation_ms": float("nan"),
            "rtt_variation_ratio": float("nan"),
            "source_file": src,
        }
    mx = max(vals)
    mn = min(vals)
    return {
        "pair": pair_desc,
        "label": label,
        "run_name": run_name,
        "max_rtt_ms": mx,
        "min_rtt_ms": mn,
        "rtt_variation_ms": mx - mn,
        "rtt_variation_ratio": (mx / mn) if mn > 0 else float("nan"),
        "source_file": src,
    }


def _ecdf(values):
    xs = sorted([v for v in values if v == v])  # drop NaN
    n = len(xs)
    if n == 0:
        return [], []
    ys = [(i + 1) / float(n) for i in range(n)]
    return xs, ys


def _write_rows(rows, csv_path):
    fields = [
        "pair",
        "label",
        "run_name",
        "max_rtt_ms",
        "min_rtt_ms",
        "rtt_variation_ms",
        "rtt_variation_ratio",
        "source_file",
    ]
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def _plot_three_panels(values_max, values_delta, values_ratio, out_prefix):
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), sharey=True)
    specs = [
        ("(a) Max RTT", values_max, "Max. RTT (ms)"),
        ("(b) Max RTT - Min RTT", values_delta, "Max. RTT - Min. RTT (ms)"),
        ("(c) Max RTT / Min RTT", values_ratio, "Max. RTT / Min. RTT (x)"),
    ]

    for i, (subtitle, vals, xlabel) in enumerate(specs):
        x, y = _ecdf(vals)
        ax = axes[i]
        if x:
            ax.plot(x, y, marker="o", lw=2.2, color="#1f77b4", label="Kuiper K1")
        ax.set_title(subtitle, fontsize=11)
        ax.set_xlabel(xlabel)
        ax.grid(True, linestyle=":", alpha=0.7)
        ax.set_ylim(0.0, 1.02)
        if i == 0:
            ax.set_ylabel("ECDF (pairs)")
        if i == 2 and x:
            ax.legend(loc="lower right")

    fig.tight_layout()

    out_png = out_prefix + ".png"
    out_pdf = out_prefix + ".pdf"
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(out_pdf)), exist_ok=True)
    fig.savefig(out_png, dpi=220)
    fig.savefig(out_pdf)
    plt.close(fig)
    print("Wrote:", out_png)
    print("Wrote:", out_pdf)


def main():
    parser = argparse.ArgumentParser(description="Plot Figure E RTT variation for LEO-only and Multilayer.")
    parser.add_argument(
        "--leo-out-prefix",
        default=os.path.join(FIGURE_DIR, "figure_e_rtt_variation_leo_only"),
        help="Output prefix for LEO-only figure.",
    )
    parser.add_argument(
        "--ml-out-prefix",
        default=os.path.join(FIGURE_DIR, "figure_e_rtt_variation_multilayer"),
        help="Output prefix for Multilayer figure.",
    )
    parser.add_argument(
        "--leo-csv",
        default=os.path.join(FIGURE_DIR, "figure_e_rtt_variation_leo_only_values.csv"),
        help="CSV output path for LEO-only per-pair values.",
    )
    parser.add_argument(
        "--ml-csv",
        default=os.path.join(FIGURE_DIR, "figure_e_rtt_variation_multilayer_values.csv"),
        help="CSV output path for Multilayer per-pair values.",
    )
    parser.add_argument(
        "--duration-s",
        type=int,
        default=simulation_end_time_s,
        help="Use RTT samples with t ≤ this (seconds). Default: run_list.simulation_end_time_s.",
    )
    parser.add_argument(
        "--time-step-ms",
        type=int,
        default=dynamic_state_update_interval_ms,
        help="Figure annotation + fstate count. Default: run_list.dynamic_state_update_interval_ms.",
    )
    args = parser.parse_args()

    n_fstate = _expected_fstate_file_count(args.duration_s, args.time_step_ms)
    print(
        "Figure E: RTT samples for t ≤ %d s; forwarding-state files ≈ %d; %d ms state updates."
        % (args.duration_s, n_fstate, args.time_step_ms)
    )
    t_max = float(args.duration_s)

    leo_rows = []
    for from_id, to_id, desc in experiment1_pairs_leo:
        run_name = "leo_only_%d_to_%d_tcp" % (from_id, to_id)
        leo_rows.append(_compute_row(run_name, desc, "leo_only", t_max_s=t_max))
    _write_rows(leo_rows, args.leo_csv)

    ml_rows = []
    for from_id, to_id, desc in experiment1_pairs_multilayer:
        run_name = "multilayer_%d_to_%d_tcp" % (from_id, to_id)
        ml_rows.append(_compute_row(run_name, desc, "multilayer", t_max_s=t_max))
    _write_rows(ml_rows, args.ml_csv)

    leo_max = [r["max_rtt_ms"] for r in leo_rows]
    leo_delta = [r["rtt_variation_ms"] for r in leo_rows]
    leo_ratio = [r["rtt_variation_ratio"] for r in leo_rows]
    _plot_three_panels(
        leo_max,
        leo_delta,
        leo_ratio,
        args.leo_out_prefix,
    )

    ml_max = [r["max_rtt_ms"] for r in ml_rows]
    ml_delta = [r["rtt_variation_ms"] for r in ml_rows]
    ml_ratio = [r["rtt_variation_ratio"] for r in ml_rows]
    _plot_three_panels(
        ml_max,
        ml_delta,
        ml_ratio,
        args.ml_out_prefix,
    )

    print("Wrote:", args.leo_csv)
    print("Wrote:", args.ml_csv)
    return 0


if __name__ == "__main__":
    sys.exit(main())


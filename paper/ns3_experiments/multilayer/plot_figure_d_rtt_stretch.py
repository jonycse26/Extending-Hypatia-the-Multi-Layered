#!/usr/bin/env python3
"""
Figure D — Max RTT / Geodesic RTT

Objective:
  Measure route efficiency relative to a physical lower bound.

Inputs:
  - computed_rtt_ms_ts  (data/<run>/computed_rtt_ms_ts.csv)
  - max_computed_rtt_ms (derived: max of computed_rtt_ms_ts)
  - geodesic_rtt_ms     (derived: min of computed_rtt_ms_ts)
  - rtt_stretch         (derived: max_computed_rtt_ms / geodesic_rtt_ms)

Layout:
  Same figure with two panels (Kuiper only):
    - Panel 1: LEO-only
    - Panel 2: Multilayer

When ``--duration-s`` is set (default from ``run_list``: 25), only RTT samples at
``t ≤ duration_s`` in ``computed_rtt_ms_ts.csv`` (column 0 = time ns) are used for
min/max and stretch. ``--time-step-ms`` annotates the figure (forwarding-state grid).
"""

import argparse
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURE_DIR = os.path.join(SCRIPT_DIR, "figure-d rtt stretch")
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


def _read_computed_rtt_ms_ts(run_name, t_max_s=None):
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


def _calc_pair_metrics(run_name, pair_desc, label, t_max_s=None):
    vals, path = _read_computed_rtt_ms_ts(run_name, t_max_s=t_max_s)
    if not vals:
        return {
            "pair": pair_desc,
            "label": label,
            "run_name": run_name,
            "max_computed_rtt_ms": float("nan"),
            "geodesic_rtt_ms": float("nan"),
            "rtt_stretch": float("nan"),
            "source_file": path,
        }
    geo = min(vals)
    mx = max(vals)
    stretch = (mx / geo) if geo > 0 else float("nan")
    return {
        "pair": pair_desc,
        "label": label,
        "run_name": run_name,
        "max_computed_rtt_ms": mx,
        "geodesic_rtt_ms": geo,
        "rtt_stretch": stretch,
        "source_file": path,
    }


def _ecdf_points(values):
    xs = sorted([v for v in values if v == v])  # drop NaN
    n = len(xs)
    if n == 0:
        return [], []
    ys = [(i + 1) / float(n) for i in range(n)]
    return xs, ys


def _write_csv(rows, csv_path):
    fields = [
        "pair",
        "label",
        "run_name",
        "max_computed_rtt_ms",
        "geodesic_rtt_ms",
        "rtt_stretch",
        "source_file",
    ]
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Plot Figure D (Max RTT / Geodesic RTT) for LEO-only and Multilayer."
    )
    parser.add_argument(
        "--out-prefix",
        default=os.path.join(FIGURE_DIR, "figure_d_rtt_stretch"),
        help="Output prefix for PNG/PDF (without extension).",
    )
    parser.add_argument(
        "--csv-out",
        default=os.path.join(FIGURE_DIR, "figure_d_rtt_stretch_values.csv"),
        help="Output CSV with per-pair metrics.",
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
        "Figure D: RTT samples for t ≤ %d s; forwarding-state files ≈ %d; figure note: %d ms state updates."
        % (args.duration_s, n_fstate, args.time_step_ms)
    )
    title_suffix = " — %d s sim, %d ms state updates" % (args.duration_s, args.time_step_ms)
    t_max = float(args.duration_s)

    rows = []
    leo_vals = []
    ml_vals = []

    for from_id, to_id, desc in experiment1_pairs_leo:
        run_name = "leo_only_%d_to_%d_tcp" % (from_id, to_id)
        r = _calc_pair_metrics(run_name, desc, "leo_only", t_max_s=t_max)
        rows.append(r)
        leo_vals.append(r["rtt_stretch"])

    for from_id, to_id, desc in experiment1_pairs_multilayer:
        run_name = "multilayer_%d_to_%d_tcp" % (from_id, to_id)
        r = _calc_pair_metrics(run_name, desc, "multilayer", t_max_s=t_max)
        rows.append(r)
        ml_vals.append(r["rtt_stretch"])

    _write_csv(rows, args.csv_out)

    x_leo, y_leo = _ecdf_points(leo_vals)
    x_ml, y_ml = _ecdf_points(ml_vals)
    if not x_leo and not x_ml:
        print("ERROR: no valid rtt_stretch values found.")
        return 1

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.0), sharey=True)

    ax0 = axes[0]
    if x_leo:
        ax0.plot(x_leo, y_leo, marker="o", lw=2.2, linestyle="-", color="#1f77b4", label="Kuiper K1")
    ax0.set_title("LEO-only")
    ax0.set_xlabel("Max. RTT / Geodesic RTT (x)")
    ax0.set_ylabel("ECDF (pairs)")
    ax0.grid(True, linestyle=":", alpha=0.7)
    ax0.set_ylim(0.0, 1.02)
    ax0.legend(loc="lower right")

    ax1 = axes[1]
    if x_ml:
        ax1.plot(x_ml, y_ml, marker="o", lw=2.2, linestyle="-", color="#1f77b4", label="Kuiper K1")
    ax1.set_title("Multilayer")
    ax1.set_xlabel("Max. RTT / Geodesic RTT (x)")
    ax1.grid(True, linestyle=":", alpha=0.7)
    ax1.set_ylim(0.0, 1.02)
    ax1.legend(loc="lower right")

    fig.suptitle("Figure D — Max RTT / Geodesic RTT (Kuiper)" + title_suffix, fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.94])

    out_png = args.out_prefix + ".png"
    out_pdf = args.out_prefix + ".pdf"
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(out_pdf)), exist_ok=True)
    fig.savefig(out_png, dpi=220)
    fig.savefig(out_pdf)
    plt.close(fig)

    print("Wrote:", out_png)
    print("Wrote:", out_pdf)
    print("Wrote:", args.csv_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3
"""
Figure Y — Experiment 1: LEO-only vs multilayer (connected dot / line)

Two compact subplots **side by side** (same pairing as Figure H):

  **(a)** Average hop count — two points per city pair (LEO-only vs multilayer), horizontal dodge,
          thin connector per pair (downward slope ⇒ fewer hops for multilayer).

  **(b)** Bottleneck utilization — same layout; legend (LEO-only / Multilayer) is drawn here only.

Data: same scalars as Figure H — ``avg_hop_count`` and ``bottleneck_utilization`` from
``multilayer_all_experiments_metrics.csv`` (default). Use ``--from-runs`` to recompute from
``runs/`` with the same field names (must match export window; see ``export_multilayer_metrics_table.py``).

Output: ``figure-y multilayer improvement ratios/figure_y_multilayer_improvement_ratios.{png,pdf}``
and ``figure_y_multilayer_improvement_ratios_values.csv``.
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
OUT_DIR = os.path.join(SCRIPT_DIR, "figure-y multilayer improvement ratios")
sys.path.insert(0, SCRIPT_DIR)

try:
    from run_list import (
        dynamic_state_update_interval_ms,
        experiment1_pairs_leo,
        experiment1_pairs_multilayer,
        simulation_end_time_s,
    )
except Exception as e:
    raise RuntimeError("Could not import run_list experiment1 definitions: %s" % e)

from evaluation_utils import extract_metrics
from experiment1_figure_metrics import DEFAULT_METRICS, load_experiment1_pairs

COLOR_LEO = "#1f77b4"
COLOR_ML = "#2ca02c"
X_DODGE = 0.14


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


def _collect_pair_metrics_from_runs(duration_s, time_step_ms):
    """Same fields as Figure H / metrics export (single fstate window)."""
    runs_dir = os.path.join(SCRIPT_DIR, "runs")
    out = []
    for (f_leo, t_leo, desc), (f_ml, t_ml, _d2) in zip(experiment1_pairs_leo, experiment1_pairs_multilayer):
        rn_leo = "leo_only_%d_to_%d_tcp" % (f_leo, t_leo)
        rn_ml = "multilayer_%d_to_%d_tcp" % (f_ml, t_ml)
        row = {"pair": desc, "run_leo": rn_leo, "run_ml": rn_ml}
        for side, rn in (("leo", rn_leo), ("ml", rn_ml)):
            rd = os.path.join(runs_dir, rn)
            if not os.path.isdir(rd):
                print("WARNING: missing run dir %s" % rd)
                row["hop_%s" % side] = float("nan")
                row["util_%s" % side] = float("nan")
                continue
            met = extract_metrics(
                rd,
                metrics_duration_s=duration_s,
                metrics_time_step_ms=time_step_ms,
            )
            if met.get("error"):
                print("WARNING [%s]: %s" % (rn, met["error"]))
            row["hop_%s" % side] = _to_float(met.get("avg_hop_count"))
            row["util_%s" % side] = _to_float(met.get("bottleneck_utilization"))

        if row.get("hop_leo") == row.get("hop_leo") or row.get("hop_ml") == row.get("hop_ml"):
            out.append(row)
    return out


def _write_values_csv(pairs, csv_path, duration_s, time_step_ms):
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "pair",
                "run_leo_only",
                "run_multilayer",
                "duration_s",
                "time_step_ms",
                "avg_hop_count_leo_only",
                "avg_hop_count_multilayer",
                "hop_ratio_leo_over_ml",
                "bottleneck_utilization_leo_only",
                "bottleneck_utilization_multilayer",
                "util_ratio_leo_over_ml",
            ]
        )
        for p in pairs:
            hop_l, hop_m = p["hop_leo"], p["hop_ml"]
            hop_ratio = (hop_l / hop_m) if hop_l == hop_l and hop_m == hop_m and hop_m > 0 else ""
            u_l, u_m = p["util_leo"], p["util_ml"]
            util_ratio = (u_l / u_m) if u_l == u_l and u_m == u_m and u_m > 0 else ""
            w.writerow(
                [
                    p["pair"],
                    p.get("run_leo", ""),
                    p.get("run_ml", ""),
                    duration_s,
                    time_step_ms,
                    hop_l,
                    hop_m,
                    hop_ratio,
                    u_l,
                    u_m,
                    util_ratio,
                ]
            )


def _short_xlabel(desc):
    return desc.replace(" to ", "\n")


def _plot_connected_dots(ax, x_centers, y_leo, y_ml, xlabels, ylabel, title, scatter_labels=True):
    n = len(x_centers)
    x_leo = x_centers - X_DODGE
    x_ml = x_centers + X_DODGE

    for i in range(n):
        a, b = y_leo[i], y_ml[i]
        if a == a and b == b:
            ax.plot(
                [x_leo[i], x_ml[i]],
                [a, b],
                color="#9e9e9e",
                linewidth=1.05,
                alpha=0.9,
                zorder=1,
                solid_capstyle="round",
            )

    mask_leo = np.array([v == v for v in y_leo])
    mask_ml = np.array([v == v for v in y_ml])
    leo_lab = "LEO-only" if scatter_labels else None
    ml_lab = "Multilayer" if scatter_labels else None
    ax.scatter(
        x_leo[mask_leo],
        np.asarray(y_leo, dtype=float)[mask_leo],
        s=72,
        c=COLOR_LEO,
        edgecolors="#0d47a1",
        linewidths=0.65,
        zorder=3,
        label=leo_lab,
    )
    ax.scatter(
        x_ml[mask_ml],
        np.asarray(y_ml, dtype=float)[mask_ml],
        s=72,
        c=COLOR_ML,
        edgecolors="#1b5e20",
        linewidths=0.65,
        zorder=3,
        label=ml_lab,
    )

    ax.set_xticks(x_centers)
    ax.set_xticklabels(xlabels, fontsize=8.5, ha="center")
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(title, fontsize=11)
    ax.grid(True, axis="y", linestyle=":", alpha=0.55)


def main():
    ap = argparse.ArgumentParser(description="Figure Y: hop count & util connected dot plots.")
    ap.add_argument("--metrics-csv", default=DEFAULT_METRICS, help="Input metrics CSV (with --use-metrics-csv).")
    ap.add_argument(
        "--from-runs",
        action="store_true",
        help="Recompute from runs/ (default: same CSV scalars as Figure H).",
    )
    ap.add_argument(
        "--duration-s",
        type=int,
        default=simulation_end_time_s,
        help="Clip logs / fstate window (default: run_list 25 s).",
    )
    ap.add_argument(
        "--time-step-ms",
        type=int,
        default=dynamic_state_update_interval_ms,
        help="Dynamic state interval (default: run_list 1000 ms).",
    )
    ap.add_argument(
        "--out-prefix",
        default=None,
        help="Output path without extension.",
    )
    ap.add_argument(
        "--suptitle",
        action="store_true",
        help="Add simulation window text above the panels (off by default).",
    )
    args = ap.parse_args()

    print(
        "Figure Y: experiment 1 · %d s · %d ms dynamic state"
        % (args.duration_s, args.time_step_ms)
    )

    if args.from_runs:
        pairs = _collect_pair_metrics_from_runs(args.duration_s, args.time_step_ms)
        if not pairs:
            print("ERROR: no experiment-1 pairs extracted from runs/")
            return 1
    else:
        if not os.path.isfile(args.metrics_csv):
            print("ERROR: missing metrics CSV:", args.metrics_csv)
            return 1
        pairs = load_experiment1_pairs(args.metrics_csv)
        if not pairs:
            print("ERROR: no experiment-1 pair rows in", args.metrics_csv)
            return 1

    for p in pairs:
        print(
            "%s: hops LEO=%.2f ML=%.2f · bottleneck util LEO=%.3f ML=%.3f"
            % (p["pair"], p["hop_leo"], p["hop_ml"], p["util_leo"], p["util_ml"])
        )

    labels = [_short_xlabel(p["pair"]) for p in pairs]
    hop_leo = [p["hop_leo"] for p in pairs]
    hop_ml = [p["hop_ml"] for p in pairs]
    util_leo = [p["util_leo"] for p in pairs]
    util_ml = [p["util_ml"] for p in pairs]

    x = np.arange(len(labels), dtype=float)

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(10.0, 3.85), layout="constrained", sharex=True)

    _plot_connected_dots(
        ax_a,
        x,
        hop_leo,
        hop_ml,
        labels,
        "Average hop count",
        "(a) Hop count",
        scatter_labels=False,
    )
    _plot_connected_dots(
        ax_b,
        x,
        util_leo,
        util_ml,
        labels,
        "Bottleneck utilization",
        "(b) Bottleneck utilization",
        scatter_labels=True,
    )

    ax_b.legend(loc="upper right", fontsize=8, framealpha=0.95, ncol=1)

    # Fixed y-axis ranges/ticks (Hypatia / thesis reference style).
    ax_a.set_ylim(3.5, 17.0)
    ax_a.set_yticks([4, 6, 8, 10, 12, 14, 16])
    ax_b.set_ylim(0.1, 0.6)
    ax_b.set_yticks([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])

    out_prefix = args.out_prefix or os.path.join(OUT_DIR, "figure_y_multilayer_improvement_ratios")
    os.makedirs(os.path.dirname(os.path.abspath(out_prefix)), exist_ok=True)
    values_csv = out_prefix + "_values.csv"
    _write_values_csv(pairs, values_csv, args.duration_s, args.time_step_ms)
    print("Wrote:", values_csv)

    if args.suptitle:
        fig.suptitle(
            "Experiment 1 · %d s simulation · %d ms dynamic state"
            % (args.duration_s, args.time_step_ms),
            fontsize=10,
            y=1.02,
        )

    png = out_prefix + ".png"
    pdf = out_prefix + ".pdf"
    fig.savefig(png, dpi=220)
    fig.savefig(pdf)
    plt.close(fig)
    print("Figure Y: %d pairs · connected dots (hop + bottleneck util)" % len(pairs))
    print("Wrote:", png)
    print("Wrote:", pdf)
    return 0


if __name__ == "__main__":
    sys.exit(main())

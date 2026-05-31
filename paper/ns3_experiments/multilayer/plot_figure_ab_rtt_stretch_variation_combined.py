#!/usr/bin/env python3
"""
Combined figure: (a) RTT stretch — one ECDF axis with LEO-only vs multilayer overlaid — and (b) RTT variation boxplots (Figure Z).

Layout: **two columns** of equal width — (a) left, (b) right.

Writes PNG/PDF under ``figure-ab rtt stretch variation/``.
"""

import argparse
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.axes import Axes

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURE_DIR = os.path.join(SCRIPT_DIR, "figure-ab rtt stretch variation")
sys.path.insert(0, SCRIPT_DIR)

import plot_figure_d_rtt_stretch as figd
import plot_figure_z_experiment1_long_rtt_variation_boxplot as figz

try:
    from run_list import (
        experiment1_pairs_leo,
        experiment1_pairs_multilayer,
        simulation_end_time_s,
    )
except Exception as e:
    raise RuntimeError("Could not import run_list: %s" % e)


def _axes_from_subplots_result(res):
    if isinstance(res, Axes):
        return res
    return res.ravel()[0]


# Shared vertical margins for sub_a / sub_b (same axis height). Higher top = taller plots, less dead band under titles.
COMBINED_PANEL_TOP = 0.91
COMBINED_PANEL_BOTTOM = 0.28


def _plot_panel_stretch(subfig, t_max, csv_out, *, top, bottom):
    ax = _axes_from_subplots_result(subfig.subplots(1, 1))

    rows = []
    leo_vals = []
    ml_vals = []
    for from_id, to_id, desc in experiment1_pairs_leo:
        run_name = "leo_only_%d_to_%d_tcp" % (from_id, to_id)
        r = figd._calc_pair_metrics(run_name, desc, "leo_only", t_max_s=t_max)
        rows.append(r)
        leo_vals.append(r["rtt_stretch"])
    for from_id, to_id, desc in experiment1_pairs_multilayer:
        run_name = "multilayer_%d_to_%d_tcp" % (from_id, to_id)
        r = figd._calc_pair_metrics(run_name, desc, "multilayer", t_max_s=t_max)
        rows.append(r)
        ml_vals.append(r["rtt_stretch"])

    if csv_out:
        figd._write_csv(rows, csv_out)

    x_leo, y_leo = figd._ecdf_points(leo_vals)
    x_ml, y_ml = figd._ecdf_points(ml_vals)
    if not x_leo and not x_ml:
        return False

    if x_leo:
        ax.plot(
            x_leo,
            y_leo,
            marker="o",
            lw=2.2,
            linestyle="-",
            color=figz.COLOR_LEO,
            label="LEO-only",
        )
    if x_ml:
        ax.plot(
            x_ml,
            y_ml,
            marker="o",
            lw=2.2,
            linestyle="-",
            color=figz.COLOR_ML,
            label="Multilayer",
        )

    ax.set_xlabel("Max. RTT / Geodesic RTT (x)")
    ax.set_ylabel("ECDF (pairs)")
    ax.grid(True, linestyle=":", alpha=0.7)
    ax.set_ylim(0.0, 1.02)
    xs = []
    if x_leo:
        xs.extend(x_leo)
    if x_ml:
        xs.extend(x_ml)
    if xs:
        lo, hi = min(xs), max(xs)
        span = hi - lo
        pad = max(span * 0.04, 0.02) if span > 0 else 0.05
        ax.set_xlim(lo - pad, hi + pad)
    ax.legend(loc="lower right")
    subfig.subplots_adjust(left=0.14, right=0.98, top=top, bottom=bottom)
    subfig.text(
        0.5,
        0.995,
        "(a) RTT stretch",
        transform=subfig.transSubfigure,
        ha="center",
        va="top",
        fontsize=11,
    )
    return True


def main():
    ap = argparse.ArgumentParser(description="Combined (a) RTT stretch + (b) RTT variation (experiment 1).")
    ap.add_argument("--out-prefix", default=None, help="Output path without extension.")
    ap.add_argument("--metrics-csv", default=figz.DEFAULT_METRICS_CSV)
    ap.add_argument(
        "--duration-s",
        type=float,
        default=float(simulation_end_time_s),
        help="Clip samples (seconds); shared by stretch and variation panels.",
    )
    ap.add_argument("--window", type=int, default=48, help="Sliding window size (Figure Z).")
    ap.add_argument("--step", type=int, default=24, help="Sliding window step (Figure Z).")
    ap.add_argument(
        "--csv-out",
        default=os.path.join(FIGURE_DIR, "figure_ab_rtt_stretch_values.csv"),
        help="Per-pair stretch metrics CSV (same as Figure D).",
    )
    ap.add_argument("--no-csv", action="store_true", help="Do not write stretch metrics CSV.")
    args = ap.parse_args()

    t_max = float(args.duration_s)
    metrics = figz._load_metrics_by_run(args.metrics_csv)
    pairs = figz._collect_all_pairs(metrics, t_max, args.window, args.step)
    if not pairs:
        print("ERROR: no pair had both LEO and multilayer variation samples.")
        return 1

    # Two columns with equal subfigure width: (a) combined stretch ECDF | (b) variation boxplots
    fig = plt.figure(figsize=(15.0, 6.9))
    sub_a, sub_b = fig.subfigures(1, 2, width_ratios=[1.0, 1.0], wspace=0.10)

    csv_path = None if args.no_csv else args.csv_out
    if not _plot_panel_stretch(
        sub_a,
        t_max,
        csv_path,
        top=COMBINED_PANEL_TOP,
        bottom=COMBINED_PANEL_BOTTOM,
    ):
        print("ERROR: no valid rtt_stretch values found.")
        return 1

    ax_b = _axes_from_subplots_result(sub_b.subplots(1, 1))
    sub_b.subplots_adjust(
        left=0.12,
        right=0.97,
        top=COMBINED_PANEL_TOP,
        bottom=COMBINED_PANEL_BOTTOM,
    )
    figz.render_rtt_variation_boxplot_on_ax(ax_b, pairs, metrics)
    sub_b.text(
        0.5,
        0.995,
        "(b) RTT Variation",
        transform=sub_b.transSubfigure,
        ha="center",
        va="top",
        fontsize=11,
    )
    fig.legend(
        handles=figz.rtt_variation_legend_handles(),
        loc="upper right",
        bbox_to_anchor=(0.99, 0.98),
        bbox_transform=sub_b.transSubfigure,
        fontsize=7,
        framealpha=0.95,
        borderaxespad=0.2,
    )

    out_prefix = args.out_prefix or os.path.join(FIGURE_DIR, "figure_ab_rtt_stretch_variation")
    os.makedirs(os.path.dirname(os.path.abspath(out_prefix)), exist_ok=True)
    png = out_prefix + ".png"
    pdf = out_prefix + ".pdf"
    fig.savefig(png, dpi=220, bbox_inches="tight", pad_inches=0.08)
    fig.savefig(pdf, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    print("Combined AB: %d variation pairs · w=%d step=%d" % (len(pairs), args.window, args.step))
    print("Wrote:", png)
    print("Wrote:", pdf)
    if csv_path:
        print("Wrote:", csv_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

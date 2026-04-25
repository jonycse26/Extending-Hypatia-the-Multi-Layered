#!/usr/bin/env python3
"""
Figure J — Load-shift (LEO → MEO backbone)

Generates a clear comparison of ISL utilization by link class (LEO-only vs multilayer),
plus a plain-language summary. See module docstring in previous revisions for metric defs.

Bars are built from ``multilayer_all_experiments_metrics.csv`` (scalar aggregates per run).
``--duration-s`` / ``--time-step-ms`` annotate the figure for the intended simulation setup
(default: ``run_list``: 25 s, 1000 ms → ``dynamic_state_1000ms_for_25s``). Re-export metrics
after 25 s experiment-1 TCP runs so the chart matches the caption.
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
OUT_DIR = os.path.join(SCRIPT_DIR, "figure-j load-shift")
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

# Plain-language x-axis: maps to leo_leo, meo_touching, meo_meo in data order
X_LABELS = [
    "LEO mesh\n(LEO–LEO links)",
    "Touches MEO*\n(vertical + feeder)",
    "MEO backbone\n(MEO–MEO)",
]


def _expected_fstate_file_count(duration_s, time_step_ms):
    if duration_s < 0 or time_step_ms <= 0:
        return 0
    return (duration_s * 1000) // time_step_ms + 1


def _to_float(v):
    try:
        return float(v)
    except Exception:
        return float("nan")


def _nanmean(xs):
    vals = [x for x in xs if x == x]
    if not vals:
        return float("nan")
    return float(sum(vals) / len(vals))


def _load_tcp_rows(csv_path):
    rows = {}
    with open(csv_path, "r") as f:
        for r in csv.DictReader(f):
            rn = (r.get("run_name") or "").strip()
            if rn.endswith("_tcp"):
                rows[rn] = r
    return rows


def _aggregate_load_shift(rows, verbose=False):
    keys_max = (
        "leo_leo_isl_max_util",
        "meo_touching_isl_max_util",
        "meo_meo_isl_max_util",
    )
    keys_mean = (
        "leo_leo_isl_mean_util_nz",
        "meo_touching_isl_mean_util_nz",
        "meo_meo_isl_mean_util_nz",
    )
    leo_max = {k: [] for k in keys_max}
    ml_max = {k: [] for k in keys_max}
    leo_mn = {k: [] for k in keys_mean}
    ml_mn = {k: [] for k in keys_mean}

    for (f_leo, t_leo, desc), (f_ml, t_ml, _d2) in zip(
        experiment1_pairs_leo, experiment1_pairs_multilayer
    ):
        rn_leo = "leo_only_%d_to_%d_tcp" % (f_leo, t_leo)
        rn_ml = "multilayer_%d_to_%d_tcp" % (f_ml, t_ml)
        if rn_leo not in rows or rn_ml not in rows:
            if verbose:
                print("skip pair %s: missing %s or %s" % (desc, rn_leo, rn_ml))
            continue
        rlo, rml = rows[rn_leo], rows[rn_ml]
        if verbose:
            print(
                "pair %s  LEO-LEO peak: leo_only=%.4f multilayer=%.4f"
                % (desc, _to_float(rlo.get("leo_leo_isl_max_util")), _to_float(rml.get("leo_leo_isl_max_util")))
            )
        for k in keys_max:
            leo_max[k].append(_to_float(rlo.get(k)))
            ml_max[k].append(_to_float(rml.get(k)))
        for k in keys_mean:
            leo_mn[k].append(_to_float(rlo.get(k)))
            ml_mn[k].append(_to_float(rml.get(k)))

    return {
        "max_leo": [_nanmean(leo_max[k]) for k in keys_max],
        "max_ml": [_nanmean(ml_max[k]) for k in keys_max],
        "mean_leo": [_nanmean(leo_mn[k]) for k in keys_mean],
        "mean_ml": [_nanmean(ml_mn[k]) for k in keys_mean],
    }


def _leo_reduction_pct(leo_only_val, multilayer_val):
    if leo_only_val != leo_only_val or multilayer_val != multilayer_val:
        return float("nan")
    if leo_only_val <= 0:
        return float("nan")
    return float((leo_only_val - multilayer_val) / leo_only_val * 100.0)


def _bar_heights(ys):
    return [0.0 if (y != y) else float(y) for y in ys]


def _annotate_bars(ax, x, ys, w):
    """Small labels on top of bars so near-zero values are readable."""
    for xi, y in zip(x, ys):
        if y <= 1e-6:
            lbl = "~0"
            yoff = 0.02
        else:
            lbl = "%.2f" % y
            yoff = y + 0.02
        ax.text(xi, yoff, lbl, ha="center", va="bottom", fontsize=7, color="#333333")


def _panel(ax, y_leo, y_ml, title, ylabel):
    x = np.arange(len(X_LABELS))
    w = 0.36
    yl, ym = _bar_heights(y_leo), _bar_heights(y_ml)
    ax.bar(x - w / 2, yl, w, label="LEO-only", color="#1f77b4", zorder=2)
    ax.bar(x + w / 2, ym, w, label="Multilayer", color="#2ca02c", zorder=2)
    _annotate_bars(ax, x - w / 2, yl, w)
    _annotate_bars(ax, x + w / 2, ym, w)
    ax.set_xticks(x)
    ax.set_xticklabels(X_LABELS, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(title, fontsize=12, pad=8)
    ax.grid(True, axis="y", linestyle=":", alpha=0.65)
    ax.set_ylim(0.0, 1.12)
    ax.margins(x=0.02)


def main():
    parser = argparse.ArgumentParser(description="Create Figure J load-shift bars.")
    parser.add_argument("--metrics-csv", default=DEFAULT_METRICS, help="Input metrics CSV.")
    parser.add_argument(
        "--out-prefix",
        default=os.path.join(OUT_DIR, "figure_j_load_shift"),
        help="Output prefix (without extension).",
    )
    parser.add_argument("--verbose", action="store_true", help="Print per-pair LEO–LEO peaks.")
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
        "Figure J: annotated for %d s sim, %d ms state updates; forwarding-state files ≈ %d."
        % (args.duration_s, args.time_step_ms, n_fstate)
    )
    if not os.path.isfile(args.metrics_csv):
        print("ERROR: missing metrics CSV:", args.metrics_csv)
        return 1

    rows = _load_tcp_rows(args.metrics_csv)
    agg = _aggregate_load_shift(rows, verbose=args.verbose)
    if not any(v == v for v in agg["max_leo"] + agg["max_ml"]):
        print("ERROR: no usable ISL utilization columns; check CSV / re-export metrics.")
        return 1

    u_lo_peak = agg["max_leo"][0]
    u_ml_peak = agg["max_ml"][0]
    u_lo_mean = agg["mean_leo"][0]
    u_ml_mean = agg["mean_ml"][0]
    red_peak = _leo_reduction_pct(u_lo_peak, u_ml_peak)
    red_mean = _leo_reduction_pct(u_lo_mean, u_ml_mean)

    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(14.0, 5.2))

    _panel(
        ax0,
        agg["max_leo"],
        agg["max_ml"],
        "(a) Peak utilization",
        "Utilization (0 = idle, 1 = saturated)",
    )
    _panel(
        ax1,
        agg["mean_leo"],
        agg["mean_ml"],
        "(b) Typical loaded links",
        "Mean utilization (only links with traffic)",
    )

    h_l, l_l = ax0.get_legend_handles_labels()
    fig.legend(
        h_l,
        l_l,
        loc="upper center",
        ncol=2,
        frameon=True,
        bbox_to_anchor=(0.5, 0.91),
        fontsize=11,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.90])

    out_png = args.out_prefix + ".png"
    out_pdf = args.out_prefix + ".pdf"
    csv_out = args.out_prefix + "_values.csv"
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)

    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)
    print("Wrote:", out_png)
    print("Wrote:", out_pdf)
    if red_peak == red_peak:
        print("LEO–LEO load reduction (peak, aggregated): %.2f %%" % red_peak)
    if red_mean == red_mean:
        print("LEO–LEO load reduction (mean_nz, aggregated): %.2f %%" % red_mean)

    with open(csv_out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "panel",
                "link_class",
                "stat",
                "leo_only_mean_over_pairs",
                "multilayer_mean_over_pairs",
                "leo_leo_load_reduction_pct_vs_leo_only",
            ]
        )
        link_classes = ["LEO_LEO", "LEO_MEO_touching", "MEO_MEO"]
        rp0 = _leo_reduction_pct(agg["max_leo"][0], agg["max_ml"][0])
        rm0 = _leo_reduction_pct(agg["mean_leo"][0], agg["mean_ml"][0])
        for i, lc in enumerate(link_classes):
            w.writerow(
                [
                    "peak_max",
                    lc,
                    "max_util",
                    agg["max_leo"][i],
                    agg["max_ml"][i],
                    rp0 if i == 0 else "",
                ]
            )
        for i, lc in enumerate(link_classes):
            w.writerow(
                [
                    "loaded_mean_nz",
                    lc,
                    "mean_util_nonzero",
                    agg["mean_leo"][i],
                    agg["mean_ml"][i],
                    rm0 if i == 0 else "",
                ]
            )
        w.writerow([])
        w.writerow(["derived", "LEO_LEO", "leo_load_reduction_pct_peak_mean_over_pairs", rp0 if rp0 == rp0 else "", "", ""])
        w.writerow(["derived", "LEO_LEO", "leo_load_reduction_pct_mean_nz_mean_over_pairs", rm0 if rm0 == rm0 else "", "", ""])
    print("Wrote:", csv_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

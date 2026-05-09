#!/usr/bin/env python3
"""
Figure O — ECDF of LEO mesh load reduction (LEO-only vs multilayer)

For each matched scenario pair (same traffic, LEO-only constellation vs multilayer):

  leo_mesh_load_reduction_ratio =
      (U_leo_only − U_multilayer) / U_leo_only

where U is **LEO–LEO ISL utilization** from ``isl_utilization.csv`` aggregates:

  - **Peak:** ``leo_leo_isl_max_util`` (from ``multilayer_all_experiments_metrics.csv``)
  - **Mean (loaded):** ``leo_leo_isl_mean_util_nz`` (mean over non-zero LEO–LEO samples)

Pairs are discovered as:

  - ``leo_only_<f>_to_<t>_tcp`` with ``multilayer_<f+OFFSET_DIFF>_to_<t+OFFSET_DIFF>_tcp``
    (``OFFSET_DIFF`` from ``run_list``, default 36).
  - Experiment 3: ``example3_distance_{tier}_<f>_to_<t>_tcp`` (LEO GS IDs) with the
    multilayer row using ``f+OFFSET_DIFF``, ``t+OFFSET_DIFF`` (same tier).

Undefined when U_leo_only ≤ 0 (no LEO-mesh load to normalize); those pairs are skipped.

Inputs: ``multilayer_all_experiments_metrics.csv`` (run ``export_multilayer_metrics_table.py``).

X-axis: load reduction ratio; Y-axis: empirical CDF (fraction of scenarios with ratio ≤ x).
"""

import argparse
import csv
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURE_DIR = os.path.join(SCRIPT_DIR, "figure-o leo mesh load reduction")
DEFAULT_METRICS = os.path.join(SCRIPT_DIR, "multilayer_all_experiments_metrics.csv")
sys.path.insert(0, SCRIPT_DIR)

try:
    from run_list import (
        OFFSET_DIFF,
        dynamic_state_update_interval_ms,
        experiment3_distance_tiers,
        experiment3_pairs_leo,
        experiment3_pairs_multilayer,
        simulation_end_time_s,
    )
except Exception as e:
    raise RuntimeError("Could not import run_list: %s" % e)


def _to_float(v):
    try:
        if v is None or v == "":
            return float("nan")
        return float(v)
    except Exception:
        return float("nan")


def _load_tcp_rows(csv_path):
    rows = {}
    with open(csv_path, "r") as f:
        for r in csv.DictReader(f):
            rn = (r.get("run_name") or "").strip()
            if rn.endswith("_tcp"):
                rows[rn] = r
    return rows


def _reduction_ratio(u_leo, u_ml):
    """(U_lo - U_ml) / U_lo; NaN if U_lo is NaN or <= 0."""
    if u_leo != u_leo or u_ml != u_ml:
        return float("nan")
    if u_leo <= 0.0:
        return float("nan")
    return float((u_leo - u_ml) / u_leo)


def _ecdf_xy(values):
    """Return (x, y) for a step ECDF: F(x) = fraction of samples <= x."""
    v = np.asarray([x for x in values if x == x], dtype=float)
    if v.size == 0:
        return np.array([]), np.array([])
    v.sort()
    y = np.arange(1, v.size + 1, dtype=float) / v.size
    return v, y


def _discover_pairs(rows, offset):
    """
    Return list of (description, run_leo, run_ml).
    """
    pairs = []
    seen = set()

    # leo_only_* → multilayer_* (+offset)
    pat_lo = re.compile(r"^leo_only_(\d+)_to_(\d+)_tcp$")
    for rn in sorted(rows.keys()):
        m = pat_lo.match(rn)
        if not m:
            continue
        f, t = int(m.group(1)), int(m.group(2))
        rn_ml = "multilayer_%d_to_%d_tcp" % (f + offset, t + offset)
        if rn_ml not in rows:
            continue
        key = (rn, rn_ml)
        if key in seen:
            continue
        seen.add(key)
        rlo = rows[rn]
        desc = "leo_only %s→%s" % (rlo.get("from_id"), rlo.get("to_id"))
        pairs.append((desc, rn, rn_ml))

    # example3_distance_{tier}_f_t_tcp — lists align with experiment3_distance_tiers order
    tier_list = list(experiment3_distance_tiers)
    for idx, tier in enumerate(tier_list):
        if idx >= len(experiment3_pairs_leo):
            break
        fl, tl, d = experiment3_pairs_leo[idx]
        fm, tm, _ = experiment3_pairs_multilayer[idx]
        rn_leo = "example3_distance_%s_%d_to_%d_tcp" % (tier, fl, tl)
        rn_ml = "example3_distance_%s_%d_to_%d_tcp" % (tier, fm, tm)
        if rn_leo not in rows or rn_ml not in rows:
            continue
        key = (rn_leo, rn_ml)
        if key in seen:
            continue
        seen.add(key)
        pairs.append((d, rn_leo, rn_ml))

    return pairs


def _plot_ecdf(ax, ratios, label, color):
    x, y = _ecdf_xy(ratios)
    if x.size == 0:
        return
    x_step = np.concatenate([[x[0]], x])
    y_step = np.concatenate([[0.0], y])
    ax.step(x_step, y_step, where="post", color=color, linewidth=2.0, label=label)


def main():
    parser = argparse.ArgumentParser(
        description="Figure O: ECDF of LEO mesh load reduction (peak / mean LEO–LEO util)."
    )
    parser.add_argument("--metrics-csv", default=DEFAULT_METRICS, help="Input metrics CSV.")
    parser.add_argument(
        "--out-prefix",
        default=os.path.join(FIGURE_DIR, "figure_o_leo_mesh_load_reduction_ecdf"),
        help="Output prefix (.png / .pdf / _values.csv).",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=OFFSET_DIFF,
        help="Ground-station ID offset LEO-only → multilayer (default: run_list.OFFSET_DIFF).",
    )
    parser.add_argument(
        "--duration-s",
        type=int,
        default=simulation_end_time_s,
        help="Caption: simulation length (metrics should match).",
    )
    parser.add_argument(
        "--time-step-ms",
        type=int,
        default=dynamic_state_update_interval_ms,
        help="Caption: dynamic state interval.",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.metrics_csv):
        print("ERROR: missing metrics CSV:", args.metrics_csv)
        print("  Run: python3 export_multilayer_metrics_table.py")
        return 1

    rows = _load_tcp_rows(args.metrics_csv)
    pair_list = _discover_pairs(rows, args.offset)

    records = []
    ratios_peak = []
    ratios_mean = []

    for desc, rn_lo, rn_ml in pair_list:
        rlo, rml = rows[rn_lo], rows[rn_ml]
        ulp = _to_float(rlo.get("leo_leo_isl_max_util"))
        ump = _to_float(rml.get("leo_leo_isl_max_util"))
        ulm = _to_float(rlo.get("leo_leo_isl_mean_util_nz"))
        umm = _to_float(rml.get("leo_leo_isl_mean_util_nz"))

        rp = _reduction_ratio(ulp, ump)
        rm = _reduction_ratio(ulm, umm)

        records.append(
            {
                "description": desc,
                "run_leo_only": rn_lo,
                "run_multilayer": rn_ml,
                "leo_leo_max_util_leo_only": ulp,
                "leo_leo_max_util_multilayer": ump,
                "load_reduction_ratio_peak": rp,
                "leo_leo_mean_util_nz_leo_only": ulm,
                "leo_leo_mean_util_nz_multilayer": umm,
                "load_reduction_ratio_mean_nz": rm,
            }
        )
        if rp == rp:
            ratios_peak.append(rp)
        if rm == rm:
            ratios_mean.append(rm)

    n_pairs = len(pair_list)
    n_peak = len(ratios_peak)
    n_mean = len(ratios_mean)
    print(
        "Figure O: %d scenario pairs; %d with defined peak ratio; %d with defined mean_nz ratio"
        % (n_pairs, n_peak, n_mean)
    )

    csv_out = args.out_prefix + "_values.csv"
    os.makedirs(os.path.dirname(os.path.abspath(csv_out)), exist_ok=True)
    with open(csv_out, "w", newline="") as fp:
        if records:
            w = csv.DictWriter(fp, fieldnames=list(records[0].keys()))
            w.writeheader()
            w.writerows(records)
    print("Wrote:", csv_out)

    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    _plot_ecdf(
        ax,
        ratios_peak,
        "Peak LEO–LEO util (max over time/links)",
        "#1f77b4",
    )
    _plot_ecdf(
        ax,
        ratios_mean,
        "Mean loaded LEO–LEO util (non-zero samples)",
        "#ff7f0e",
    )

    ax.set_xlabel(
        "LEO mesh load reduction ratio  "
        r"$\frac{U_{\mathrm{LEO\text{-}only}} - U_{\mathrm{multilayer}}}{U_{\mathrm{LEO\text{-}only}}}$"
        "\n(LEO–LEO ISL utilization)",
        fontsize=10,
    )
    ax.set_ylabel("ECDF (fraction of scenarios ≤ x)", fontsize=11)
    ax.set_title(
        "Figure O — LEO mesh load reduction (LEO-only vs multilayer)\n"
        "%d s sim, %d ms state updates · %d pairs"
        % (args.duration_s, args.time_step_ms, n_pairs),
        fontsize=11,
    )
    ax.grid(True, linestyle=":", alpha=0.65)
    ax.legend(loc="lower right", fontsize=9, framealpha=0.95)
    ax.set_xlim(-0.05, 1.15)
    ax.set_ylim(0.0, 1.05)
    fig.tight_layout()

    out_png = args.out_prefix + ".png"
    out_pdf = args.out_prefix + ".pdf"
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)
    print("Wrote:", out_png)
    print("Wrote:", out_pdf)

    if n_peak == 0 and n_mean == 0:
        print(
            "WARNING: no valid ratios (need U_leo_only > 0 for peak/mean). "
            "Check metrics CSV and ISL utilization logs."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

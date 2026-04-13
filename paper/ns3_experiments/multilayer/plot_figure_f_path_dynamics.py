#!/usr/bin/env python3
"""
Figure F — Path structure changes across pairs

Objective:
  Quantify routing dynamics and path stability.

Inputs (per pair):
  - path_change_count
  - hop_count_variation
  - hop_count_ratio

Layout:
  Three panels:
    (a) number of path changes
    (b) max hop count − min hop count
    (c) max hop count / min hop count

Creates figures for:
  - LEO-only
  - Multilayer

Notes:
  - Kuiper values are loaded from multilayer_all_experiments_metrics.csv
  - Optional external CSVs can be supplied for Telesat / Starlink

Metrics are **per-run scalars** (not time series). ``--duration-s`` / ``--time-step-ms`` annotate the
figure and console so CSVs are understood to reflect that simulation setup (default: match
``run_list``: 25 s, 1000 ms → ``dynamic_state_1000ms_for_25s``). Regenerate
``multilayer_all_experiments_metrics.csv`` from 25 s runs for comparable numbers.
"""

import argparse
import csv
import os
import sys
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURE_DIR = os.path.join(SCRIPT_DIR, "figure-f path dynamics")
DEFAULT_KUIPER_METRICS = os.path.join(SCRIPT_DIR, "multilayer_all_experiments_metrics.csv")
sys.path.insert(0, SCRIPT_DIR)

try:
    from run_list import (
        dynamic_state_update_interval_ms,
        simulation_end_time_s,
    )
except Exception as e:
    raise RuntimeError("Could not import run_list timing defaults: %s" % e)


def _expected_fstate_file_count(duration_s, time_step_ms):
    if duration_s < 0 or time_step_ms <= 0:
        return 0
    return (duration_s * 1000) // time_step_ms + 1


def _to_float(v):
    try:
        return float(v)
    except Exception:
        return float("nan")


def _ecdf(values: List[float]) -> Tuple[List[float], List[float]]:
    xs = sorted([v for v in values if v == v])  # drop NaN
    n = len(xs)
    if n == 0:
        return [], []
    ys = [(i + 1) / float(n) for i in range(n)]
    return xs, ys


def _empty_metric_map():
    return {
        "path_change_count": [],
        "hop_count_variation": [],
        "hop_count_ratio": [],
    }


def _read_kuiper_metrics(csv_path):
    """
    Read Kuiper values from multilayer_all_experiments_metrics.csv.
    Returns:
      {
        "leo_only": {"path_change_count": [...], ...},
        "multilayer": {"path_change_count": [...], ...},
      }
    """
    out = {
        "leo_only": _empty_metric_map(),
        "multilayer": _empty_metric_map(),
    }
    if not os.path.isfile(csv_path):
        print("WARNING: Kuiper metrics CSV not found:", csv_path)
        return out

    with open(csv_path, "r") as f:
        r = csv.DictReader(f)
        for row in r:
            run_name = (row.get("run_name") or "").strip()
            # Keep experiment-1 TCP runs only.
            if not run_name.endswith("_tcp"):
                continue
            if run_name.startswith("leo_only_"):
                mode = "leo_only"
            elif run_name.startswith("multilayer_"):
                mode = "multilayer"
            else:
                continue

            out[mode]["path_change_count"].append(_to_float(row.get("path_change_count", "")))
            out[mode]["hop_count_variation"].append(_to_float(row.get("hop_count_variation", "")))
            out[mode]["hop_count_ratio"].append(_to_float(row.get("hop_count_ratio", "")))
    return out


def _read_external_constellation(csv_path, constellation_name):
    """
    Read optional external constellation CSV.
    Expected columns:
      scenario_type,path_change_count,hop_count_variation,hop_count_ratio
    where scenario_type is one of: leo_only, multilayer
    """
    out = {
        "leo_only": _empty_metric_map(),
        "multilayer": _empty_metric_map(),
    }
    if not csv_path:
        print("WARNING: %s CSV not provided; skipping." % constellation_name)
        return out
    if not os.path.isfile(csv_path):
        print("WARNING: %s CSV not found: %s" % (constellation_name, csv_path))
        return out

    with open(csv_path, "r") as f:
        r = csv.DictReader(f)
        for row in r:
            mode = (row.get("scenario_type") or "").strip()
            if mode not in out:
                continue
            out[mode]["path_change_count"].append(_to_float(row.get("path_change_count", "")))
            out[mode]["hop_count_variation"].append(_to_float(row.get("hop_count_variation", "")))
            out[mode]["hop_count_ratio"].append(_to_float(row.get("hop_count_ratio", "")))
    return out


def _plot_mode(mode, datasets, out_prefix, title, title_suffix):
    """
    datasets:
      {
        "Kuiper K1": {"path_change_count":[...], ...},
        "Telesat T1": {...},
        "Starlink S1": {...},
      }
    """
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), sharey=True)
    panel_specs = [
        ("(a) Distribution of path changes.", "path_change_count", "# of path changes"),
        ("(b) Distribution of path hop-count differences.", "hop_count_variation", "Max. hop count - Min. hop count (# hops)"),
        ("(c) Distribution of max hop-count / min hop-count.", "hop_count_ratio", "Max. hop count / Min. hop count"),
    ]
    styles = {
        "Kuiper K1": dict(color="#1f77b4", lw=2.2, linestyle="-"),
        "Telesat T1": dict(color="#2ca02c", lw=2.0, linestyle=":"),
        "Starlink S1": dict(color="#ff7f0e", lw=2.0, linestyle=(0, (4, 4))),
    }

    for i, (panel_title, metric_key, xlabel) in enumerate(panel_specs):
        ax = axes[i]
        for name in ["Telesat T1", "Kuiper K1", "Starlink S1"]:
            vals = datasets.get(name, {}).get(metric_key, [])
            x, y = _ecdf(vals)
            if not x:
                continue
            ax.plot(x, y, label=name, **styles[name])
        ax.set_title(panel_title, fontsize=11)
        ax.set_xlabel(xlabel)
        if i == 0:
            ax.set_ylabel("ECDF (pairs)")
        ax.set_ylim(0.0, 1.02)
        ax.grid(True, linestyle=":", alpha=0.6)
        if i == 2:
            ax.legend(loc="lower right")

    fig.suptitle("%s%s (%s)" % (title, title_suffix, mode.replace("_", "-")), fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.95])

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
    parser = argparse.ArgumentParser(
        description="Plot Figure F path dynamics for Kuiper (+ optional Telesat/Starlink)."
    )
    parser.add_argument(
        "--kuiper-csv",
        default=DEFAULT_KUIPER_METRICS,
        help="Kuiper metrics CSV (default: multilayer_all_experiments_metrics.csv).",
    )
    parser.add_argument(
        "--telesat-csv",
        default="",
        help="Optional Telesat CSV with columns: scenario_type,path_change_count,hop_count_variation,hop_count_ratio",
    )
    parser.add_argument(
        "--starlink-csv",
        default="",
        help="Optional Starlink CSV with columns: scenario_type,path_change_count,hop_count_variation,hop_count_ratio",
    )
    parser.add_argument(
        "--leo-out-prefix",
        default=os.path.join(FIGURE_DIR, "figure_f_path_dynamics_leo_only"),
        help="Output prefix for LEO-only figure.",
    )
    parser.add_argument(
        "--ml-out-prefix",
        default=os.path.join(FIGURE_DIR, "figure_f_path_dynamics_multilayer"),
        help="Output prefix for Multilayer figure.",
    )
    parser.add_argument(
        "--duration-s",
        type=int,
        default=simulation_end_time_s,
        help="Simulation length for figure annotation (metrics CSV should match). Default: run_list.",
    )
    parser.add_argument(
        "--time-step-ms",
        type=int,
        default=dynamic_state_update_interval_ms,
        help="Dynamic state interval for figure annotation. Default: run_list.",
    )
    args = parser.parse_args()

    n_fstate = _expected_fstate_file_count(args.duration_s, args.time_step_ms)
    print(
        "Figure F: annotated for %d s sim, %d ms state updates; forwarding-state files ≈ %d "
        "(regenerate multilayer_all_experiments_metrics.csv from matching runs)."
        % (args.duration_s, args.time_step_ms, n_fstate)
    )
    title_suffix = " — %d s sim, %d ms state updates" % (args.duration_s, args.time_step_ms)

    kuiper = _read_kuiper_metrics(args.kuiper_csv)
    telesat = _read_external_constellation(args.telesat_csv, "Telesat")
    starlink = _read_external_constellation(args.starlink_csv, "Starlink")

    leo_datasets = {
        "Kuiper K1": kuiper["leo_only"],
        "Telesat T1": telesat["leo_only"],
        "Starlink S1": starlink["leo_only"],
    }
    ml_datasets = {
        "Kuiper K1": kuiper["multilayer"],
        "Telesat T1": telesat["multilayer"],
        "Starlink S1": starlink["multilayer"],
    }

    _plot_mode(
        "leo_only",
        leo_datasets,
        args.leo_out_prefix,
        "Figure F — Path structure changes across pairs",
        title_suffix,
    )
    _plot_mode(
        "multilayer",
        ml_datasets,
        args.ml_out_prefix,
        "Figure F — Path structure changes across pairs",
        title_suffix,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3
"""
Figure H — Multilayer vs LEO-only scorecard

Goal:
  Provide a clear, thesis-friendly comparison to justify multilayer benefits
  against LEO-only for Kuiper experiment-1 pairs.

Panels (2x2):
  (a) Avg hop count (lower is better)
  (b) Bottleneck utilization (lower is better)
  (c) RTT stretch max/geodesic (lower is better); CD output uses per-pair TCP-sample histograms.
  (d) Path stability ratio (higher is better); CD output uses per-snapshot 0/1 histograms (CSV fallback if no fstate).

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
import matplotlib.gridspec as gridspec
import numpy as np

from evaluation_utils import _resolve_run_dir, extract_path_stability_binary_samples


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
                "rn_leo": rn_leo,
                "rn_ml": rn_ml,
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


def _run_dir_candidates(run_name):
    return [
        os.path.join(SCRIPT_DIR, "data", run_name),
        os.path.join(SCRIPT_DIR, "runs", run_name),
    ]


def _rtt_stretch_samples_for_run(run_name, t_max_s, metrics_by_run):
    """Per-sample RTT stretch (rtt_ms / min rtt in window), same as Figure U / D."""
    rtt_path = None
    for rd in _run_dir_candidates(run_name):
        if not os.path.isdir(rd):
            continue
        resolved = None
        try:
            from evaluation_utils import _resolve_run_dir

            resolved = _resolve_run_dir(rd, None)
        except Exception:
            resolved = rd
        for cand in (
            os.path.join(resolved, "tcp_flow_0_rtt.csv"),
            os.path.join(resolved, "logs_ns3", "tcp_flow_0_rtt.csv"),
        ):
            if os.path.isfile(cand):
                rtt_path = cand
                break
        if rtt_path:
            break

    samples_ms = []
    if rtt_path:
        with open(rtt_path, "r") as f:
            for row in csv.reader(f):
                if len(row) < 3:
                    continue
                try:
                    t_ns = float(row[1])
                    rtt_ns = float(row[2])
                except ValueError:
                    continue
                if t_max_s is None or t_max_s <= 0 or (t_ns / 1e9) <= float(t_max_s):
                    samples_ms.append(rtt_ns / 1e6)
        if samples_ms:
            mn = min(samples_ms)
            if mn > 0:
                return [x / mn for x in samples_ms]

    row = metrics_by_run.get(run_name)
    if row:
        v = _to_float(row.get("rtt_stretch"))
        if v == v:
            return [v]
    return []


def _path_stability_samples_for_run(run_name, fallback_scalar):
    for rd in _run_dir_candidates(run_name):
        if os.path.isdir(rd):
            s = extract_path_stability_binary_samples(rd, None)
            if s:
                return s
    if fallback_scalar == fallback_scalar:
        return [fallback_scalar]
    return []


def _hist_leo_ml_on_ax(ax, leo_vals, ml_vals, subtitle, xlabel, lower_better, discrete_01=False):
    leo_a = np.asarray([x for x in leo_vals if x == x], dtype=float)
    ml_a = np.asarray([x for x in ml_vals if x == x], dtype=float)
    if leo_a.size == 0 and ml_a.size == 0:
        ax.text(0.5, 0.5, "no data", ha="center", va="center", transform=ax.transAxes, fontsize=8)
        ax.set_title(subtitle, fontsize=9)
        return

    if discrete_01:
        bins = [0, 1, 2]
        rtt_range = None
    else:
        flat = np.concatenate([a for a in (leo_a, ml_a) if a.size > 0])
        hi = float(np.clip(np.max(flat) * 1.06, 0.08, 50.0))
        bins = 28
        rtt_range = (0.0, hi)

    kwargs = dict(alpha=0.52, edgecolor="white", linewidth=0.35)
    if rtt_range is not None:
        ax.hist(
            leo_a,
            bins=bins,
            range=rtt_range,
            label="LEO-only",
            color="#1f77b4",
            **kwargs,
        )
        ax.hist(ml_a, bins=bins, range=rtt_range, label="Multilayer", color="#2ca02c", **kwargs)
        ax.set_xlim(rtt_range[0], rtt_range[1])
    else:
        ax.hist(leo_a, bins=bins, label="LEO-only", color="#1f77b4", **kwargs)
        ax.hist(ml_a, bins=bins, label="Multilayer", color="#2ca02c", **kwargs)
        ax.set_xlim(-0.05, 1.05)

    ax.set_title(subtitle, fontsize=8.5, rotation=14, ha="right")
    ax.set_xlabel(xlabel, fontsize=8)
    ax.set_ylabel("Count", fontsize=8)
    ax.grid(True, axis="y", linestyle=":", alpha=0.55)
    note = "lower better" if lower_better else "higher better"
    ax.text(0.02, 0.96, note, transform=ax.transAxes, fontsize=7, va="top")


def _save_cd_histogram_figure(pairs, metrics_by_run, t_max_s, out_prefix):
    """
    (c) and (d) as two columns; each column is a row of three histograms (one per city pair),
    LEO vs multilayer overlaid per subplot.
    """
    n = len(pairs)
    fig = plt.figure(figsize=(14.0, 4.6), layout="constrained")
    outer = gridspec.GridSpec(1, 2, figure=fig, width_ratios=[1.0, 1.0], wspace=0.22)
    gs_c = gridspec.GridSpecFromSubplotSpec(1, n, subplot_spec=outer[0], wspace=0.32)
    gs_d = gridspec.GridSpecFromSubplotSpec(1, n, subplot_spec=outer[1], wspace=0.32)

    axes_c = [fig.add_subplot(gs_c[0, i]) for i in range(n)]
    axes_d = [fig.add_subplot(gs_d[0, i]) for i in range(n)]

    for i, p in enumerate(pairs):
        rl = _rtt_stretch_samples_for_run(p["rn_leo"], t_max_s, metrics_by_run)
        rm = _rtt_stretch_samples_for_run(p["rn_ml"], t_max_s, metrics_by_run)
        if not rl and p["leo"]["rtt_stretch"] == p["leo"]["rtt_stretch"]:
            rl = [p["leo"]["rtt_stretch"]]
        if not rm and p["ml"]["rtt_stretch"] == p["ml"]["rtt_stretch"]:
            rm = [p["ml"]["rtt_stretch"]]

        sl = _path_stability_samples_for_run(p["rn_leo"], p["leo"]["path_stability_ratio"])
        sm = _path_stability_samples_for_run(p["rn_ml"], p["ml"]["path_stability_ratio"])

        pair_lab = p["pair"].replace(" to ", "\n")
        _hist_leo_ml_on_ax(
            axes_c[i],
            rl,
            rm,
            pair_lab,
            "RTT stretch (×)",
            lower_better=True,
            discrete_01=False,
        )
        _hist_leo_ml_on_ax(
            axes_d[i],
            sl,
            sm,
            pair_lab,
            "Stable (1) / changed (0)",
            lower_better=False,
            discrete_01=True,
        )

    fig.text(0.27, 0.99, "(c) RTT stretch (max/geodesic)", ha="center", va="top", fontsize=11)
    fig.text(0.73, 0.99, "(d) Path stability ratio", ha="center", va="top", fontsize=11)
    leg_kw = dict(loc="upper right", fontsize=7.5, framealpha=0.92)
    axes_c[0].legend(**leg_kw)
    axes_d[0].legend(**leg_kw)

    out_png = out_prefix + ".png"
    out_pdf = out_prefix + ".pdf"
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(out_pdf)), exist_ok=True)
    fig.savefig(out_png, dpi=220)
    fig.savefig(out_pdf)
    plt.close(fig)
    print("Wrote:", out_png)
    print("Wrote:", out_pdf)


def _save_two_panel_figure(pairs, panel_specs, out_prefix):
    """
    panel_specs: list of tuples (key, title, lower_better), length 2
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for i, (key, title, lower_better) in enumerate(panel_specs):
        _panel(axes[i], pairs, key, title, lower_better=lower_better)
    axes[0].legend(loc="upper right")
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
    if not os.path.isfile(args.metrics_csv):
        print("ERROR: missing metrics CSV:", args.metrics_csv)
        return 1

    rows = _load_rows(args.metrics_csv)
    pairs = _collect_pairwise(rows)
    if not pairs:
        print("ERROR: no experiment-1 pair rows found in", args.metrics_csv)
        return 1

    _save_two_panel_figure(
        pairs,
        [
            ("avg_hop_count", "(a) Avg hop count", True),
            ("bottleneck_utilization", "(b) Bottleneck utilization", True),
        ],
        args.out_prefix + "_ab",
    )
    _save_cd_histogram_figure(pairs, rows, args.duration_s, args.out_prefix + "_cd")
    return 0


if __name__ == "__main__":
    sys.exit(main())


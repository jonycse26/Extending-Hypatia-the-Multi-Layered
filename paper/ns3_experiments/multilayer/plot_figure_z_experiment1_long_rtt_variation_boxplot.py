#!/usr/bin/env python3
"""
Figure Z — Experiment 1: RTT variation (ms) box plots for **all three** city pairs

For each pair (Mumbai–Lima, Lima–Karachi, Tokyo–Buenos-Aires), **grouped** LEO-only vs multilayer.

The **box** uses **local** variation: ``max − min`` RTT inside each **sliding window** of TCP samples
(``tcp_flow_0_rtt.csv``). That differs from ``rtt_variation_ms`` in ``multilayer_all_experiments_metrics.csv``,
which is **global** max − min over the **entire** trace — shown as **diamond** markers when available.

Output: ``figure-z experiment1 long rtt variation/figure_z_experiment1_long_rtt_variation_ms.{png,pdf}``.
"""

import argparse
import csv
import os
import sys
import warnings

import matplotlib

warnings.filterwarnings("ignore", message="Unable to import Axes3D.*", category=UserWarning)

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import matplotlib.patches as mpatches
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURE_DIR = os.path.join(SCRIPT_DIR, "figure-z experiment1 long rtt variation")
DEFAULT_METRICS_CSV = os.path.join(SCRIPT_DIR, "multilayer_all_experiments_metrics.csv")
sys.path.insert(0, SCRIPT_DIR)

try:
    from run_list import experiment1_pairs_leo, experiment1_pairs_multilayer, simulation_end_time_s
except Exception as e:
    raise RuntimeError("Could not import run_list: %s" % e)

from evaluation_utils import _resolve_run_dir

COLOR_LEO = "#1f77b4"
COLOR_ML = "#2ca02c"
GROUP_SPACING = 2.55
PAIR_DODGE = 0.3
BOX_WIDTH = 0.38
CSV_TRACE_LEGEND_LABEL = "CSV: full-trace max−min"


def rtt_variation_legend_handles():
    """Legend entries for LEO-only, Multilayer, and full-trace CSV (use with ``fig.legend`` / subfigure legend)."""
    leg_box_leo = mpatches.Patch(facecolor=COLOR_LEO, edgecolor="#222222", linewidth=0.6, label="LEO-only (windowed)")
    leg_box_ml = mpatches.Patch(facecolor=COLOR_ML, edgecolor="#222222", linewidth=0.6, label="Multilayer (windowed)")
    leg_csv = mlines.Line2D(
        [],
        [],
        color="none",
        marker="D",
        markerfacecolor="white",
        markeredgecolor="#333333",
        markersize=7,
        markeredgewidth=1.2,
        label=CSV_TRACE_LEGEND_LABEL,
    )
    return [leg_box_leo, leg_box_ml, leg_csv]


def _to_float(v):
    try:
        if v is None or (isinstance(v, str) and not str(v).strip()):
            return float("nan")
        return float(v)
    except Exception:
        return float("nan")


def _load_metrics_by_run(csv_path):
    if not os.path.isfile(csv_path):
        return {}
    out = {}
    with open(csv_path, "r") as f:
        for r in csv.DictReader(f):
            rn = (r.get("run_name") or "").strip()
            if rn:
                out[rn] = r
    return out


def _run_dir_candidates(run_name):
    return [
        os.path.join(SCRIPT_DIR, "data", run_name),
        os.path.join(SCRIPT_DIR, "runs", run_name),
    ]


def _read_rtt_ms_ordered(run_name, t_max_s):
    t_max = float(t_max_s) if t_max_s is not None and t_max_s > 0 else None
    for rd in _run_dir_candidates(run_name):
        if not os.path.isdir(rd):
            continue
        try:
            resolved = _resolve_run_dir(rd, None)
        except Exception:
            resolved = rd
        tcp_candidates = (
            os.path.join(resolved, "tcp_flow_0_rtt.csv"),
            os.path.join(resolved, "logs_ns3", "tcp_flow_0_rtt.csv"),
        )
        for tcp_path in tcp_candidates:
            if not os.path.isfile(tcp_path):
                continue
            out = []
            with open(tcp_path, "r") as f:
                for row in csv.reader(f):
                    if len(row) < 3:
                        continue
                    try:
                        t_ns = float(row[1])
                        rtt_ns = float(row[2])
                    except ValueError:
                        continue
                    if t_max is None or (t_ns / 1e9) <= t_max:
                        out.append(rtt_ns / 1e6)
            if out:
                return out

        comp = os.path.join(resolved, "computed_rtt_ms_ts.csv")
        if os.path.isfile(comp):
            out = []
            with open(comp, "r") as f:
                for row in csv.reader(f):
                    if len(row) < 2:
                        continue
                    try:
                        t_s = float(row[0]) / 1e9
                        rtt_ms = float(row[1])
                    except ValueError:
                        continue
                    if t_max is None or t_s <= t_max:
                        out.append(rtt_ms)
            if out:
                return out
    return []


def _sliding_variation_ms(rtt_ms, window, step):
    n = len(rtt_ms)
    if n < 4:
        return []
    w = int(window)
    s = int(step)
    w = max(4, min(w, n))
    s = max(1, min(s, w))
    out = []
    i = 0
    while i + w <= n:
        seg = rtt_ms[i : i + w]
        out.append(float(max(seg) - min(seg)))
        i += s
    return out


def _variation_samples_for_run(run_name, t_max_s, metrics_by_run, window, step):
    series = _read_rtt_ms_ordered(run_name, t_max_s)
    if len(series) >= 8:
        w_eff = min(int(window), max(4, len(series) // 2))
        s_eff = max(1, min(int(step), w_eff))
        v = _sliding_variation_ms(series, w_eff, s_eff)
        if v:
            return v
    row = metrics_by_run.get(run_name)
    if row:
        x = _to_float(row.get("rtt_variation_ms"))
        if x == x:
            return [x]
    return []


def _short_xlabel(desc):
    """City pair on three lines: origin, ``to`` (middle), destination — for ticks at top of axes."""
    if " to " in desc:
        left, right = desc.split(" to ", 1)
        return "%s\nto\n%s" % (left.strip(), right.strip())
    return desc


def _collect_all_pairs(metrics, t_max, window, step):
    rows = []
    for (f_leo, t_leo, desc), (f_ml, t_ml, _) in zip(experiment1_pairs_leo, experiment1_pairs_multilayer):
        rn_leo = "leo_only_%d_to_%d_tcp" % (f_leo, t_leo)
        rn_ml = "multilayer_%d_to_%d_tcp" % (f_ml, t_ml)
        s_leo = _variation_samples_for_run(rn_leo, t_max, metrics, window, step)
        s_ml = _variation_samples_for_run(rn_ml, t_max, metrics, window, step)
        if not s_leo or not s_ml:
            print("WARN: skip pair (missing LEO or ML variation samples):", desc, rn_leo, rn_ml)
            continue
        rows.append(
            {
                "desc": desc,
                "rn_leo": rn_leo,
                "rn_ml": rn_ml,
                "s_leo": np.asarray(s_leo, dtype=float),
                "s_ml": np.asarray(s_ml, dtype=float),
            }
        )
    return rows


def render_rtt_variation_boxplot_on_ax(ax, pairs, metrics):
    """
    Draw grouped boxplots and CSV diamond markers on ``ax``.

    Caller supplies ``pairs`` from :func:`_collect_all_pairs` (non-empty).
    Caller adds a centered title (``fig.text`` / subfigure) and :func:`rtt_variation_legend_handles`
    with ``fig.legend`` (or subfigure transform) for the top-right series key.
    """
    positions = []
    data = []
    for i, p in enumerate(pairs):
        base = i * GROUP_SPACING
        x_leo = base - PAIR_DODGE
        x_ml = base + PAIR_DODGE
        positions.extend([x_leo, x_ml])
        a = p["s_leo"][np.isfinite(p["s_leo"])]
        b = p["s_ml"][np.isfinite(p["s_ml"])]
        data.extend([a, b])

    bp = ax.boxplot(
        data,
        positions=positions,
        widths=BOX_WIDTH,
        patch_artist=True,
        showfliers=True,
        manage_ticks=False,
    )
    for j, patch in enumerate(bp["boxes"]):
        c = COLOR_LEO if j % 2 == 0 else COLOR_ML
        patch.set_facecolor(c)
        patch.set_alpha(0.88)
        patch.set_edgecolor("#222222")
        patch.set_linewidth(0.6)
    for w in bp["whiskers"]:
        w.set_color("#222222")
        w.set_linewidth(0.8)
    for c in bp["caps"]:
        c.set_color("#222222")
        c.set_linewidth(0.8)
    for m in bp["medians"]:
        m.set_color("#222222")
        m.set_linewidth(1.0)

    ymax_data = 0.0
    parts = [d for d in data if d.size > 0]
    if parts:
        ymax_data = float(np.max(np.concatenate(parts)))

    ymax_ref = 0.0
    for i, p in enumerate(pairs):
        base = i * GROUP_SPACING
        x_leo = base - PAIR_DODGE
        x_ml = base + PAIR_DODGE
        row_leo = metrics.get(p["rn_leo"]) or {}
        row_ml = metrics.get(p["rn_ml"]) or {}
        csv_leo = _to_float(row_leo.get("rtt_variation_ms"))
        csv_ml = _to_float(row_ml.get("rtt_variation_ms"))
        if csv_leo == csv_leo:
            ax.scatter(
                [x_leo],
                [csv_leo],
                s=48,
                marker="D",
                facecolors="white",
                edgecolors=COLOR_LEO,
                linewidths=1.3,
                zorder=6,
            )
            ymax_ref = max(ymax_ref, csv_leo)
        if csv_ml == csv_ml:
            ax.scatter(
                [x_ml],
                [csv_ml],
                s=48,
                marker="D",
                facecolors="white",
                edgecolors=COLOR_ML,
                linewidths=1.3,
                zorder=6,
            )
            ymax_ref = max(ymax_ref, csv_ml)

    hi_y = max(ymax_data, ymax_ref, 1.0) * 1.08
    ax.set_ylim(0.0, hi_y)

    tick_x = [i * GROUP_SPACING for i in range(len(pairs))]
    ax.set_xticks(tick_x)
    ax.set_xticklabels([_short_xlabel(p["desc"]) for p in pairs], fontsize=8.5, ha="center", linespacing=0.92)
    ax.tick_params(axis="x", bottom=True, labelbottom=True, top=False, labeltop=False, pad=2)
    for tl in ax.get_xticklabels():
        tl.set_va("top")
    ax.set_ylabel("RTT variation (ms)", fontsize=11)
    ax.grid(True, axis="y", linestyle=":", alpha=0.55)


def main():
    ap = argparse.ArgumentParser(description="Figure Z: experiment-1 RTT variation (ms), all pairs.")
    ap.add_argument("--metrics-csv", default=DEFAULT_METRICS_CSV)
    ap.add_argument(
        "--out-prefix",
        default=None,
        help="Output path without extension.",
    )
    ap.add_argument(
        "--duration-s",
        type=float,
        default=float(simulation_end_time_s),
        help="Clip TCP / computed RTT samples (seconds).",
    )
    ap.add_argument("--window", type=int, default=48, help="Samples per sliding window.")
    ap.add_argument("--step", type=int, default=24, help="Sliding window step (samples).")
    args = ap.parse_args()

    metrics = _load_metrics_by_run(args.metrics_csv)
    t_max = float(args.duration_s)
    pairs = _collect_all_pairs(metrics, t_max, args.window, args.step)
    if not pairs:
        print("ERROR: no pair had both LEO and multilayer variation samples.")
        return 1

    fig, ax = plt.subplots(figsize=(max(7.5, 2.2 + len(pairs) * GROUP_SPACING), 4.5))
    fig.subplots_adjust(left=0.11, right=0.97, top=0.80, bottom=0.22)
    render_rtt_variation_boxplot_on_ax(ax, pairs, metrics)
    fig.text(
        0.5,
        0.99,
        "RTT Variation",
        transform=fig.transFigure,
        ha="center",
        va="top",
        fontsize=11,
    )
    fig.legend(
        handles=rtt_variation_legend_handles(),
        loc="upper right",
        bbox_to_anchor=(0.99, 0.99),
        bbox_transform=fig.transFigure,
        fontsize=7,
        framealpha=0.95,
        borderaxespad=0.25,
    )

    out_prefix = args.out_prefix or os.path.join(FIGURE_DIR, "figure_z_experiment1_long_rtt_variation_ms")
    os.makedirs(os.path.dirname(os.path.abspath(out_prefix)), exist_ok=True)
    png = out_prefix + ".png"
    pdf = out_prefix + ".pdf"
    fig.savefig(png, dpi=220, bbox_inches="tight", pad_inches=0.18)
    fig.savefig(pdf, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)
    print("Figure Z: %d pairs · w=%d step=%d" % (len(pairs), args.window, args.step))
    print("Wrote:", png)
    print("Wrote:", pdf)
    return 0


if __name__ == "__main__":
    sys.exit(main())

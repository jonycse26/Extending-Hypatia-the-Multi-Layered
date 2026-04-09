#!/usr/bin/env python3
"""
Figure B — TCP window vs path capacity (overlay LEO vs Multilayer)

Per experiment-1 pair (three panels):
  - LEO-only CWND / max(CWND)  — dashed
  - Multilayer CWND / max(CWND) — solid
  - LEO-only BDP+Q / max(BDP) — light dash-dot (reference)
  - Multilayer BDP+Q / max(BDP) — light dotted (reference)

Tracking error (raw packets):
  mean(|cwnd − bdp|) with BDP linearly interpolated onto CWND times.
  If bdp_plus_q_packets_ts is the evaluation_utils CWND mirror, this metric is ~0 and only the
  normalized overlay (LEO vs multilayer) is meaningful until a true capacity trace is supplied.

Outputs (default, under ``figure-b cwnd vs bdp/``):

- ``figure_b_cwnd_vs_bdp`` — normalized LEO vs multilayer overlay (three panels).
- ``figure_b_cwnd_vs_bdp_leo_only`` — raw packets: CWND vs BDP+Q for LEO-only runs only.
- ``figure_b_cwnd_vs_bdp_multilayer`` — raw packets for multilayer runs only.

Expects ``data/<run>/`` CWND/BDP CSVs from ns-3 runs using the same simulation length and
dynamic_state interval as ``run_list`` (default: ``simulation_end_time_s=25``,
``dynamic_state_update_interval_ms=1000`` → ``dynamic_state_1000ms_for_25s``).
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
FIGURE_DIR = os.path.join(SCRIPT_DIR, "figure-b cwnd vs bdp")
sys.path.insert(0, SCRIPT_DIR)

try:
    from run_list import (
        dynamic_state_update_interval_ms,
        experiment1_pairs_leo,
        experiment1_pairs_multilayer,
        simulation_end_time_s,
    )
except Exception as e:
    raise RuntimeError("Could not import run_list defaults / experiment1 pairs: %s" % e)


def _clip_series_to_time_s(xs, ys, t_max_s):
    if t_max_s is None or t_max_s <= 0:
        return xs, ys
    out_x, out_y = [], []
    for x, y in zip(xs, ys):
        if x <= t_max_s:
            out_x.append(x)
            out_y.append(y)
    return out_x, out_y


def _clip_panel(panel, t_max_s):
    cx, cy = panel["cwnd"]
    bx, by = panel["bdp"]
    cx, cy = _clip_series_to_time_s(cx, cy, t_max_s)
    bx, by = _clip_series_to_time_s(bx, by, t_max_s)
    out = dict(panel)
    out["cwnd"] = (cx, cy)
    out["bdp"] = (bx, by)
    return out


def _expected_fstate_file_count(duration_s, time_step_ms):
    if duration_s < 0 or time_step_ms <= 0:
        return 0
    return (duration_s * 1000) // time_step_ms + 1


def _read_cwnd_packets_ts(run_name):
    path = os.path.join(SCRIPT_DIR, "data", run_name, "tcp_flow_0_cwnd.csv")
    xs, ys = [], []
    with open(path, "r") as f:
        for row in csv.reader(f):
            if len(row) < 3:
                continue
            try:
                xs.append(float(row[1]) / 1e9)
                ys.append(float(row[2]))
            except ValueError:
                continue
    return xs, ys, path


def _read_bdp_plus_q_packets_ts(run_name):
    path = os.path.join(SCRIPT_DIR, "data", run_name, "bdp_plus_q_packets_ts.csv")
    if not os.path.isfile(path):
        return None, None, path
    xs, ys = [], []
    with open(path, "r") as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            try:
                xs.append(float(row[0]) / 1e9)
                ys.append(float(row[1]))
            except ValueError:
                continue
    return xs, ys, path


def _load_panel(run_name):
    cwnd_x, cwnd_y, cwnd_path = _read_cwnd_packets_ts(run_name)
    if not cwnd_x:
        raise RuntimeError("Empty/missing cwnd: %s" % cwnd_path)
    bdp_x, bdp_y, bdp_path = _read_bdp_plus_q_packets_ts(run_name)
    bdp_label = "bdp_plus_q_packets_ts"
    bdp_is_proxy = False
    if not bdp_x:
        bdp_x = list(cwnd_x)
        bdp_y = list(cwnd_y)
        bdp_label = "bdp_plus_q_packets_ts (proxy=cwnd)"
        bdp_is_proxy = True
        print("WARNING: missing/empty %s; using cwnd proxy." % bdp_path)
    else:
        # Current exported bdp_plus_q often mirrors cwnd; note this explicitly in legend/text.
        if len(bdp_x) == len(cwnd_x) and len(bdp_y) == len(cwnd_y):
            same_x = np.allclose(np.asarray(bdp_x, dtype=float), np.asarray(cwnd_x, dtype=float))
            same_y = np.allclose(np.asarray(bdp_y, dtype=float), np.asarray(cwnd_y, dtype=float))
            if same_x and same_y:
                bdp_is_proxy = True
                bdp_label = "bdp_plus_q_packets_ts (identical to cwnd)"
                print("WARNING: %s is identical to cwnd for %s; lines will overlap." % (os.path.basename(bdp_path), run_name))
    return {
        "cwnd": (cwnd_x, cwnd_y),
        "bdp": (bdp_x, bdp_y),
        "bdp_label": bdp_label,
        "bdp_is_proxy": bdp_is_proxy,
    }


def _normalize01(vals):
    v = np.asarray(vals, dtype=float)
    m = float(np.max(v)) if v.size else 0.0
    if m <= 0:
        return np.zeros_like(v)
    return v / m


def _tracking_error_mean_abs(cwnd_x, cwnd_y, bdp_x, bdp_y):
    """mean(|cwnd − bdp|) with bdp interpolated to cwnd times."""
    if not cwnd_x or not cwnd_y or not bdp_x or not bdp_y:
        return float("nan")
    tx = np.asarray(cwnd_x, dtype=float)
    cy = np.asarray(cwnd_y, dtype=float)
    bx = np.asarray(bdp_x, dtype=float)
    by = np.asarray(bdp_y, dtype=float)
    if bx.size == 0 or by.size == 0:
        return float("nan")
    if bx.size == 1:
        by_i = np.full_like(cy, float(by[0]))
    else:
        by_i = np.interp(tx, bx, by, left=float(by[0]), right=float(by[-1]))
    return float(np.mean(np.abs(cy - by_i)))


def _plot_overlay_panels(triples, title, out_prefix, time_window_s):
    """
    triples: list of (panel_title, leo_panel, ml_panel, leo_te, ml_te)
    """
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2), sharey=True)
    leo_errors = []
    ml_errors = []

    proxy_any = False
    for i, (panel_title, leo_p, ml_p, te_leo, te_ml) in enumerate(triples):
        ax = axes[i]
        leo_errors.append(te_leo)
        ml_errors.append(te_ml)
        if leo_p.get("bdp_is_proxy") or ml_p.get("bdp_is_proxy"):
            proxy_any = True

        lcx, lcy = leo_p["cwnd"]
        lbx, lby = leo_p["bdp"]
        mcx, mcy = ml_p["cwnd"]
        mbx, mby = ml_p["bdp"]

        lcy_n = _normalize01(lcy)
        lby_n = _normalize01(lby)
        mcy_n = _normalize01(mcy)
        mby_n = _normalize01(mby)

        ax.plot(lcx, lcy_n, lw=2.0, ls="--", color="#1f77b4", label="LEO-only CWND / max", zorder=3)
        ax.plot(mcx, mcy_n, lw=2.2, ls="-", color="#2ca02c", label="Multilayer CWND / max", zorder=4)
        # BDP+Q reference: darker hues + thicker + high alpha so dash-dot / dotted read on grid/PDF.
        ax.plot(
            lbx,
            lby_n,
            lw=2.2,
            ls="-.",
            color="#0d3d6b",
            alpha=0.92,
            label="LEO-only BDP+Q / max",
            zorder=2.5,
        )
        ax.plot(
            mbx,
            mby_n,
            lw=2.2,
            ls=":",
            color="#1b5e20",
            alpha=0.92,
            label="Multilayer BDP+Q / max",
            zorder=2.5,
        )

        ax.set_title(panel_title, fontsize=11)
        ax.set_xlabel("Time (s)")
        ax.set_xlim(0.0, float(time_window_s))
        ax.grid(True, alpha=0.3)
        ax.set_ylim(-0.03, 1.08)

        # LEO-only callout: bottom-right. Multilayer: top-right (avoids overlap).
        ax.text(
            0.98,
            0.02,
            "LEO-only:\nCWND overshoot →\ncollapse risk",
            transform=ax.transAxes,
            fontsize=7.5,
            ha="right",
            va="bottom",
            color="#1f77b4",
            linespacing=1.15,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#1f77b4", alpha=0.85),
        )
        ax.text(
            0.98,
            0.98,
            "Multilayer:\nCWND follows\ncapacity",
            transform=ax.transAxes,
            fontsize=7.5,
            ha="right",
            va="top",
            color="#2ca02c",
            linespacing=1.15,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#2ca02c", alpha=0.85),
        )

    axes[0].set_ylabel("Normalized (0–1)", fontsize=11)
    handles, labels = axes[2].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, fontsize=8, frameon=True, bbox_to_anchor=(0.5, 1.02))

    mean_leo = float(np.nanmean(np.asarray(leo_errors, dtype=float))) if leo_errors else float("nan")
    mean_ml = float(np.nanmean(np.asarray(ml_errors, dtype=float))) if ml_errors else float("nan")

    sub = title
    if proxy_any:
        sub += (
            "\nNote: BDP+Q missing for some runs (cwnd fallback) — |cwnd−bdp| can be 0 by construction."
        )
    elif mean_leo == mean_leo and mean_ml == mean_ml and mean_leo < 1e-9 and mean_ml < 1e-9:
        sub += (
            "\nNote: bdp_plus_q_packets_ts mirrors CWND in evaluation_utils; "
            "use an independent BDP+Q (BDP+queue) estimate for a non-degenerate tracking metric."
        )
    fig.suptitle(sub, fontsize=10, y=1.1)
    fig.tight_layout(rect=[0, 0, 1, 0.82])
    for ax in axes:
        ax.set_xlim(0.0, float(time_window_s))

    out_png = out_prefix + ".png"
    out_pdf = out_prefix + ".pdf"
    csv_path = out_prefix + "_tracking_error.csv"
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)

    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)
    print("Wrote:", out_png)
    print("Wrote:", out_pdf)

    with open(csv_path, "w", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(
            [
                "pair",
                "cwnd_tracking_error_leo_only",
                "cwnd_tracking_error_multilayer",
                "bdp_proxy_leo",
                "bdp_proxy_ml",
            ]
        )
        for (panel_title, leo, ml, te_l, te_m) in triples:
            w.writerow(
                [
                    panel_title,
                    te_l,
                    te_m,
                    leo.get("bdp_is_proxy", False),
                    ml.get("bdp_is_proxy", False),
                ]
            )
        w.writerow([])
        w.writerow(["mean_over_pairs", mean_leo, mean_ml, "", ""])
    print("Wrote:", csv_path)


def _plot_raw_cwnd_bdp_panels(pair_rows, figure_title, out_prefix, time_window_s):
    """
    Three panels, one constellation: raw cwnd vs bdp_plus_q in packets (not normalized).

    pair_rows: list of (panel_title, panel) with panel from _load_panel / _clip_panel.
    """
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2), sharey=True)
    data_t_max = 0.0

    for i, (panel_title, p) in enumerate(pair_rows):
        ax = axes[i]
        cx, cy = p["cwnd"]
        bx, by = p["bdp"]
        for xv in (cx, bx):
            if xv:
                data_t_max = max(data_t_max, max(xv))

        ax.plot(cx, cy, lw=2.0, ls="-", color="#2ca02c", label="cwnd_packets_ts", zorder=3)
        # Draw BDP+Q with sparse markers so it remains visible even when identical to CWND.
        ax.plot(
            bx,
            by,
            lw=2.0,
            ls="--",
            color="#0d3d6b",
            marker="o",
            markersize=2.3,
            markevery=max(1, len(bx) // 45) if bx else 1,
            alpha=0.95,
            label=p.get("bdp_label", "bdp_plus_q_packets_ts"),
            zorder=4,
        )
        ax.set_title(panel_title, fontsize=11)
        ax.set_xlabel("Time (s)")
        ax.set_xlim(0.0, float(time_window_s))
        ax.grid(True, alpha=0.3)
        if p.get("bdp_is_proxy", False):
            ax.text(
                0.98,
                0.98,
                "BDP+Q overlaps CWND\n(proxy/identical series)",
                transform=ax.transAxes,
                ha="right",
                va="top",
                fontsize=7.2,
                color="#0d3d6b",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#0d3d6b", alpha=0.85),
            )

    axes[0].set_ylabel("Packets", fontsize=11)
    handles, labels = axes[2].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, fontsize=8, frameon=True, bbox_to_anchor=(0.5, 1.02))

    fig.suptitle(figure_title, fontsize=12, y=1.08)
    fig.tight_layout(rect=[0, 0, 1, 0.88])
    for ax in axes:
        ax.set_xlim(0.0, float(time_window_s))

    if data_t_max + 0.05 < float(time_window_s):
        print(
            "WARNING (%s): latest sample t≈%.3f s < x-axis end %.0f s — CSVs may be from a shorter sim."
            % (os.path.basename(out_prefix), data_t_max, float(time_window_s))
        )

    out_png = out_prefix + ".png"
    out_pdf = out_prefix + ".pdf"
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)
    print("Wrote:", out_png)
    print("Wrote:", out_pdf)


def main():
    parser = argparse.ArgumentParser(description="Plot Figure B (overlay LEO vs Multilayer cwnd vs BDP+Q).")
    parser.add_argument(
        "--duration-s",
        type=int,
        default=simulation_end_time_s,
        help="Simulation window: clip series and set x-axis [0, duration_s]. Default: run_list.simulation_end_time_s.",
    )
    parser.add_argument(
        "--time-step-ms",
        type=int,
        default=dynamic_state_update_interval_ms,
        help="Dynamic state interval (annotation + fstate count print). Default: run_list.dynamic_state_update_interval_ms.",
    )
    parser.add_argument(
        "--out-prefix",
        default=os.path.join(FIGURE_DIR, "figure_b_cwnd_vs_bdp"),
        help="Output prefix for the combined normalized figure.",
    )
    parser.add_argument(
        "--combined-only",
        action="store_true",
        help="Only write the combined overlay; skip LEO-only and Multilayer raw packet figures.",
    )
    args = parser.parse_args()

    n_fstate = _expected_fstate_file_count(args.duration_s, args.time_step_ms)
    print(
        "Figure B: x-axis [0, %d] s; forwarding-state files ≈ %d (duration_s×1000/time_step_ms + 1)"
        % (args.duration_s, n_fstate)
    )
    title_suffix = " — %d s sim, %d ms state updates" % (args.duration_s, args.time_step_ms)

    triples = []
    leo_only_rows = []
    multilayer_rows = []
    try:
        for i, ((f_leo, t_leo, desc), (f_ml, t_ml, _)) in enumerate(
            zip(experiment1_pairs_leo, experiment1_pairs_multilayer)
        ):
            run_leo = "leo_only_%d_to_%d_tcp" % (f_leo, t_leo)
            run_ml = "multilayer_%d_to_%d_tcp" % (f_ml, t_ml)
            leo_p = _clip_panel(_load_panel(run_leo), args.duration_s)
            ml_p = _clip_panel(_load_panel(run_ml), args.duration_s)
            lcx, lcy = leo_p["cwnd"]
            lbx, lby = leo_p["bdp"]
            mcx, mcy = ml_p["cwnd"]
            mbx, mby = ml_p["bdp"]
            te_l = _tracking_error_mean_abs(lcx, lcy, lbx, lby)
            te_m = _tracking_error_mean_abs(mcx, mcy, mbx, mby)
            panel_title = "(%s) %s" % (chr(ord("a") + i), desc)
            triples.append((panel_title, leo_p, ml_p, te_l, te_m))
            leo_only_rows.append((panel_title, leo_p))
            multilayer_rows.append((panel_title, ml_p))
    except Exception as e:
        print("ERROR:", str(e))
        return 1

    _plot_overlay_panels(
        triples,
        "Figure B — Normalized CWND vs BDP+Q reference (LEO dashed vs Multilayer solid)" + title_suffix,
        args.out_prefix,
        args.duration_s,
    )

    if not args.combined_only:
        _plot_raw_cwnd_bdp_panels(
            leo_only_rows,
            "Figure B — TCP window vs path capacity (LEO-only)" + title_suffix,
            os.path.join(FIGURE_DIR, "figure_b_cwnd_vs_bdp_leo_only"),
            args.duration_s,
        )
        _plot_raw_cwnd_bdp_panels(
            multilayer_rows,
            "Figure B — TCP window vs path capacity (Multilayer)" + title_suffix,
            os.path.join(FIGURE_DIR, "figure_b_cwnd_vs_bdp_multilayer"),
            args.duration_s,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())

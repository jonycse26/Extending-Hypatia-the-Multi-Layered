#!/usr/bin/env python3
"""
Figure B — TCP congestion window evolution (Hypatia paper Fig. 4 style)

Three panels, each showing:
  - **CWND** (orange step line) — ``tcp_flow_0_cwnd.csv`` in packets (bytes / MSS)
  - **BDP+Q** (blue step line) — ``RTT × bandwidth / MSS + Q`` from ``tcp_flow_0_rtt.csv``


MSS = 1380 B, 10 Mbps, Q = 100 packets (Hypatia ``paper/figures/a_b/tcp_cwnd/``).

Outputs (``figure-b cwnd vs bdp/``):
  - ``figure_b_cwnd_vs_bdp_leo_only`` — LEO-only runs
  - ``figure_b_cwnd_vs_bdp_multilayer`` — multilayer runs (default single figure)
  - ``figure_b_cwnd_vs_bdp_both`` — LEO vs multilayer overlaid (experiment1)
"""

import argparse
import csv
import os
import shutil
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
        experiment3_distance_tiers,
        experiment3_pairs_leo,
        experiment3_pairs_multilayer,
        simulation_end_time_s,
    )
except Exception as e:
    raise RuntimeError("Could not import run_list: %s" % e)

TCP_MSS_BYTES = 1380.0
TCP_LINK_BPS = 10.0e6
TCP_BYTES_PER_S = TCP_LINK_BPS / 8.0
QUEUE_PACKETS = 100.0

COLOR_BDP = "#2177b0"
COLOR_CWND = "#fc7f2b"
COLOR_LEO = "#1f77b4"
COLOR_MULTILAYER = "#2ca02c"

PANEL_ORDER = ("long", "short", "medium")
EXAMPLE3_CITY_TITLES = {
    "long": "Rio de Janeiro to St. Petersburg",
    "short": "Manila to Dalian",
    "medium": "Istanbul to Nairobi",
}


def _run_dir_candidates(run_name):
    base = SCRIPT_DIR
    return [
        os.path.join(base, "data", run_name),
        os.path.join(base, "runs", run_name),
        os.path.join(base, "runs", run_name, "logs_ns3"),
    ]


def _clip_series_to_time_s(xs, ys, t_max_s):
    if t_max_s is None or t_max_s <= 0:
        return xs, ys
    out_x, out_y = [], []
    for x, y in zip(xs, ys):
        if x <= t_max_s:
            out_x.append(x)
            out_y.append(y)
    return out_x, out_y


def _read_tcp_flow_csv(run_name, kind):
    """Read tcp_flow_0_{cwnd,rtt}.csv from data/ or runs/."""
    fname = "tcp_flow_0_%s.csv" % kind
    best_path, best_xs, best_ys, best_tmax = None, [], [], -1.0
    for rd in _run_dir_candidates(run_name):
        path = os.path.join(rd, fname)
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            continue
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
        if xs and max(xs) > best_tmax:
            best_tmax = max(xs)
            best_xs, best_ys, best_path = xs, ys, path
    return best_xs, best_ys, best_path


def _cwnd_bytes_to_packets(raw_values):
    v = np.asarray(raw_values, dtype=float)
    if v.size == 0:
        return v
    if float(np.max(v)) > 5000.0:
        return v / TCP_MSS_BYTES
    return v


def _bdp_plus_q_packets_from_rtt_ns(rtt_ns, queue_packets=QUEUE_PACKETS):
    rtt_s = float(rtt_ns) / 1e9
    return rtt_s * TCP_BYTES_PER_S / TCP_MSS_BYTES + float(queue_packets)


def _load_panel(run_name, queue_packets=QUEUE_PACKETS):
    cwnd_x, cwnd_raw, cwnd_path = _read_tcp_flow_csv(run_name, "cwnd")
    if not cwnd_x:
        raise RuntimeError("Empty/missing cwnd: %s" % cwnd_path)

    cwnd_y = _cwnd_bytes_to_packets(cwnd_raw).tolist()

    rtt_x, rtt_ns, rtt_path = _read_tcp_flow_csv(run_name, "rtt")
    if not rtt_x:
        raise RuntimeError("Empty/missing RTT for BDP+Q: %s" % rtt_path)

    bdp_y = [_bdp_plus_q_packets_from_rtt_ns(r, queue_packets) for r in rtt_ns]
    return {"cwnd": (cwnd_x, cwnd_y), "bdp": (rtt_x, bdp_y)}


def _clip_panel(panel, t_max_s):
    cx, cy = _clip_series_to_time_s(*panel["cwnd"], t_max_s)
    bx, by = _clip_series_to_time_s(*panel["bdp"], t_max_s)
    return {"cwnd": (cx, cy), "bdp": (bx, by)}


def _experiment1_panels(constellation):
    pairs = experiment1_pairs_leo if constellation == "leo" else experiment1_pairs_multilayer
    prefix = "leo_only" if constellation == "leo" else "multilayer"
    rows = []
    for i, (from_id, to_id, desc) in enumerate(pairs):
        title = "(%s) %s" % (chr(ord("a") + i), desc)
        run_name = "%s_%d_to_%d_tcp" % (prefix, from_id, to_id)
        rows.append((title, run_name))
    return rows


def _example3_panels(leo_only):
    pairs = experiment3_pairs_leo if leo_only else experiment3_pairs_multilayer
    tier_map = dict(zip(experiment3_distance_tiers, pairs))
    rows = []
    for i, tier in enumerate(PANEL_ORDER):
        from_id, to_id, _desc = tier_map[tier]
        title = "(%s) %s" % (chr(ord("a") + i), EXAMPLE3_CITY_TITLES[tier])
        run_name = "example3_distance_%s_%d_to_%d_tcp" % (tier, from_id, to_id)
        rows.append((title, run_name))
    return rows


def _step_value_at(xs, ys, t):
    if not xs:
        return 0.0
    val = float(ys[0])
    for x, y in zip(xs, ys):
        if x <= t:
            val = float(y)
        else:
            break
    return val


def _cwnd_label_anchor(cx, cy, t_win):
    """Place CWND label after the slow-start peak, on the post-congestion trace."""
    peak_y, peak_t = 0.0, 0.0
    for x, y in zip(cx, cy):
        if x <= 0.65 * t_win and y >= peak_y:
            peak_y, peak_t = float(x), float(y)

    settle_t = peak_t + max(0.5, 0.02 * t_win)
    if peak_y > 0.0:
        for x, y in zip(cx, cy):
            if x > peak_t and y < peak_y * 0.88:
                settle_t = float(x)
                break

    t_label = settle_t + max(2.0, 0.12 * t_win)
    t_label = min(max(t_label, 0.20 * t_win), 0.55 * t_win)
    return t_label, _step_value_at(cx, cy, t_label)


def _add_cwnd_bdp_line_labels(ax, bx, by, cx, cy, time_window_s, ymax=None):
    """Hypatia Fig. 4 style: colored text on the plot near each curve."""
    t_win = float(time_window_s)
    label_z = 10

    peak_t, peak_y = 0.0, 0.0
    for x, y in zip(cx, cy):
        if x <= t_win * 0.7 and y >= peak_y:
            peak_t, peak_y = float(x), float(y)

    if peak_y <= 0.0:
        peak_t = t_win * 0.12

    t_bdp = min(max(peak_t * 1.15 + 0.25, t_win * 0.05), t_win * 0.45)
    y_bdp = _step_value_at(bx, by, t_bdp)
    y_bdp += max(6.0, 0.03 * max(y_bdp, 1.0))

    t_cwnd, y_cwnd = _cwnd_label_anchor(cx, cy, t_win)
    y_bdp_at = _step_value_at(bx, by, t_cwnd)
    gap = y_bdp_at - y_cwnd
    if gap > 80.0:
        y_cwnd_label = y_cwnd + min(gap * 0.14, (ymax or gap) * 0.12)
    else:
        y_cwnd_label = y_cwnd + max(12.0, 0.06 * max(y_cwnd, 1.0))

    ax.text(
        t_bdp,
        y_bdp,
        "BDP+Q",
        color=COLOR_BDP,
        fontsize=10,
        ha="center",
        va="bottom",
        clip_on=False,
        zorder=label_z,
    )
    ax.text(
        t_cwnd,
        y_cwnd_label,
        "CWND",
        color=COLOR_CWND,
        fontsize=10,
        ha="center",
        va="bottom",
        clip_on=False,
        zorder=label_z,
    )


def _plot_hypatia_panels(panels, out_prefix, time_window_s):
    fig, axes = plt.subplots(1, len(panels), figsize=(4.8 * len(panels), 4.2), sharey=False)
    if len(panels) == 1:
        axes = [axes]

    for ax, (panel_title, p) in zip(axes, panels):
        cx, cy = p["cwnd"]
        bx, by = p["bdp"]

        ax.plot(bx, by, drawstyle="steps-post", lw=2.4, color=COLOR_BDP, zorder=2)
        ax.plot(cx, cy, drawstyle="steps-post", lw=2.4, color=COLOR_CWND, zorder=3)

        ymax = 50.0
        for ys in (cy, by):
            if ys:
                ymax = max(ymax, max(ys))
        ax.set_ylim(0.0, ymax * 1.08)
        ax.set_xlim(0.0, float(time_window_s))
        ax.set_title(panel_title, fontsize=11)
        ax.set_xlabel("Time (s)")
        ax.grid(True, linestyle=":", color="#999999", alpha=0.55)
        ax.set_axisbelow(True)

        _add_cwnd_bdp_line_labels(ax, bx, by, cx, cy, time_window_s, ymax=ymax * 1.08)

    axes[0].set_ylabel("# of packets", fontsize=11)
    fig.tight_layout()

    os.makedirs(os.path.dirname(os.path.abspath(out_prefix)), exist_ok=True)
    png = out_prefix + ".png"
    pdf = out_prefix + ".pdf"
    fig.savefig(png, dpi=220, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    print("Wrote:", png)
    print("Wrote:", pdf)


def _plot_combined_panels(panel_specs, out_prefix, time_window_s):
    """
    Three panels with LEO-only and multilayer overlaid per city pair.
    Solid = CWND, dashed = BDP+Q; blue = LEO-only, green = multilayer.
    """
    fig, axes = plt.subplots(1, len(panel_specs), figsize=(4.8 * len(panel_specs), 4.5), sharey=False)
    if len(panel_specs) == 1:
        axes = [axes]

    legend_handles = []
    legend_labels = []

    for ax, (panel_title, leo_p, ml_p) in zip(axes, panel_specs):
        ymax = 50.0
        for p in (leo_p, ml_p):
            for key in ("cwnd", "bdp"):
                ys = p[key][1]
                if ys:
                    ymax = max(ymax, max(ys))

        for color, p, prefix in (
            (COLOR_LEO, leo_p, "LEO-only"),
            (COLOR_MULTILAYER, ml_p, "Multilayer"),
        ):
            cx, cy = p["cwnd"]
            bx, by = p["bdp"]
            (h_c,) = ax.plot(
                cx,
                cy,
                drawstyle="steps-post",
                lw=2.2,
                color=color,
                zorder=3,
            )
            (h_b,) = ax.plot(
                bx,
                by,
                drawstyle="steps-post",
                lw=2.0,
                color=color,
                ls="--",
                alpha=0.85,
                zorder=2,
            )
            if ax is axes[0]:
                legend_handles.extend([h_c, h_b])
                legend_labels.extend(["%s CWND" % prefix, "%s BDP+Q" % prefix])

        ax.set_ylim(0.0, ymax * 1.08)
        ax.set_xlim(0.0, float(time_window_s))
        ax.set_title(panel_title, fontsize=11)
        ax.set_xlabel("Time (s)")
        ax.grid(True, linestyle=":", color="#999999", alpha=0.55)
        ax.set_axisbelow(True)

    axes[0].set_ylabel("# of packets", fontsize=11)
    fig.legend(
        legend_handles,
        legend_labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.08),
        ncol=4,
        fontsize=9,
        framealpha=0.92,
    )
    fig.subplots_adjust(top=0.88)
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.88])

    os.makedirs(os.path.dirname(os.path.abspath(out_prefix)), exist_ok=True)
    png = out_prefix + ".png"
    pdf = out_prefix + ".pdf"
    fig.savefig(png, dpi=220, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    print("Wrote:", png)
    print("Wrote:", pdf)


def main():
    parser = argparse.ArgumentParser(
        description="Figure B — CWND vs BDP+Q (Hypatia style, experiment 1 pairs by default)."
    )
    parser.add_argument(
        "--duration-s",
        type=float,
        default=float(simulation_end_time_s),
        help="X-axis upper limit and clip window.",
    )
    parser.add_argument(
        "--time-step-ms",
        type=int,
        default=dynamic_state_update_interval_ms,
        help="Printed for context only.",
    )
    parser.add_argument(
        "--scenario",
        choices=("experiment1", "example3"),
        default="experiment1",
        help="Pair set (default: experiment1 Mumbai/Lima/Karachi/Tokyo).",
    )
    parser.add_argument(
        "--constellation",
        choices=("leo", "multilayer"),
        default="multilayer",
        help="LEO-only or multilayer runs (experiment1 only).",
    )
    parser.add_argument(
        "--dual-figures",
        action="store_true",
        default=True,
        help="Write both LEO and multilayer figures for experiment1 (default: on).",
    )
    parser.add_argument(
        "--single-figure",
        action="store_true",
        help="Only one figure (--constellation selects leo or multilayer).",
    )
    parser.add_argument(
        "--example3-leo",
        action="store_true",
        help="Shortcut for --scenario example3 --single-figure --constellation leo.",
    )
    parser.add_argument(
        "--queue-packets",
        type=float,
        default=QUEUE_PACKETS,
        help="Queue size Q in BDP+Q (default: 100).",
    )
    args = parser.parse_args()

    if args.example3_leo:
        args.scenario = "example3"
        args.single_figure = True
        args.constellation = "leo"

    queue_packets = float(args.queue_packets)

    if args.scenario == "experiment1":
        constellations = [args.constellation]
        if args.dual_figures and not args.single_figure and args.constellation == "multilayer":
            constellations = ["multilayer", "leo"]
        elif args.dual_figures and not args.single_figure and args.constellation == "leo":
            constellations = ["leo", "multilayer"]
    else:
        constellations = ["leo" if args.constellation == "leo" else "multilayer"]

    wrote_any = False
    combined_specs = []

    for const in constellations:
        if args.scenario == "experiment1":
            spec = _experiment1_panels(const)
        else:
            spec = _example3_panels(const == "leo")

        panels = []
        for panel_title, run_name in spec:
            try:
                p = _clip_panel(_load_panel(run_name, queue_packets), args.duration_s)
            except Exception as e:
                print("ERROR [%s] %s: %s" % (panel_title, run_name, e))
                continue
            panels.append((panel_title, p))
            cx, cy = p["cwnd"]
            bx, by = p["bdp"]
            print(
                "%s: %s · cwnd max %.0f pkts · bdp+q max %.0f pkts · t≤%.0f s"
                % (panel_title, run_name, max(cy) if cy else 0, max(by) if by else 0, args.duration_s)
            )

        if not panels:
            print("ERROR: no panels for %s / %s" % (args.scenario, const))
            continue

        if args.scenario == "experiment1" and const == "leo":
            out_prefix = os.path.join(FIGURE_DIR, "figure_b_cwnd_vs_bdp_leo_only")
        elif args.scenario == "experiment1" and const == "multilayer":
            out_prefix = os.path.join(FIGURE_DIR, "figure_b_cwnd_vs_bdp_multilayer")
        else:
            out_prefix = os.path.join(FIGURE_DIR, "figure_b_cwnd_vs_bdp")

        print(
            "Figure B [%s / %s]: MSS=%.0f B · 10 Mbps · Q=%.0f · x∈[0, %.0f] s"
            % (args.scenario, const, TCP_MSS_BYTES, queue_packets, args.duration_s)
        )
        _plot_hypatia_panels(panels, out_prefix, args.duration_s)
        if args.scenario == "experiment1" and const == "multilayer":
            alias = os.path.join(FIGURE_DIR, "figure_b_cwnd_vs_bdp")
            for ext in (".png", ".pdf"):
                shutil.copy2(out_prefix + ext, alias + ext)
                print("Wrote:", alias + ext)
        if args.scenario == "experiment1":
            while len(combined_specs) < len(panels):
                combined_specs.append([None, None, None])
            for i, (panel_title, p) in enumerate(panels):
                if combined_specs[i][0] is None:
                    combined_specs[i][0] = panel_title
                slot = 1 if const == "leo" else 2
                combined_specs[i][slot] = p
        wrote_any = True

    if (
        args.scenario == "experiment1"
        and args.dual_figures
        and not args.single_figure
        and combined_specs
        and all(row[1] is not None and row[2] is not None for row in combined_specs)
    ):
        both_prefix = os.path.join(FIGURE_DIR, "figure_b_cwnd_vs_bdp_both")
        print(
            "Figure B [experiment1 / both]: MSS=%.0f B · 10 Mbps · Q=%.0f · x∈[0, %.0f] s"
            % (TCP_MSS_BYTES, queue_packets, args.duration_s)
        )
        _plot_combined_panels(
            [(title, leo_p, ml_p) for title, leo_p, ml_p in combined_specs],
            both_prefix,
            args.duration_s,
        )

    return 0 if wrote_any else 1


if __name__ == "__main__":
    sys.exit(main())

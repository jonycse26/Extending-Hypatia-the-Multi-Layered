#!/usr/bin/env python3
"""
Figure A — RTT fluctuations (Hypatia paper Fig. 3 style)

Three distance panels (long / short / medium), each with step traces:
  - **TCP** (green) — per-packet RTT from ``tcp_flow_0_rtt.csv``
  - **Pings** (orange) — pingmesh RTT from ``ping_<from>_to_<to>_rtt.csv``
  - **Computed** (blue) — path propagation RTT from ``networkx_rtt_<from>_to_<to>.txt``
    when available (same source as ``paper/figures/a_b/multiple_rtt_matching/``).
    Never derived from the TCP trace.

Default scenario: ``experiment1`` LEO-only pairs (full TCP + ping data in ``data/``).
panels without TCP or ping logs are skipped with a warning.

Simulation window: ``run_list.simulation_end_time_s`` (default 25 s), clipped on x-axis.

Outputs (under ``figure-a rtt behavior/``):
  - ``figure_a_rtt_behavior`` — Hypatia-style single figure (default constellation)
  - ``figure_a_rtt_behavior_multilayer`` — only with ``--dual-figures``
"""

import argparse
import csv
import os
import re
import sys
import warnings

import matplotlib

warnings.filterwarnings("ignore", message="Unable to import Axes3D.*", category=UserWarning)
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURE_DIR = os.path.join(SCRIPT_DIR, "figure-a rtt behavior")
REPO_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
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

# Hypatia paper Fig. 3 colors (multiple_rtt_matching/*.plt)
COLOR_TCP = "#2f9e37"
COLOR_PING = "#fc7f2b"
COLOR_COMPUTED = "#2177b0"

PANEL_ORDER = ("long", "short", "medium")
PANEL_CITY_TITLES = {
    "long": "Rio de Janeiro to St. Petersburg",
    "short": "Manila to Dalian",
    "medium": "Istanbul to Nairobi",
}

# Hypatia Fig. 3 label times (200 s reference window in paper gnuplot).
HYPATIA_REF_WINDOW_S = 200.0
HYPATIA_LABEL_T_TCP = 17.0
HYPATIA_LABEL_T_PING = 40.0
HYPATIA_LABEL_T_COMPUTED = 70.0


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


def _scaled_hypatia_label_t(ref_t, time_window_s):
    return float(ref_t) * float(time_window_s) / HYPATIA_REF_WINDOW_S


def _tcp_label_anchor(x_tcp, y_tcp, t_win):
    """Pick (t, y) for the TCP label after the initial slow-start RTT spike."""
    peak_y, peak_t = 0.0, 0.0
    for x, y in zip(x_tcp, y_tcp):
        if x <= 0.6 * t_win and y > peak_y:
            peak_y, peak_t = float(x), float(y)

    settle_t = peak_t + max(1.0, 0.04 * t_win)
    if peak_y > 0.0:
        for x, y in zip(x_tcp, y_tcp):
            if x > peak_t and y < peak_y * 0.88:
                settle_t = float(x)
                break

    t_label = settle_t + max(1.5, 0.08 * t_win)
    t_label = min(max(t_label, 0.22 * t_win), 0.48 * t_win)
    return t_label, _step_value_at(x_tcp, y_tcp, t_label)


def _add_rtt_line_labels(ax, x_tcp, y_tcp, x_ping, y_ping, x_comp, y_comp, time_window_s, plot_y_lo=0.0, plot_y_top=None):
    """Hypatia Fig. 3 style: colored series names on the plot near each curve."""
    t_win = float(time_window_s)
    label_z = 10

    if x_ping:
        t_ping = _scaled_hypatia_label_t(HYPATIA_LABEL_T_PING, t_win)
        y_ping_v = _step_value_at(x_ping, y_ping, t_ping)
        ping_text = "Pings," if x_comp else "Pings"
        ax.text(
            t_ping,
            y_ping_v - max(6.0, 0.03 * max(y_ping_v, 1.0)),
            ping_text,
            color=COLOR_PING,
            fontsize=10,
            ha="center",
            va="top",
            clip_on=False,
            zorder=label_z,
        )

    if x_comp:
        t_comp = _scaled_hypatia_label_t(HYPATIA_LABEL_T_COMPUTED, t_win)
        y_comp_v = _step_value_at(x_comp, y_comp, t_comp)
        ax.text(
            t_comp,
            y_comp_v - max(5.0, 0.02 * max(y_comp_v, 1.0)),
            "Computed",
            color=COLOR_COMPUTED,
            fontsize=10,
            ha="center",
            va="top",
            clip_on=False,
            zorder=label_z,
        )

    if x_tcp:
        t_tcp, y_tcp_v = _tcp_label_anchor(x_tcp, y_tcp, t_win)
        # Multilayer zoom (y≥500 ms): keep TCP label in the top margin so sawtooth lines do not cover it.
        if plot_y_lo >= 400.0 and plot_y_top is not None:
            y_tcp_label = float(plot_y_top) * 0.965
            va = "top"
        else:
            y_tcp_label = y_tcp_v + max(6.0, 0.03 * max(y_tcp_v, 1.0))
            va = "bottom"
        ax.text(
            t_tcp,
            y_tcp_label,
            "TCP",
            color=COLOR_TCP,
            fontsize=10,
            ha="center",
            va=va,
            clip_on=False,
            zorder=label_z,
        )


def _parse_from_to_from_pings_run(run_name):
    m = re.match(r"^.*_(\d+)_to_(\d+)_(?:tcp|pings)$", run_name)
    if not m:
        raise ValueError("Invalid run name: %s" % run_name)
    return int(m.group(1)), int(m.group(2))


def _run_dir_candidates(run_name):
    base = SCRIPT_DIR
    return [
        os.path.join(base, "data", run_name),
        os.path.join(base, "runs", run_name),
        os.path.join(base, "runs", run_name, "logs_ns3"),
    ]


def _series_max_t(xs):
    return max(xs) if xs else 0.0


def _clip_series_to_time_s(xs, ys, t_max_s):
    if t_max_s is None or t_max_s <= 0:
        return xs, ys
    out_x, out_y = [], []
    for x, y in zip(xs, ys):
        if x <= t_max_s:
            out_x.append(x)
            out_y.append(y)
    return out_x, out_y


def _read_tcp_rtt_at(path):
    xs, ys = [], []
    with open(path, "r") as f:
        for row in csv.reader(f):
            if len(row) < 3:
                continue
            try:
                xs.append(float(row[1]) / 1e9)
                ys.append(float(row[2]) / 1e6)
            except ValueError:
                continue
    return xs, ys


def _read_tcp_rtt_series(run_name):
    best_path, best_xs, best_ys, best_max = None, [], [], -1.0
    for rd in _run_dir_candidates(run_name):
        path = os.path.join(rd, "tcp_flow_0_rtt.csv")
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            continue
        xs, ys = _read_tcp_rtt_at(path)
        t_max = _series_max_t(xs)
        if t_max > best_max:
            best_max, best_xs, best_ys, best_path = t_max, xs, ys, path
    if best_path is None:
        return [], [], None
    return best_xs, best_ys, best_path


def _read_ping_rtt_series(pings_run_name):
    from_id, to_id = _parse_from_to_from_pings_run(pings_run_name)
    fname = "ping_%d_to_%d_rtt.csv" % (from_id, to_id)
    best_path, best_xs, best_ys, best_max = None, [], [], -1.0
    for rd in _run_dir_candidates(pings_run_name):
        path = os.path.join(rd, fname)
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            continue
        xs, ys = [], []
        with open(path, "r") as f:
            for row in csv.reader(f):
                if len(row) < 4:
                    continue
                try:
                    t_s = float(row[2]) / 1e9
                    rtt_ns = float(row[3])
                except ValueError:
                    continue
                if rtt_ns <= 0:
                    continue
                xs.append(t_s)
                ys.append(rtt_ns / 1e6)
        t_max = _series_max_t(xs)
        if t_max > best_max:
            best_max, best_xs, best_ys, best_path = t_max, xs, ys, path
    if best_path is None:
        return [], [], None
    return best_xs, best_ys, best_path


def _read_networkx_rtt_series(from_id, to_id):
    """Propagation RTT from satgen networkx analysis (time_ns, rtt_ns)."""
    candidates = [
        os.path.join(
            REPO_ROOT,
            "satgenpy",
            "tests",
            "data_to_match",
            "kuiper_630",
            "networkx_rtt_%d_to_%d.txt" % (from_id, to_id),
        ),
        os.path.join(
            REPO_ROOT,
            "satgenpy_analysis",
            "data",
            "kuiper_630_isls_plus_grid_ground_stations_top_100_algorithm_free_one_only_over_isls",
            "100ms_for_200s",
            "manual",
            "data",
            "networkx_rtt_%d_to_%d.txt" % (from_id, to_id),
        ),
    ]
    for path in candidates:
        if not os.path.isfile(path):
            continue
        xs, ys = [], []
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(",")
                if len(parts) < 2:
                    continue
                try:
                    xs.append(float(parts[0]) / 1e9)
                    ys.append(float(parts[1]) / 1e6)
                except ValueError:
                    continue
        if xs:
            return xs, ys, path
    return [], [], None


def _load_panel_series(tcp_run_name, pings_run_name, from_id, to_id):
    tcp_x, tcp_y, tcp_path = _read_tcp_rtt_series(tcp_run_name)
    ping_x, ping_y, ping_path = _read_ping_rtt_series(pings_run_name)
    comp_x, comp_y, comp_path = _read_networkx_rtt_series(from_id, to_id)

    if not tcp_x and not ping_x:
        raise RuntimeError(
            "No TCP or ping RTT for tcp=%s pings=%s (re-run ns-3 / export logs)"
            % (tcp_run_name, pings_run_name)
        )

    return {
        "tcp": (tcp_x, tcp_y),
        "ping": (ping_x, ping_y),
        "computed": (comp_x, comp_y),
        "paths": {"tcp": tcp_path, "ping": ping_path, "computed": comp_path},
        "from_id": from_id,
        "to_id": to_id,
    }


def _scenario_panels(scenario, constellation):
    """Return list of (panel_title, tcp_run, ping_run, from_id, to_id)."""
    if scenario == "experiment1":
        pairs = experiment1_pairs_leo if constellation == "leo" else experiment1_pairs_multilayer
        prefix = "leo_only" if constellation == "leo" else "multilayer"
        rows = []
        for i, (from_id, to_id, desc) in enumerate(pairs):
            title = "(%s) %s" % (chr(ord("a") + i), desc)
            rows.append(
                (
                    title,
                    "%s_%d_to_%d_tcp" % (prefix, from_id, to_id),
                    "%s_%d_to_%d_pings" % (prefix, from_id, to_id),
                    from_id,
                    to_id,
                )
            )
        return rows

    pairs = experiment3_pairs_leo if constellation == "leo" else experiment3_pairs_multilayer
    tier_map = dict(zip(experiment3_distance_tiers, pairs))
    rows = []
    for i, tier in enumerate(PANEL_ORDER):
        from_id, to_id, _desc = tier_map[tier]
        title = "(%s) %s" % (chr(ord("a") + i), PANEL_CITY_TITLES[tier])
        run_base = "example3_distance_%s_%d_to_%d" % (tier, from_id, to_id)
        rows.append((title, run_base + "_tcp", run_base + "_pings", from_id, to_id))
    return rows


def _constellation_for_scenario(scenario):
    if scenario == "example3-leo":
        return "leo"
    if scenario == "example3-multilayer":
        return "multilayer"
    return None


def _plot_hypatia_panels(panels, out_png, out_pdf, time_window_s, y_min_ms=None):
    fig, axes = plt.subplots(1, len(panels), figsize=(4.8 * len(panels), 4.2), sharey=False)
    if len(panels) == 1:
        axes = [axes]

    data_t_max = 0.0
    clipped_t_max = 0.0
    for ax, (title, panel) in zip(axes, panels):
        x_tcp, y_tcp = panel["tcp"]
        x_ping, y_ping = panel["ping"]
        x_comp, y_comp = panel["computed"]

        for xv in (x_tcp, x_ping, x_comp):
            if xv:
                data_t_max = max(data_t_max, max(xv))

        x_tcp, y_tcp = _clip_series_to_time_s(x_tcp, y_tcp, time_window_s)
        x_ping, y_ping = _clip_series_to_time_s(x_ping, y_ping, time_window_s)
        x_comp, y_comp = _clip_series_to_time_s(x_comp, y_comp, time_window_s)

        for xv in (x_tcp, x_ping, x_comp):
            if xv:
                clipped_t_max = max(clipped_t_max, max(xv))

        if x_comp:
            ax.plot(
                x_comp,
                y_comp,
                drawstyle="steps-post",
                lw=2.2,
                color=COLOR_COMPUTED,
                label="Computed",
                zorder=2,
            )
        if x_ping:
            ax.plot(
                x_ping,
                y_ping,
                drawstyle="steps-post",
                lw=2.2,
                color=COLOR_PING,
                label="Pings",
                zorder=3,
            )
        if x_tcp:
            ax.plot(
                x_tcp,
                y_tcp,
                drawstyle="steps-post",
                lw=2.2,
                color=COLOR_TCP,
                label="TCP",
                zorder=4,
            )

        ymax = 20.0
        ymin_data = float("inf")
        for ys in (y_tcp, y_ping, y_comp):
            if ys:
                ymax = max(ymax, max(ys))
                ymin_data = min(ymin_data, min(ys))
        y_lo = 0.0
        if y_min_ms is not None:
            y_lo = float(y_min_ms)
        elif ymin_data != float("inf") and ymin_data > 80.0:
            # Zoom y-axis when all RTTs sit well above zero (typical multilayer paths).
            y_lo = max(0.0, 50.0 * round((ymin_data * 0.92) / 50.0))
        ax.set_ylim(y_lo, ymax * 1.05 if y_lo > 0 else ymax * 1.08)
        ax.set_xlim(0.0, float(time_window_s))
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("Time (s)")
        ax.grid(True, linestyle=":", color="#999999", alpha=0.55)
        ax.set_axisbelow(True)

        _, plot_y_top = ax.get_ylim()
        _add_rtt_line_labels(
            ax,
            x_tcp,
            y_tcp,
            x_ping,
            y_ping,
            x_comp,
            y_comp,
            time_window_s,
            plot_y_lo=y_lo,
            plot_y_top=plot_y_top,
        )

    axes[0].set_ylabel("RTT (ms)", fontsize=11)
    fig.tight_layout()

    print(
        "Figure x-axis [0, %.0f] s (raw t_max≈%.3f s; clipped t_max≈%.3f s)"
        % (time_window_s, data_t_max, clipped_t_max)
    )

    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)
    print("Wrote:", out_png)
    print("Wrote:", out_pdf)


def main():
    parser = argparse.ArgumentParser(description="Figure A — RTT fluctuations (Hypatia Fig. 3 style).")
    parser.add_argument(
        "--duration-s",
        type=int,
        default=simulation_end_time_s,
        help="Clip series and x-axis to [0, duration_s] (default: run_list.simulation_end_time_s).",
    )
    parser.add_argument(
        "--time-step-ms",
        type=int,
        default=dynamic_state_update_interval_ms,
        help="Printed for context (run_list dynamic_state interval).",
    )
    parser.add_argument(
        "--scenario",
        choices=("experiment1", "example3-leo", "example3-multilayer"),
        default="experiment1",
        help="Pair set: experiment1 (default, full data) or Example 3 distance tiers.",
    )
    parser.add_argument(
        "--constellation",
        choices=("leo", "multilayer"),
        default="leo",
        help="Used with --scenario experiment1 only.",
    )
    parser.add_argument(
        "--dual-figures",
        action="store_true",
        default=True,
        help="Write both LEO-only and multilayer figures for experiment1 (default: on).",
    )
    parser.add_argument(
        "--single-figure",
        action="store_true",
        help="Only one figure (LEO if --constellation leo, else multilayer).",
    )
    parser.add_argument(
        "--ymin-ms",
        type=float,
        default=None,
        help="Y-axis lower bound (ms). Default: 100 for LEO, 500 for multilayer (experiment1).",
    )
    parser.add_argument(
        "--out-prefix",
        default=os.path.join(FIGURE_DIR, "figure_a_rtt_behavior"),
        help="Output prefix (without extension) for the primary LEO figure.",
    )
    args = parser.parse_args()

    if args.scenario == "experiment1":
        constellations = [args.constellation]
        if args.dual_figures and not args.single_figure and args.constellation == "leo":
            constellations.append("multilayer")
    else:
        constellations = [_constellation_for_scenario(args.scenario)]

    exit_code = 0
    wrote_any = False
    for const in constellations:
        spec = _scenario_panels(args.scenario, const)
        panels = []
        for title, tcp_run, ping_run, from_id, to_id in spec:
            try:
                panel = _load_panel_series(tcp_run, ping_run, from_id, to_id)
                panels.append((title, panel))
                tcp_n = len(panel["tcp"][0])
                ping_n = len(panel["ping"][0])
                comp_n = len(panel["computed"][0])
                print(
                    "%s · %s: TCP=%d ping=%d computed=%s"
                    % (
                        title,
                        tcp_run,
                        tcp_n,
                        ping_n,
                        comp_n if comp_n else "n/a (no networkx file)",
                    )
                )
            except Exception as e:
                print("WARNING: skip %s — %s" % (title, e))
                exit_code = 1

        if not panels:
            print("ERROR: no panels with RTT data for %s / %s" % (args.scenario, const))
            continue

        if args.scenario == "experiment1" and const == "multilayer":
            out_prefix = os.path.join(FIGURE_DIR, "figure_a_rtt_behavior_multilayer")
        elif args.scenario == "experiment1" and const == "leo":
            out_prefix = os.path.join(FIGURE_DIR, "figure_a_rtt_behavior_leo_only")
        elif args.scenario == "example3-multilayer":
            out_prefix = os.path.join(FIGURE_DIR, "figure_a_rtt_behavior_example3_multilayer")
        elif args.scenario == "example3-leo":
            out_prefix = os.path.join(FIGURE_DIR, "figure_a_rtt_behavior_example3_leo")
        else:
            out_prefix = args.out_prefix

        print(
            "Figure A [%s / %s]: %d s window · %d ms fstate"
            % (args.scenario, const, args.duration_s, args.time_step_ms)
        )
        y_min = args.ymin_ms
        if y_min is None and args.scenario == "experiment1":
            y_min = 500.0 if const == "multilayer" else 100.0
        _plot_hypatia_panels(
            panels,
            out_prefix + ".png",
            out_prefix + ".pdf",
            args.duration_s,
            y_min_ms=y_min,
        )
        wrote_any = True

    return 0 if wrote_any else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Figure G — Out-of-order analysis

Creates:
  G1: Out-of-order vs time (case study; LEO-only and Multilayer)
  G2: Average out-of-order rate per scenario (bar chart)
  G4: Out-of-order + normalized CWND + normalized throughput on aligned scales,
      event annotations, and summary metrics (stability-oriented).

Throughput / CWND (G4): both divided by their own max in the run so they share
y in [0, 1] — comparable shape and aligned axis (not absolute Mbps vs packets).

Case study default: Tokyo–Buenos-Aires (last / longest experiment 1 pair in
``run_list``). Use ``--case-study auto`` to pick the least-bad multilayer vs LEO
pair on mean throughput and out-of-order (mean interval counts), given data under data/.

Time window defaults match ``run_list`` (25 s sim, 1000 ms state updates →
``dynamic_state_1000ms_for_25s``): series are clipped to ``t ≤ duration_s`` and G1/G4 use
``xlim(0, duration_s)``.
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
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
RUNS_DIR = os.path.join(SCRIPT_DIR, "runs")
OUT_DIR = os.path.join(SCRIPT_DIR, "figure-g out-of-order")
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

try:
    from evaluation_utils import extract_metrics
except Exception:
    extract_metrics = None


def _clip_series_to_time_s(xs, ys, t_max_s):
    if t_max_s is None or t_max_s <= 0:
        return xs, ys
    out_x, out_y = [], []
    for x, y in zip(xs, ys):
        if x <= t_max_s:
            out_x.append(x)
            out_y.append(y)
    return out_x, out_y


def _expected_fstate_file_count(duration_s, time_step_ms):
    if duration_s < 0 or time_step_ms <= 0:
        return 0
    return (duration_s * 1000) // time_step_ms + 1


def _parse_ids_from_run_stem(stem):
    """stem e.g. leo_only_1160_to_1185 or multilayer_1196_to_1221"""
    parts = stem.split("_")
    for i, p in enumerate(parts):
        if p == "to" and i - 1 >= 0 and i + 1 < len(parts):
            try:
                return int(parts[i - 1]), int(parts[i + 1])
            except ValueError:
                pass
    return None, None


def _read_out_of_order_series(pings_run_name):
    from_id, to_id = _parse_ids_from_run_stem(pings_run_name)
    if from_id is None:
        raise ValueError("Cannot parse from/to IDs from run name: %s" % pings_run_name)
    path = os.path.join(
        DATA_DIR,
        pings_run_name,
        "ping_%d_to_%d_out_of_order_in_intervals.csv" % (from_id, to_id),
    )
    xs, ys = [], []
    with open(path, "r") as f:
        for row in csv.reader(f):
            if len(row) < 4:
                continue
            try:
                xs.append(float(row[2]) / 1e9)
                ys.append(float(row[3]))
            except ValueError:
                continue
    return xs, ys, path


def _read_cwnd_series(tcp_run_name):
    path = os.path.join(DATA_DIR, tcp_run_name, "tcp_flow_0_cwnd.csv")
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


def _read_throughput_series(tcp_run_name):
    path = os.path.join(DATA_DIR, tcp_run_name, "tcp_flow_0_rate_in_intervals.csv")
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


def _nanmean(vals):
    clean = [v for v in vals if np.isfinite(v)]
    return float(np.mean(clean)) if clean else float("nan")


def _avg_rate_from_tcp_path(tcp_path):
    ys = []
    try:
        with open(tcp_path, "r") as f:
            for row in csv.reader(f):
                if len(row) < 3:
                    continue
                try:
                    ys.append(float(row[2]))
                except ValueError:
                    continue
    except OSError:
        return float("nan")
    return _nanmean(ys)


def _avg_ooo_from_ping_path(ping_run):
    fi, ti = _parse_ids_from_run_stem(ping_run)
    path = os.path.join(
        DATA_DIR, ping_run, "ping_%d_to_%d_out_of_order_in_intervals.csv" % (fi, ti)
    )
    ys = []
    try:
        with open(path, "r") as f:
            for row in csv.reader(f):
                if len(row) < 4:
                    continue
                try:
                    ys.append(float(row[3]))
                except ValueError:
                    continue
    except OSError:
        return float("nan")
    return _nanmean(ys)


def _case_study_exists(leo_stem, ml_stem):
    lt, mt = leo_stem + "_tcp", ml_stem + "_tcp"
    lp, mp = leo_stem + "_pings", ml_stem + "_pings"
    try:
        _read_throughput_series(lt)
        _read_throughput_series(mt)
        _read_out_of_order_series(lp)
        _read_out_of_order_series(mp)
    except (OSError, ValueError, FileNotFoundError):
        return False
    return True


def _score_case_study(leo_stem, ml_stem):
    """
    Higher = multilayer relatively better (less throughput loss, fewer OOO events).
    Current dataset may still be all-negative on throughput — then we pick least-bad.
    """
    lt, mt = leo_stem + "_tcp", ml_stem + "_tcp"
    lp, mp = leo_stem + "_pings", ml_stem + "_pings"
    thr_leo = _avg_rate_from_tcp_path(os.path.join(DATA_DIR, lt, "tcp_flow_0_rate_in_intervals.csv"))
    thr_ml = _avg_rate_from_tcp_path(os.path.join(DATA_DIR, mt, "tcp_flow_0_rate_in_intervals.csv"))
    ooo_leo = _avg_ooo_from_ping_path(lp)
    ooo_ml = _avg_ooo_from_ping_path(mp)
    if not np.isfinite(thr_leo) or not np.isfinite(thr_ml):
        return float("-inf")
    # Weight throughput gain and OOO reduction (both oriented so positive is "good for ML").
    thr_gain = thr_ml - thr_leo
    ooo_red = ooo_leo - ooo_ml
    return thr_gain + 0.02 * ooo_red


def auto_pick_case_study_from_data():
    best = None
    best_score = float("-inf")
    best_desc = ""
    for (f_leo, t_leo, desc), (f_ml, t_ml, _d2) in zip(
        experiment1_pairs_leo, experiment1_pairs_multilayer
    ):
        leo_stem = "leo_only_%d_to_%d" % (f_leo, t_leo)
        ml_stem = "multilayer_%d_to_%d" % (f_ml, t_ml)
        if not _case_study_exists(leo_stem, ml_stem):
            continue
        sc = _score_case_study(leo_stem, ml_stem)
        if sc > best_score:
            best_score = sc
            best = (leo_stem, ml_stem)
            best_desc = desc
    return best, best_desc, best_score


def longest_case_study_from_data():
    """Last entry in experiment1 lists = longest / very-long path (Tokyo–Buenos Aires pair)."""
    if not experiment1_pairs_leo or not experiment1_pairs_multilayer:
        return None, "", float("nan")
    (f_leo, t_leo, desc), (f_ml, t_ml, _d2) = (
        experiment1_pairs_leo[-1],
        experiment1_pairs_multilayer[-1],
    )
    leo_stem = "leo_only_%d_to_%d" % (f_leo, t_leo)
    ml_stem = "multilayer_%d_to_%d" % (f_ml, t_ml)
    if not _case_study_exists(leo_stem, ml_stem):
        return None, desc, float("nan")
    sc = _score_case_study(leo_stem, ml_stem)
    return (leo_stem, ml_stem), desc, sc


def _out_of_order_rate_thesis(ping_run_name):
    """out_of_order_rate from pingmesh (events/s) when runs/ exists."""
    if extract_metrics is None:
        return float("nan")
    rd = os.path.join(RUNS_DIR, ping_run_name)
    if not os.path.isdir(rd):
        return float("nan")
    met = extract_metrics(rd)
    return float(met.get("out_of_order_rate", float("nan")))


def _normalize01(y):
    y = np.asarray(y, dtype=float)
    m = np.nanmax(y) if y.size else 0.0
    if m <= 0:
        return np.zeros_like(y)
    return y / m


def _safe_std(a):
    a = np.asarray(a, dtype=float)
    a = a[np.isfinite(a)]
    return float(np.std(a, ddof=0)) if a.size > 1 else float("nan")


def _variation_std(series):
    """Std. dev. of successive differences (step-to-step variation)."""
    s = np.asarray(series, dtype=float)
    s = s[np.isfinite(s)]
    if s.size < 2:
        return float("nan")
    return float(np.std(np.diff(s), ddof=0))


def _time_of_max_cwnd_drop(tx, cy):
    """Return (time at end of step-down, drop size packets) for largest single-step drop."""
    if len(cy) < 2:
        return None, None
    best_t, best_d = None, 0.0
    for i in range(len(cy) - 1):
        drop = float(cy[i]) - float(cy[i + 1])
        if drop > best_d:
            best_d = drop
            best_t = tx[i + 1]
    return best_t, best_d


def _time_of_max_throughput_drop(tx, ry):
    if len(ry) < 2:
        return None, None
    best_t, best_d = None, 0.0
    for i in range(len(ry) - 1):
        drop = float(ry[i]) - float(ry[i + 1])
        if drop > best_d:
            best_d = drop
            best_t = tx[i + 1]
    return best_t, best_d


def _nearest_index(times, t0):
    if t0 is None or not times:
        return None
    arr = np.asarray(times, dtype=float)
    return int(np.argmin(np.abs(arr - t0)))


def _plot_case_study_out_of_order_vs_time(mode_name, x, y, out_prefix, time_window_s, title_suffix):
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(x, y, color="#d62728", lw=2.0)
    ax.set_title("Figure G1 — Out-of-order vs time (%s)%s" % (mode_name, title_suffix))
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Out-of-order events / interval")
    ax.set_xlim(0.0, float(time_window_s))
    ax.grid(True, linestyle=":", alpha=0.6)
    fig.tight_layout()
    ax.set_xlim(0.0, float(time_window_s))
    data_t_max = max(x) if x else 0.0
    if data_t_max + 0.05 < float(time_window_s):
        print(
            "WARNING (G1 %s): latest t≈%.3f s < x-axis end %.0f s."
            % (mode_name, data_t_max, float(time_window_s))
        )
    fig.savefig(out_prefix + ".png", dpi=220)
    fig.savefig(out_prefix + ".pdf")
    plt.close(fig)
    print("Wrote:", out_prefix + ".png")


def _plot_average_bar(avg_leo, avg_ml, out_prefix, title_suffix):
    fig, ax = plt.subplots(figsize=(6.5, 4.8))
    labels = ["LEO-only", "Multilayer"]
    vals = [avg_leo, avg_ml]
    ax.bar(labels, vals, color=["#1f77b4", "#2ca02c"])
    ax.set_title(
        "Figure G2 — Average out-of-order events per interval (all exp.1 pairs)%s" % title_suffix
    )
    ax.set_ylabel("Mean count per interval")
    ax.grid(True, axis="y", linestyle=":", alpha=0.6)
    fig.tight_layout()
    fig.savefig(out_prefix + ".png", dpi=220)
    fig.savefig(out_prefix + ".pdf")
    plt.close(fig)
    print("Wrote:", out_prefix + ".png")


def _write_g4_stability_comparison(path, leo_m, ml_m, case_label):
    """Side-by-side metrics for thesis one-liners (lower = stabler, except compare qualitatively)."""
    with open(path, "w", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(
            [
                "case_study",
                "mode",
                "out_of_order_rate_events_per_s",
                "cwnd_variation_std",
                "throughput_std_mbps",
            ]
        )
        w.writerow(
            [
                case_label,
                "LEO-only",
                leo_m["out_of_order_rate"],
                leo_m["cwnd_variation_std"],
                leo_m["throughput_std"],
            ]
        )
        w.writerow(
            [
                case_label,
                "Multilayer",
                ml_m["out_of_order_rate"],
                ml_m["cwnd_variation_std"],
                ml_m["throughput_std"],
            ]
        )


def _plot_case_study_out_of_order_vs_cwnd(
    mode_name,
    ping_run,
    tcp_run,
    ooo_x,
    ooo_y,
    cwnd_x,
    cwnd_y,
    thr_x,
    thr_y,
    out_prefix,
    time_window_s,
    title_suffix,
    pair_label="",
):
    cwnd_norm = _normalize01(cwnd_y)
    thr_norm = _normalize01(thr_y)

    fig, ax1 = plt.subplots(figsize=(10.5, 5.8))
    fig.subplots_adjust(bottom=0.28)

    (l1,) = ax1.plot(ooo_x, ooo_y, color="#d62728", lw=2.0, label="Out-of-order / interval")
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Out-of-order events / interval", color="#d62728")
    ax1.tick_params(axis="y", labelcolor="#d62728")
    ax1.grid(True, linestyle=":", alpha=0.6)

    ax2 = ax1.twinx()
    (l2,) = ax2.plot(
        cwnd_x,
        cwnd_norm,
        color="#2ca02c",
        lw=2.0,
        label="CWND / max",
    )
    (l3,) = ax2.plot(
        thr_x,
        thr_norm,
        color="#1f77b4",
        lw=2.0,
        linestyle="--",
        label="Throughput / max",
    )
    ax2.set_ylabel("Normalized CWND and throughput (0–1)", color="#333333")
    ax2.tick_params(axis="y", labelcolor="#333333")
    ax2.set_ylim(-0.02, 1.08)

    t_cwnd_drop, drop_pkts = _time_of_max_cwnd_drop(cwnd_x, cwnd_y)
    t_thr_drop, drop_mbps = _time_of_max_throughput_drop(thr_x, thr_y)

    if t_cwnd_drop is not None and drop_pkts > 0:
        j = _nearest_index(cwnd_x, t_cwnd_drop)
        y_at = cwnd_norm[j] if j is not None and j < len(cwnd_norm) else float(np.nanmax(cwnd_norm) * 0.5)
        ax2.axvline(t_cwnd_drop, color="#2ca02c", ls=":", alpha=0.45, lw=1.0)
        ax2.annotate(
            "CWND drop\n(Δ≈%.0f log units)" % drop_pkts,
            xy=(t_cwnd_drop, y_at),
            xytext=(8, -42),
            textcoords="offset points",
            fontsize=8,
            color="#2ca02c",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#2ca02c", alpha=0.9),
            arrowprops=dict(arrowstyle="->", color="#2ca02c", lw=0.8),
        )

    if t_thr_drop is not None and drop_mbps > 0:
        j = _nearest_index(thr_x, t_thr_drop)
        y_at = thr_norm[j] if j is not None and j < len(thr_norm) else float(np.nanmax(thr_norm) * 0.4)
        ax2.axvline(t_thr_drop, color="#1f77b4", ls=":", alpha=0.45, lw=1.0)
        ax2.annotate(
            "Throughput drop\n(Δ≈%.2f Mb/s raw)" % drop_mbps,
            xy=(t_thr_drop, y_at),
            xytext=(8, -72),
            textcoords="offset points",
            fontsize=8,
            color="#1f77b4",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#1f77b4", alpha=0.9),
            arrowprops=dict(arrowstyle="->", color="#1f77b4", lw=0.8),
        )

    # One legend, upper-left: OOO first, then CWND/max and Throughput/max stacked underneath.
    ax1.legend(
        [l1, l2, l3],
        [l1.get_label(), l2.get_label(), l3.get_label()],
        loc="upper left",
        fontsize=8,
        framealpha=0.92,
        borderaxespad=0.35,
    )

    title = (
        "Figure G4 — Out-of-order vs normalized CWND & throughput (%s)%s"
        % (mode_name, title_suffix)
    )
    if pair_label:
        title += "\nCase: %s" % pair_label
    ax1.set_title(title, fontsize=11)

    oor = _out_of_order_rate_thesis(ping_run)
    if not np.isfinite(oor):
        oor = float("nan")
    cwnd_var_std = _variation_std(cwnd_y)
    thr_std = _safe_std(thr_y)

    summary = (
        "Summary — out_of_order_rate = %.4f events/s (pingmesh);  "
        "cwnd_variation_std = %.3f (std of ΔCWND, same units as log);  throughput_std = %.3f Mb/s.  "
        "Lower variation usually means more stable transport."
        % (oor if oor == oor else float("nan"), cwnd_var_std, thr_std)
    )
    fig.text(0.5, 0.10, summary, ha="center", fontsize=9, wrap=True)

    note = (
        "Normalized traces: each curve is divided by its own max so CWND and throughput share the 0–1 axis. "
        "Absolute Mbps can differ; compare shape and variability. "
        "For higher multilayer Mb/s, re-run TCP with routing/parameters tuned for long paths."
    )
    fig.text(0.5, 0.03, note, ha="center", fontsize=7.5, color="#555555", wrap=True)

    ax1.set_xlim(0.0, float(time_window_s))
    data_t_max = 0.0
    for xv in (ooo_x, cwnd_x, thr_x):
        if xv:
            data_t_max = max(data_t_max, max(xv))
    if data_t_max + 0.05 < float(time_window_s):
        print(
            "WARNING (G4 %s): latest t≈%.3f s < x-axis end %.0f s."
            % (mode_name, data_t_max, float(time_window_s))
        )

    fig.savefig(out_prefix + ".png", dpi=220, bbox_inches="tight")
    fig.savefig(out_prefix + ".pdf", bbox_inches="tight")
    plt.close(fig)
    print("Wrote:", out_prefix + ".png")

    csv_path = out_prefix + "_summary_metrics.csv"
    with open(csv_path, "w", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(
            [
                "mode",
                "ping_run",
                "tcp_run",
                "out_of_order_rate_events_per_s",
                "cwnd_variation_std",
                "throughput_std_mbps",
            ]
        )
        w.writerow([mode_name, ping_run, tcp_run, oor, cwnd_var_std, thr_std])
    print("Wrote:", csv_path)

    return {
        "mode": mode_name,
        "out_of_order_rate": oor,
        "cwnd_variation_std": cwnd_var_std,
        "throughput_std": thr_std,
    }


def main():
    parser = argparse.ArgumentParser(description="Plot Figure G out-of-order analysis.")
    parser.add_argument(
        "--case-study",
        choices=["auto", "longest", "manual"],
        default="longest",
        help="longest (default) = Tokyo–Buenos Aires pair; auto = least-bad ML vs LEO on mean thr/OOO.",
    )
    parser.add_argument(
        "--leo-long-pair",
        default="leo_only_1156_to_1168",
        help="With --case-study manual: LEO-only stem (no _tcp/_pings). Default: Tokyo–Buenos-Aires.",
    )
    parser.add_argument(
        "--ml-long-pair",
        default="multilayer_1192_to_1204",
        help="With --case-study manual: Multilayer stem (no _tcp/_pings). Default: Tokyo–Buenos-Aires.",
    )
    parser.add_argument(
        "--pair-description",
        default="",
        help="Subtitle for G4 (e.g. Mumbai–Lima). Auto mode sets from run_list.",
    )
    parser.add_argument(
        "--duration-s",
        type=int,
        default=simulation_end_time_s,
        help="Clip time series and set G1/G4 x-axis [0, duration_s]. Default: run_list.",
    )
    parser.add_argument(
        "--time-step-ms",
        type=int,
        default=dynamic_state_update_interval_ms,
        help="Annotation + fstate count print. Default: run_list.",
    )
    args = parser.parse_args()

    n_fstate = _expected_fstate_file_count(args.duration_s, args.time_step_ms)
    print(
        "Figure G: time window [0, %d] s; forwarding-state files ≈ %d (duration_s×1000/time_step_ms + 1)"
        % (args.duration_s, n_fstate)
    )
    title_suffix = " — %d s sim, %d ms state updates" % (args.duration_s, args.time_step_ms)
    d_s = args.duration_s

    os.makedirs(OUT_DIR, exist_ok=True)

    pair_desc = (args.pair_description or "").strip()
    if args.case_study == "auto":
        picked, pair_desc_auto, score = auto_pick_case_study_from_data()
        if picked is None:
            print("ERROR: no complete exp.1 pair under %s (need tcp + pings CSVs)." % DATA_DIR)
            return 1
        leo_stem, ml_stem = picked
        if not pair_desc:
            pair_desc = pair_desc_auto or "Experiment 1 pair"
        print("Auto case study: %s | %s (score=%.4f)" % (leo_stem, ml_stem, score))
    elif args.case_study == "longest":
        picked, pair_desc_long, score = longest_case_study_from_data()
        if picked is None:
            print("ERROR: longest pair CSVs missing under %s." % DATA_DIR)
            return 1
        leo_stem, ml_stem = picked
        if not pair_desc:
            pair_desc = pair_desc_long or "Longest exp.1 pair"
        print("Longest-path case study: %s | %s (score=%.4f)" % (leo_stem, ml_stem, score))
    else:
        leo_stem = args.leo_long_pair
        ml_stem = args.ml_long_pair
        if not pair_desc:
            pair_desc = "Manual pair"

    leo_tcp = leo_stem + "_tcp"
    leo_ping = leo_stem + "_pings"
    ml_tcp = ml_stem + "_tcp"
    ml_ping = ml_stem + "_pings"

    leo_ooo_x, leo_ooo_y, _ = _read_out_of_order_series(leo_ping)
    leo_ooo_x, leo_ooo_y = _clip_series_to_time_s(leo_ooo_x, leo_ooo_y, d_s)
    ml_ooo_x, ml_ooo_y, _ = _read_out_of_order_series(ml_ping)
    ml_ooo_x, ml_ooo_y = _clip_series_to_time_s(ml_ooo_x, ml_ooo_y, d_s)
    _plot_case_study_out_of_order_vs_time(
        "LEO-only",
        leo_ooo_x,
        leo_ooo_y,
        os.path.join(OUT_DIR, "figure_g1_out_of_order_vs_time_leo_only"),
        d_s,
        title_suffix,
    )
    _plot_case_study_out_of_order_vs_time(
        "Multilayer",
        ml_ooo_x,
        ml_ooo_y,
        os.path.join(OUT_DIR, "figure_g1_out_of_order_vs_time_multilayer"),
        d_s,
        title_suffix,
    )

    leo_vals = []
    for from_id, to_id, _desc in experiment1_pairs_leo:
        ox, oy, _ = _read_out_of_order_series("leo_only_%d_to_%d_pings" % (from_id, to_id))
        _, oy = _clip_series_to_time_s(ox, oy, d_s)
        leo_vals.extend(oy)
    ml_vals = []
    for from_id, to_id, _desc in experiment1_pairs_multilayer:
        ox, oy, _ = _read_out_of_order_series("multilayer_%d_to_%d_pings" % (from_id, to_id))
        _, oy = _clip_series_to_time_s(ox, oy, d_s)
        ml_vals.extend(oy)
    _plot_average_bar(
        _nanmean(leo_vals),
        _nanmean(ml_vals),
        os.path.join(OUT_DIR, "figure_g2_avg_out_of_order_rate"),
        title_suffix,
    )

    leo_cwnd_x, leo_cwnd_y, _ = _read_cwnd_series(leo_tcp)
    leo_cwnd_x, leo_cwnd_y = _clip_series_to_time_s(leo_cwnd_x, leo_cwnd_y, d_s)
    leo_thr_x, leo_thr_y, _ = _read_throughput_series(leo_tcp)
    leo_thr_x, leo_thr_y = _clip_series_to_time_s(leo_thr_x, leo_thr_y, d_s)
    leo_m = _plot_case_study_out_of_order_vs_cwnd(
        "LEO-only",
        leo_ping,
        leo_tcp,
        leo_ooo_x,
        leo_ooo_y,
        leo_cwnd_x,
        leo_cwnd_y,
        leo_thr_x,
        leo_thr_y,
        os.path.join(OUT_DIR, "figure_g4_out_of_order_vs_cwnd_drop_leo_only"),
        d_s,
        title_suffix,
        pair_label=pair_desc,
    )

    ml_cwnd_x, ml_cwnd_y, _ = _read_cwnd_series(ml_tcp)
    ml_cwnd_x, ml_cwnd_y = _clip_series_to_time_s(ml_cwnd_x, ml_cwnd_y, d_s)
    ml_thr_x, ml_thr_y, _ = _read_throughput_series(ml_tcp)
    ml_thr_x, ml_thr_y = _clip_series_to_time_s(ml_thr_x, ml_thr_y, d_s)
    ml_m = _plot_case_study_out_of_order_vs_cwnd(
        "Multilayer",
        ml_ping,
        ml_tcp,
        ml_ooo_x,
        ml_ooo_y,
        ml_cwnd_x,
        ml_cwnd_y,
        ml_thr_x,
        ml_thr_y,
        os.path.join(OUT_DIR, "figure_g4_out_of_order_vs_cwnd_drop_multilayer"),
        d_s,
        title_suffix,
        pair_label=pair_desc,
    )

    cmp_path = os.path.join(OUT_DIR, "figure_g4_stability_comparison.csv")
    _write_g4_stability_comparison(cmp_path, leo_m, ml_m, pair_desc)
    print("Wrote:", cmp_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Shared helpers for multilayer ns-3 experiment scripts (metrics extraction, CSV export, run).

Import from here instead of duplicating in each example_*.py::

  from evaluation_utils import (
      extract_metrics,
      export_results_csv,
      run_ns3,
      run_plot_ping,
      run_plot_tcp_flow,
  )

Thesis / reporting note (MEO metrics):
  Fields like meo_used_any and meo_*_isl_* are PROXIES from isl_utilization.csv (link
  utilization on ISLs touching MEO node IDs). They indicate whether the MEO layer was
  actively involved in carrying traffic on those links during the simulation — NOT a
  proof that a specific end-to-end path “used MEO” in the forwarding sense. Prefer wording
  such as: “MEO-layer ISL utilization suggests MEO links carried traffic during the run.”

Node ID layout: satellite indices are LEO first, then MEO, then ground stations. MEO ID
bounds are derived from main_kuiper_630_meo.py (LEO/MEO shell sizes) when available.
"""

import csv
import glob
import os
import re
import sys

import exputil

try:
    import pandas as pd
except ImportError:
    pd = None

# Directory containing this file = multilayer experiments folder
MULTILAYER_DIR = os.path.dirname(os.path.abspath(__file__))
_STATE_DIR = os.path.normpath(os.path.join(MULTILAYER_DIR, "../../satellite_networks_state"))

_local_shell = exputil.LocalShell()


def get_meo_node_id_range():
    """
    Return (meo_min_id, meo_max_id) inclusive for MEO satellites.

    Hypatia assigns contiguous node IDs: LEO [0 .. leo_num_sats-1], then MEO
    [leo_num_sats .. leo_num_sats+meo_num_sats-1], then ground stations.

    Derived from main_kuiper_630_meo.py when importable; else fallback for Kuiper-630+MEO.
    """
    sys.path.insert(0, _STATE_DIR)
    try:
        import main_kuiper_630_meo as k

        leo_n = k.LEO_NUM_ORBS * k.LEO_NUM_SATS_PER_ORB
        meo_n = k.MEO_NUM_ORBS * k.MEO_NUM_SATS_PER_ORB
        meo_min = leo_n
        meo_max = leo_n + meo_n - 1
        return meo_min, meo_max
    except Exception:
        return 1156, 1191


def run_ns3(run_dir, _multilayer_dir=None):
    """
    run_dir: relative path under multilayer dir, e.g. runs/foo_tcp

    Caller should ``os.chdir`` to the multilayer directory first (same as original scripts).
    """
    # Ensure logs directory exists for tee (some scripts create it, some don't).
    resolved = _resolve_run_dir(run_dir, multilayer_dir=_multilayer_dir)
    _local_shell.make_full_dir(os.path.join(resolved, "logs_ns3"))
    sim_cmd = (
        "cd ../../../ns3-sat-sim/simulator; "
        # tee writes to a relative path; ensure the target directory exists relative to this cwd.
        "mkdir -p '../../paper/ns3_experiments/multilayer/%s/logs_ns3' && "
        "./waf --run=\"main_satnet --run_dir='../../paper/ns3_experiments/multilayer/%s'\" "
        "2>&1 | tee '../../paper/ns3_experiments/multilayer/%s/logs_ns3/console.txt'"
    ) % (run_dir, run_dir, run_dir)
    _local_shell.perfect_exec(sim_cmd, output_redirect=exputil.OutputRedirect.CONSOLE)


# Same flow id / rate-plot interval as step_3_generate_plots.py
_PLOT_TCP_FLOW_ID = 0
_PLOT_RATE_INTERVAL_NS = 1 * 1000 * 1000 * 1000
_PLOT_PING_OUT_OF_ORDER_INTERVAL_NS = 1 * 1000 * 1000 * 1000


def _parse_from_to_ids_from_pings_run_name(run_name):
    """
    Extract (from_id, to_id) from names like:
      leo_only_1160_to_1185_pings
      multilayer_1196_to_1221_pings
      threshold_test_1192_to_1204_pings
    """
    m = re.match(r"^.*_(\d+)_to_(\d+)_pings$", run_name)
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def _extract_out_of_order_rate_from_pingmesh(pingmesh_path, from_id, to_id, interval_ns):
    """
    Best-effort out-of-order rate from pingmesh.csv.

    Mirrors the interval counting logic in ns-3-sat-sim's plot_ping tool:
      - mark a ping out-of-order if it is LOST OR if its receive_reply_timestamp is
        greater than any later ping's receive_reply_timestamp (reverse scan).
      - count out-of-order events in fixed intervals starting at t=0.
      - report: total_out_of_order / total_time_seconds
    """
    if not os.path.isfile(pingmesh_path) or from_id is None or to_id is None or interval_ns <= 0:
        return float("nan")

    pings = []
    with open(pingmesh_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) < 10:
                continue
            try:
                f_id = int(parts[0])
                t_id = int(parts[1])
                send_ts = int(parts[3])
                receive_reply_ts = int(parts[5])
                arrived = parts[9].strip()
            except ValueError:
                continue
            if f_id != from_id or t_id != to_id:
                continue
            pings.append(
                {
                    "send_request_timestamp": send_ts,
                    "receive_reply_timestamp": receive_reply_ts,
                    "is_lost": arrived != "YES",
                }
            )

    if not pings:
        return float("nan")

    is_out_of_order = [False] * len(pings)
    current_lowest_timestamp = 10**30
    for i in reversed(range(len(pings))):
        entry = pings[i]
        if entry["is_lost"]:
            is_out_of_order[i] = True
            continue
        rx = entry["receive_reply_timestamp"]
        if rx > current_lowest_timestamp:
            is_out_of_order[i] = True
        current_lowest_timestamp = min(current_lowest_timestamp, rx)

    interval_counts = {}
    max_send_ts = max(p["send_request_timestamp"] for p in pings if p["send_request_timestamp"] >= 0)
    last_interval_idx = int(max_send_ts // interval_ns)
    for i, entry in enumerate(pings):
        if not is_out_of_order[i]:
            continue
        idx = int(entry["send_request_timestamp"] // interval_ns)
        interval_counts[idx] = interval_counts.get(idx, 0) + 1

    total_out_of_order = sum(interval_counts.values())
    total_intervals = last_interval_idx + 1
    total_time_s = (total_intervals * interval_ns) / 1e9
    if not total_time_s or total_time_s <= 0:
        return float("nan")
    return float(total_out_of_order) / float(total_time_s)


def run_plot_tcp_flow(run_name, multilayer_dir=None, tcp_flow_id=None):
    """
    Run gnuplot ``plot_tcp_flow.py`` for ``runs/<run_name>/`` (identical invocation to
    ``step_3_generate_plots.py``). Creates ``pdf/<run_name>/`` and ``data/<run_name>/``.

    Returns True if the plotter completed, False if skipped (missing or empty
    ``tcp_flow_*_progress.csv``) or gnuplot had no valid points.

    Caller should ``os.chdir`` to the multilayer directory unless ``multilayer_dir`` is absolute.
    """
    if tcp_flow_id is None:
        tcp_flow_id = _PLOT_TCP_FLOW_ID
    base = multilayer_dir or MULTILAYER_DIR
    progress = os.path.join(base, "runs", run_name, "logs_ns3", "tcp_flow_%d_progress.csv" % tcp_flow_id)
    if not os.path.isfile(progress) or os.path.getsize(progress) == 0:
        print("WARNING: skip plot_tcp_flow for %s (missing or empty %s)" % (run_name, os.path.basename(progress)))
        return False

    _local_shell.make_full_dir(os.path.join(base, "pdf", run_name))
    _local_shell.make_full_dir(os.path.join(base, "data", run_name))

    cmd = (
        "cd ../../../ns3-sat-sim/simulator/contrib/basic-sim/tools/plotting/plot_tcp_flow; "
        "python plot_tcp_flow.py "
        "../../../../../../../paper/ns3_experiments/multilayer/runs/%s/logs_ns3 "
        "../../../../../../../paper/ns3_experiments/multilayer/data/%s "
        "../../../../../../../paper/ns3_experiments/multilayer/pdf/%s "
        "%d %d"
    ) % (run_name, run_name, run_name, tcp_flow_id, _PLOT_RATE_INTERVAL_NS)

    try:
        _local_shell.perfect_exec(cmd, output_redirect=exputil.OutputRedirect.CONSOLE)
    except Exception as e:
        err = str(e)
        if "no valid points" in err or "x range is invalid" in err:
            print("WARNING: plot_tcp_flow gnuplot skip %s: %s" % (run_name, err))
            return False
        raise

    # Derived time-series CSVs requested in the thesis metrics list.
    # - computed_rtt_ms_ts: currently best-effort alias of TCP RTT.
    # - bdp_plus_q_packets_ts: best-effort proxy using cwnd_packets (BDP+queue ~= cwnd).
    try:
        data_root = multilayer_dir or MULTILAYER_DIR
        data_dir = os.path.join(data_root, "data", run_name)
        pdf_dir = os.path.join(data_root, "pdf", run_name)
        os.makedirs(pdf_dir, exist_ok=True)
        rtt_file = os.path.join(data_dir, "tcp_flow_%d_rtt.csv" % tcp_flow_id)
        cwnd_file = os.path.join(data_dir, "tcp_flow_%d_cwnd.csv" % tcp_flow_id)

        computed_rtt_out = os.path.join(data_dir, "computed_rtt_ms_ts.csv")
        bdp_plus_q_out = os.path.join(data_dir, "bdp_plus_q_packets_ts.csv")

        if os.path.isfile(rtt_file) and os.path.getsize(rtt_file) > 0:
            # Input: [flow_id,time_ns,rtt_ns] -> Output: [time_ns,rtt_ms]
            with open(rtt_file, "r") as f_in, open(computed_rtt_out, "w") as f_out:
                for line in f_in:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(",")
                    if len(parts) < 3:
                        continue
                    try:
                        t_ns = float(parts[1])
                        rtt_ms = float(parts[2]) / 1e6
                    except ValueError:
                        continue
                    f_out.write("%.0f,%.10f\n" % (t_ns, rtt_ms))
        # Plot computed RTT (ms) if matplotlib is available.
        try:
            if os.path.isfile(computed_rtt_out) and os.path.getsize(computed_rtt_out) > 0:
                import matplotlib
                matplotlib.use("Agg")
                import matplotlib.pyplot as plt

                xs = []
                ys = []
                with open(computed_rtt_out, "r") as f_in:
                    for line in f_in:
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split(",")
                        if len(parts) < 2:
                            continue
                        xs.append(float(parts[0]) / 1e9)
                        ys.append(float(parts[1]))

                if xs:
                    plt.figure(figsize=(7.5, 4.5))
                    plt.plot(xs, ys, lw=2)
                    plt.xlabel("Time (s)")
                    plt.ylabel("Computed RTT (ms)")
                    plt.grid(True, alpha=0.3)
                    plt.tight_layout()
                    plt.savefig(os.path.join(pdf_dir, "plot_computed_rtt_ms_ts.pdf"))
                    plt.close()
        except Exception:
            pass

        if os.path.isfile(cwnd_file) and os.path.getsize(cwnd_file) > 0:
            # Input: [flow_id,time_ns,cwnd_packets] -> Output: [time_ns,cwnd_packets]
            with open(cwnd_file, "r") as f_in, open(bdp_plus_q_out, "w") as f_out:
                for line in f_in:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(",")
                    if len(parts) < 3:
                        continue
                    try:
                        t_ns = float(parts[1])
                        cwnd_pkts = float(parts[2])
                    except ValueError:
                        continue
                    f_out.write("%.0f,%.10f\n" % (t_ns, cwnd_pkts))
        # Plot BDP+Q proxy (packets) if matplotlib is available.
        try:
            if os.path.isfile(bdp_plus_q_out) and os.path.getsize(bdp_plus_q_out) > 0:
                import matplotlib
                matplotlib.use("Agg")
                import matplotlib.pyplot as plt

                xs = []
                ys = []
                with open(bdp_plus_q_out, "r") as f_in:
                    for line in f_in:
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split(",")
                        if len(parts) < 2:
                            continue
                        xs.append(float(parts[0]) / 1e9)
                        ys.append(float(parts[1]))

                if xs:
                    plt.figure(figsize=(7.5, 4.5))
                    plt.plot(xs, ys, lw=2)
                    plt.xlabel("Time (s)")
                    plt.ylabel("BDP+Q (packets) [proxy = cwnd]")
                    plt.grid(True, alpha=0.3)
                    plt.tight_layout()
                    plt.savefig(os.path.join(pdf_dir, "plot_bdp_plus_q_packets_ts.pdf"))
                    plt.close()
        except Exception:
            pass
    except Exception:
        # Derived CSVs are supplementary; ignore failures.
        pass
    return True


def run_plot_ping(run_name, multilayer_dir=None, from_id=None, to_id=None, plot_interval_ns=None):
    """
    Run ``plot_ping.py`` for ``runs/<run_name>/`` (same invocation as ``step_3_generate_plots.py``).

    Creates ``pdf/<run_name>/`` and ``data/<run_name>/`` with per-pair RTT CSVs.
    ``from_id`` / ``to_id`` default to values parsed from ``*_<from>_to_<to>_pings`` names.
    ``plot_interval_ns`` defaults to 1e9 (1 s buckets), matching step_3.
    """
    if from_id is None or to_id is None:
        from_id, to_id = _parse_from_to_ids_from_pings_run_name(run_name)
    if from_id is None or to_id is None:
        print("WARNING: run_plot_ping: could not parse from/to from run name %r" % run_name)
        return False
    if plot_interval_ns is None:
        plot_interval_ns = 1 * 1000 * 1000 * 1000

    base = multilayer_dir or MULTILAYER_DIR
    ping_file = os.path.join(base, "runs", run_name, "logs_ns3", "pingmesh.csv")
    if not os.path.isfile(ping_file):
        print("WARNING: skip run_plot_ping %s (missing logs_ns3/pingmesh.csv)" % run_name)
        return False

    _local_shell.make_full_dir(os.path.join(base, "pdf", run_name))
    _local_shell.make_full_dir(os.path.join(base, "data", run_name))

    cmd = (
        "cd ../../../ns3-sat-sim/simulator/contrib/basic-sim/tools/plotting/plot_ping; "
        "python plot_ping.py "
        "../../../../../../../paper/ns3_experiments/multilayer/runs/%s/logs_ns3 "
        "../../../../../../../paper/ns3_experiments/multilayer/data/%s "
        "../../../../../../../paper/ns3_experiments/multilayer/pdf/%s "
        "%d %d %d"
    ) % (run_name, run_name, run_name, from_id, to_id, int(plot_interval_ns))

    try:
        _local_shell.perfect_exec(cmd, output_redirect=exputil.OutputRedirect.CONSOLE)
    except Exception as e:
        print("ERROR: run_plot_ping failed for %s: %s" % (run_name, e))
        return False
    return True


def _resolve_run_dir(run_dir, multilayer_dir=None):
    base = multilayer_dir or MULTILAYER_DIR
    if os.path.isabs(run_dir):
        return run_dir
    return os.path.normpath(os.path.join(base, run_dir))


def _read_schedule_max_bytes(run_dir, multilayer_dir=None):
    """Parse template schedule line: flow_id, from, to, max_bytes, ..."""
    run_dir = _resolve_run_dir(run_dir, multilayer_dir)
    return _read_schedule_max_bytes_resolved(run_dir)


def _read_schedule_max_bytes_resolved(resolved_run_dir):
    """Same as _read_schedule_max_bytes but ``resolved_run_dir`` is already absolute."""
    path = os.path.join(resolved_run_dir, "schedule.csv")
    if not os.path.isfile(path):
        return None
    with open(path, "r") as f:
        line = f.readline().strip()
    if not line:
        return None
    parts = line.split(",")
    if len(parts) < 4:
        return None
    try:
        return int(parts[3])
    except ValueError:
        return None


def _isl_stats_max_mean_nz(utils):
    """Return (max_util, mean_util_over_nonzero) from a list of utilizations in [0,1]."""
    if not utils:
        # No logged edges in this class: peak load is 0; mean over non-zero is undefined.
        return 0.0, float("nan")
    mx = max(utils)
    nz = [u for u in utils if u > 1e-12]
    mn = (sum(nz) / len(nz)) if nz else float("nan")
    return mx, mn


def extract_meo_isl_metrics(run_dir, multilayer_dir=None):
    """
    Proxy metrics from logs_ns3/isl_utilization.csv (src,dst, t0, t1, util in [0,1]).

    Categories (satellite ISLs only, both endpoints <= meo_max):
      - leo_leo_*: LEO–LEO ISLs (max / mean over nonzero utilizations on those edges)
      - meo_meo_*: MEO–MEO ISLs

    meo_touching_* uses any ISL with at least one MEO satellite endpoint (same as before),
    including MEO–ground feeder links when present in the CSV.

    Thesis note: for multilayer routing, leo_leo_isl_max_util can be very small while
    MEO-class metrics rise — that indicates less congestion on the LEO mesh (hot-spot
    offload), not that LEO satellites are unused.

    See module docstring: link utilization aggregates, not per-flow path proof.
    """
    run_dir = _resolve_run_dir(run_dir, multilayer_dir)
    path = os.path.join(run_dir, "logs_ns3", "isl_utilization.csv")
    meo_lo, meo_hi = get_meo_node_id_range()

    def is_leo_sat(i):
        return 0 <= i < meo_lo

    def is_meo_sat(i):
        return meo_lo <= i <= meo_hi

    def both_satellites(a, b):
        return 0 <= a <= meo_hi and 0 <= b <= meo_hi

    out = {
        "leo_leo_isl_max_util": float("nan"),
        "leo_leo_isl_mean_util_nz": float("nan"),
        "meo_touching_isl_max_util": float("nan"),
        "meo_meo_isl_max_util": float("nan"),
        "meo_touching_isl_mean_util_nz": float("nan"),
        "meo_meo_isl_mean_util_nz": float("nan"),
        "meo_used_any": False,
    }
    if not os.path.isfile(path):
        return out
    leo_leo = []
    meo_meo = []
    touching = []
    with open(path, "r") as fp:
        for line in fp:
            parts = line.strip().split(",")
            if len(parts) < 5:
                continue
            try:
                a, b = int(parts[0]), int(parts[1])
                util = float(parts[4])
            except ValueError:
                continue
            ta = is_meo_sat(a)
            tb = is_meo_sat(b)
            if ta or tb:
                touching.append(util)
                if util > 1e-12:
                    out["meo_used_any"] = True
            if both_satellites(a, b):
                if is_leo_sat(a) and is_leo_sat(b):
                    leo_leo.append(util)
                elif ta and tb:
                    meo_meo.append(util)
    mx, mn = _isl_stats_max_mean_nz(leo_leo)
    out["leo_leo_isl_max_util"] = mx
    out["leo_leo_isl_mean_util_nz"] = mn
    mx, mn = _isl_stats_max_mean_nz(meo_meo)
    out["meo_meo_isl_max_util"] = mx
    out["meo_meo_isl_mean_util_nz"] = mn
    mx, mn = _isl_stats_max_mean_nz(touching)
    out["meo_touching_isl_max_util"] = mx
    out["meo_touching_isl_mean_util_nz"] = mn
    return out


def _parse_kv_properties(path):
    """Parse simple key=value properties files (ignores blank lines)."""
    props = {}
    if not os.path.isfile(path):
        return props
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip()
            # Some config values are quoted (e.g. ".../dynamic_state_...").
            if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
                v = v[1:-1].strip()
            props[k.strip()] = v
    return props


def _load_schedule_from_to(run_dir):
    """Parse schedule.csv: flow_id, from_id, to_id, ... . Return (from_id, to_id)."""
    schedule_path = os.path.join(run_dir, "schedule.csv")
    if not os.path.isfile(schedule_path):
        return None, None
    with open(schedule_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) < 3:
                continue
            try:
                return int(parts[1]), int(parts[2])
            except ValueError:
                continue
    return None, None


def _resolve_dynamic_state_dir_from_config(resolved_run_dir):
    """
    Resolve satellite_network_routes_dir from config_ns3.properties into an absolute directory.
    """
    cfg_path = os.path.join(resolved_run_dir, "config_ns3.properties")
    props = _parse_kv_properties(cfg_path)
    routes_dir_rel = props.get("satellite_network_routes_dir")
    if not routes_dir_rel:
        return None
    # config values are relative to the run directory
    return os.path.normpath(os.path.join(resolved_run_dir, routes_dir_rel))


def _read_sim_end_time_ns(resolved_run_dir):
    cfg_path = os.path.join(resolved_run_dir, "config_ns3.properties")
    props = _parse_kv_properties(cfg_path)
    try:
        return int(props.get("simulation_end_time_ns", "0"))
    except ValueError:
        return 0


def _get_satellite_counts_from_config(resolved_run_dir):
    """
    Return (leo_num_sats, total_satellites, meo_min_id, meo_max_id_or_none).

    Node IDs are assumed contiguous:
      LEO: [0 .. leo_num_sats-1]
      MEO: [leo_num_sats .. total_satellites-1] (if present)
      GS:  [total_satellites .. ...]
    """
    cfg_path = os.path.join(resolved_run_dir, "config_ns3.properties")
    props = _parse_kv_properties(cfg_path)
    satnet_dir = props.get("satellite_network_dir", "")

    # Use main_kuiper_630* constants for exact shell sizes.
    sys.path.insert(0, _STATE_DIR)
    try:
        if "kuiper_630_meo" in satnet_dir:
            import main_kuiper_630_meo as k  # type: ignore

            leo_n = k.LEO_NUM_ORBS * k.LEO_NUM_SATS_PER_ORB
            meo_n = k.MEO_NUM_ORBS * k.MEO_NUM_SATS_PER_ORB
            total = leo_n + meo_n
            return leo_n, total, leo_n, total - 1
        else:
            import main_kuiper_630 as k  # type: ignore

            leo_n = k.NUM_ORBS * k.NUM_SATS_PER_ORB
            return leo_n, leo_n, None, None
    except Exception:
        # Fallback for Kuiper-630 + MEO
        if "meo" in satnet_dir:
            return 1156, 1192, 1156, 1191
        return 1156, 1156, None, None


def _reconstruct_paths_from_fstate(fstate_files_in_time_order, from_id, to_id, leo_num_sats, total_sats):
    """
    Reconstruct forwarding paths at each timestep by merging fstate deltas.

    Returns list of dicts:
      {time_ns, valid, path_nodes, hop_count, meo_sat_count, meo_usage_ratio, signature}
    """
    next_map = {}  # src_id -> next_hop_id for a fixed destination to_id
    results = []
    max_hops = 60

    for t_ns, fp in fstate_files_in_time_order:
        # Apply delta updates for this timestep.
        with open(fp, "r") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) < 3:
                    continue
                try:
                    src = int(parts[0])
                    dst = int(parts[1])
                    if dst != to_id:
                        continue
                    nh = int(parts[2])
                    next_map[src] = nh
                except (ValueError, IndexError):
                    continue

        # Attempt to reconstruct the path using cumulative next_map.
        valid = False
        path_nodes = []
        hop_count = float("nan")
        meo_usage_ratio = float("nan")
        signature = None
        meo_sat_count = 0

        if from_id in next_map:
            current = next_map.get(from_id)
            if current is not None and current != -1:
                path_nodes = [from_id]
                # Walk until we reach the destination ground station or fail.
                for _ in range(max_hops):
                    path_nodes.append(current)
                    if current == to_id:
                        valid = True
                        break
                    nxt = next_map.get(current)
                    if nxt is None or nxt == -1:
                        valid = False
                        break
                    current = nxt

        if valid:
            hop_count_int = len([n for n in path_nodes if isinstance(n, int) and n < total_sats])
            meo_sat_count = len([n for n in path_nodes if isinstance(n, int) and leo_num_sats is not None and leo_num_sats <= n < total_sats])
            hop_count = hop_count_int
            if hop_count_int > 0:
                meo_usage_ratio = float(meo_sat_count) / float(hop_count_int)
            else:
                meo_usage_ratio = 0.0
            signature = tuple([n for n in path_nodes if isinstance(n, int) and n < total_sats])

        results.append(
            {
                "time_ns": t_ns,
                "valid": valid,
                "path_nodes": path_nodes if valid else None,
                "hop_count": hop_count,
                "meo_sat_count": meo_sat_count if valid else None,
                "meo_usage_ratio": meo_usage_ratio if valid else None,
                "signature": signature,
            }
        )

    return results


def _load_isl_utilization_for_edges(isl_util_path, needed_edges):
    """Load util values from isl_utilization.csv only for edges in needed_edges."""
    util = {}
    if not os.path.isfile(isl_util_path):
        return util
    if not needed_edges:
        return util
    with open(isl_util_path, "r") as fp:
        for line in fp:
            parts = line.strip().split(",")
            if len(parts) < 5:
                continue
            try:
                a, b = int(parts[0]), int(parts[1])
                key = (a, b)
                if key not in needed_edges:
                    continue
                util_val = float(parts[4])
                util[key] = util_val
            except (ValueError, IndexError):
                continue
    return util


def _compute_bottleneck_utilization(paths, isl_util_dict):
    """
    For each valid path signature, take min util along each consecutive edge on the reconstructed
    path (sat<->sat and sat<->GS edges are included if present in isl_utilization.csv).
    """
    vals = []
    for p in paths:
        if not p.get("valid"):
            continue
        nodes = p.get("path_nodes")
        if not nodes or len(nodes) < 2:
            continue
        edge_utils = []
        for i in range(len(nodes) - 1):
            u = nodes[i]
            v = nodes[i + 1]
            if not isinstance(u, int) or not isinstance(v, int):
                continue
            if (u, v) in isl_util_dict:
                edge_utils.append(isl_util_dict[(u, v)])
            elif (v, u) in isl_util_dict:
                edge_utils.append(isl_util_dict[(v, u)])
        if edge_utils:
            vals.append(min(edge_utils))
    if not vals:
        return float("nan")
    return sum(vals) / len(vals)


def _extract_path_based_metrics(run_dir, resolved_run_dir):
    """
    Compute path-based metrics (hop count, MEO usage ratio, stability, stretch, bottleneck util)
    by reconstructing forwarding paths from fstate_*.txt.

    These metrics are approximations for end-to-end behavior:
      - forwarding paths are reconstructed at each dynamic snapshot (simulation update interval)
      - stability uses whether the satellite-only path signature changes between consecutive snapshots
      - stretch is computed as hop_count / min_hop_count_over_snapshots for that (from,to)
      - bottleneck utilization is computed from isl_utilization.csv aggregated over the run
    """
    from_id, to_id = _load_schedule_from_to(resolved_run_dir)
    if from_id is None or to_id is None:
        return {}

    dynamic_state_dir = _resolve_dynamic_state_dir_from_config(resolved_run_dir)
    if not dynamic_state_dir or not os.path.isdir(dynamic_state_dir):
        return {}

    sim_end_time_ns = _read_sim_end_time_ns(resolved_run_dir)
    leo_num_sats, total_sats, meo_min, meo_max = _get_satellite_counts_from_config(resolved_run_dir)

    # Collect fstate snapshots in time order (fstate files are deltas).
    fstate_files = []
    for fp in glob.glob(os.path.join(dynamic_state_dir, "fstate_*.txt")):
        base = os.path.basename(fp)
        try:
            t_ns = int(base.replace("fstate_", "").replace(".txt", ""))
        except ValueError:
            continue
        if t_ns <= sim_end_time_ns:
            fstate_files.append((t_ns, fp))
    fstate_files.sort(key=lambda x: x[0])
    if not fstate_files:
        return {}

    merged_paths = _reconstruct_paths_from_fstate(
        fstate_files, from_id, to_id, leo_num_sats, total_sats
    )

    valid_paths = [p for p in merged_paths if p.get("valid")]
    if not valid_paths:
        return {
            "avg_hop_count": float("nan"),
            "avg_path_stretch": float("nan"),
            "path_stability_ratio": float("nan"),
            "bottleneck_utilization": float("nan"),
            "meo_usage_ratio": float("nan"),
            "path_change_count": float("nan"),
            "hop_count_variation": float("nan"),
            "hop_count_ratio": float("nan"),
        }

    hop_counts = [p["hop_count"] for p in valid_paths if isinstance(p.get("hop_count"), (int, float))]
    meo_ratios = [p["meo_usage_ratio"] for p in valid_paths if p.get("meo_usage_ratio") is not None]
    min_hops = min(hop_counts) if hop_counts else None

    # Path change count: how often the forwarding path signature changes between
    # consecutive *valid* snapshots.
    hop_count_variation = float("nan")
    hop_count_ratio = float("nan")
    path_change_count = float("nan")
    if hop_counts:
        max_hops = max(hop_counts)
        if min_hops is not None:
            hop_count_variation = float(max_hops - min_hops)
            hop_count_ratio = float(max_hops) / float(min_hops) if min_hops > 0 else float("nan")

    # Only compare signatures on valid snapshots to avoid "invalid -> invalid" or
    # "invalid -> valid" artifacts.
    valid_sigs = [p.get("signature") for p in merged_paths if p.get("valid") and p.get("signature") is not None]
    if len(valid_sigs) >= 2:
        path_change_count = float(sum(1 for i in range(1, len(valid_sigs)) if valid_sigs[i] != valid_sigs[i - 1]))

    # Stability ratio: unchanged path signature over consecutive valid snapshots.
    unchanged = 0
    compared = 0
    prev_sig = None
    for p in merged_paths:
        if not p.get("valid"):
            prev_sig = None
            continue
        sig = p.get("signature")
        if sig is None:
            prev_sig = None
            continue
        if prev_sig is None:
            prev_sig = sig
            continue
        compared += 1
        if sig == prev_sig:
            unchanged += 1
        prev_sig = sig
    stability_ratio = (float(unchanged) / float(compared)) if compared > 0 else float("nan")

    # Stretch: hop_count relative to minimum hop_count seen over snapshots.
    if min_hops is None or min_hops == 0:
        stretches = [1.0 for _ in valid_paths]
    else:
        stretches = [float(p["hop_count"]) / float(min_hops) for p in valid_paths if p.get("hop_count") is not None]
    avg_stretch = (sum(stretches) / len(stretches)) if stretches else float("nan")

    avg_hops = sum(hop_counts) / len(hop_counts) if hop_counts else float("nan")
    avg_meo_ratio = sum(meo_ratios) / len(meo_ratios) if meo_ratios else float("nan")

    # Bottleneck utilization: min util across edges on the reconstructed path.
    isl_util_path = os.path.join(resolved_run_dir, "logs_ns3", "isl_utilization.csv")
    needed_edges = set()
    for p in merged_paths:
        if not p.get("valid"):
            continue
        nodes = p.get("path_nodes")
        if not nodes or len(nodes) < 2:
            continue
        for i in range(len(nodes) - 1):
            u = nodes[i]
            v = nodes[i + 1]
            if isinstance(u, int) and isinstance(v, int) and u != v:
                needed_edges.add((u, v))
                needed_edges.add((v, u))
    isl_util_dict = _load_isl_utilization_for_edges(isl_util_path, needed_edges)
    bottleneck = _compute_bottleneck_utilization(merged_paths, isl_util_dict)

    return {
        "avg_hop_count": avg_hops,
        "avg_path_stretch": avg_stretch,
        "path_stability_ratio": stability_ratio,
        "bottleneck_utilization": bottleneck,
        "meo_usage_ratio": avg_meo_ratio,
        "path_change_count": path_change_count,
        "hop_count_variation": hop_count_variation,
        "hop_count_ratio": hop_count_ratio,
    }


def extract_metrics(run_dir, tcp_flow_id=0, multilayer_dir=None):
    """
    Read ns-3 TCP logs under run_dir/logs_ns3 and compute aggregated metrics.

    Uses:
      tcp_flow_<id>_rate_in_intervals.csv  (if present; else derived from progress)
      tcp_flow_<id>_rtt.csv
      tcp_flow_<id>_progress.csv
    """
    resolved = _resolve_run_dir(run_dir, multilayer_dir)
    data_dir = os.path.join(resolved, "logs_ns3")
    base = os.path.join(data_dir, "tcp_flow_%d" % tcp_flow_id)

    out = {
        "avg_throughput_mbps": float("nan"),
        "avg_rtt_ms": float("nan"),
        "rtt_variation_ms": float("nan"),
        "rtt_variation_ratio": float("nan"),
        "geodesic_rtt_ms": float("nan"),
        "rtt_stretch": float("nan"),
        "completion_time_s": float("nan"),
        "active_transfer_duration_s": float("nan"),
        "transfer_complete": False,
        "bytes_transferred_final": None,
        "leo_leo_isl_max_util": float("nan"),
        "leo_leo_isl_mean_util_nz": float("nan"),
        "meo_touching_isl_max_util": float("nan"),
        "meo_meo_isl_max_util": float("nan"),
        "meo_touching_isl_mean_util_nz": float("nan"),
        "meo_meo_isl_mean_util_nz": float("nan"),
        "meo_used_any": False,
        "out_of_order_rate": float("nan"),
        "error": None,
    }

    if not os.path.isdir(data_dir):
        out["error"] = "missing logs_ns3: %s" % data_dir
        return out

    # Optional ping (out-of-order) metrics (for *_pings runs).
    pingmesh_path = os.path.join(data_dir, "pingmesh.csv")
    if os.path.isfile(pingmesh_path):
        run_name = os.path.basename(os.path.normpath(resolved))
        from_id, to_id = _parse_from_to_ids_from_pings_run_name(run_name)
        if from_id is not None and to_id is not None:
            out["out_of_order_rate"] = _extract_out_of_order_rate_from_pingmesh(
                pingmesh_path,
                from_id,
                to_id,
                interval_ns=_PLOT_PING_OUT_OF_ORDER_INTERVAL_NS,
            )

    progress_path = base + "_progress.csv"
    rtt_path = base + "_rtt.csv"
    rate_path = base + "_rate_in_intervals.csv"

    times_ns = []
    bytes_prog = []
    if os.path.isfile(progress_path):
        with open(progress_path, "r") as f:
            for row in csv.reader(f):
                if len(row) < 3:
                    continue
                try:
                    times_ns.append(int(float(row[1])))
                    bytes_prog.append(int(float(row[2])))
                except ValueError:
                    continue
        if bytes_prog:
            out["bytes_transferred_final"] = bytes_prog[-1]

    if os.path.isfile(rate_path):
        rates = []
        with open(rate_path, "r") as f:
            for row in csv.reader(f):
                if len(row) < 3:
                    continue
                try:
                    rates.append(float(row[2]))
                except ValueError:
                    continue
        if rates:
            nz = [r for r in rates if r > 1e-12]
            use = nz if nz else rates
            out["avg_throughput_mbps"] = sum(use) / len(use)
    elif len(times_ns) >= 2 and bytes_prog:
        dt_s = (times_ns[-1] - times_ns[0]) / 1e9
        if dt_s > 0:
            db = bytes_prog[-1] - bytes_prog[0]
            out["avg_throughput_mbps"] = (db * 8.0) / (dt_s * 1e6)

    if os.path.isfile(rtt_path):
        rtts_ns = []
        with open(rtt_path, "r") as f:
            for row in csv.reader(f):
                if len(row) < 3:
                    continue
                try:
                    rtts_ns.append(float(row[2]))
                except ValueError:
                    continue
        if rtts_ns:
            rtts_ms = [x / 1e6 for x in rtts_ns]
            out["avg_rtt_ms"] = sum(rtts_ms) / len(rtts_ms)

            # RTT variation metrics (best-effort from TCP RTT time series).
            rtt_min = min(rtts_ms)
            rtt_max = max(rtts_ms)
            out["geodesic_rtt_ms"] = rtt_min
            out["rtt_variation_ms"] = float(rtt_max - rtt_min)
            out["rtt_variation_ratio"] = (float(rtt_max) / float(rtt_min)) if rtt_min > 0 else float("nan")
            out["rtt_stretch"] = (out["avg_rtt_ms"] / rtt_min) if rtt_min > 0 else float("nan")

    t_first_byte = None
    if bytes_prog and times_ns:
        for t, b in zip(times_ns, bytes_prog):
            if b > 0:
                t_first_byte = t
                break
    if t_first_byte is not None and times_ns:
        out["active_transfer_duration_s"] = (times_ns[-1] - t_first_byte) / 1e9

    max_bytes = _read_schedule_max_bytes_resolved(resolved)

    if max_bytes is not None and len(times_ns) >= 1 and bytes_prog:
        t0 = t_first_byte
        if t0 is not None:
            for t, b in zip(times_ns, bytes_prog):
                if b >= max_bytes:
                    out["completion_time_s"] = (t - t0) / 1e9
                    out["transfer_complete"] = True
                    break
            if not out["transfer_complete"]:
                out["completion_time_s"] = float("nan")

    out.update(extract_meo_isl_metrics(resolved, multilayer_dir=None))

    # Path-based metrics (hop/stability/stretch/bottleneck/meo usage)
    # These are best-effort: if dynamic_state or fstate snapshots are missing, they remain NaN.
    try:
        out.update(_extract_path_based_metrics(run_dir, resolved))
    except Exception:
        # Keep extraction robust; path metrics are supplementary.
        pass
    return out


def export_results_csv(results, csv_path):
    """Write thesis table (CSV). Uses pandas if available."""
    if not results:
        print("No results to export.")
        return
    if pd is not None:
        df = pd.DataFrame(results)
        df.to_csv(csv_path, index=False)
    else:
        fieldnames = list(results[0].keys())
        with open(csv_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(results)
    print("Wrote thesis table: %s (%d rows)" % (csv_path, len(results)))

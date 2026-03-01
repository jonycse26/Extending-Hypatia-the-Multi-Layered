#!/usr/bin/env python3
"""
Explain why each satellite in a path was chosen (why these satellites, not others).

For a given GS→GS pair and time step, traces the path from fstate and at each hop shows:
- Which routing case applies (GS→LEO source choice, Case A/B/C, or MEO gateway routing)
- The target used (dst_sat, best_meo_sat, or gateway_meo)
- All candidate next hops considered by the algorithm and their scores (edge + dist to target)
- Which one was chosen and why (lowest score)

Usage:
  python3 explain_path_decisions.py [from_id to_id] [time_s]
  Default: from_id=1192, to_id=1204 (Tokyo→Buenos-Aires), time_s=0

Example:
  python3 explain_path_decisions.py 1192 1204 5.0
"""

import os
import sys
import math

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '../../../satgenpy')))
sys.path.insert(0, SCRIPT_DIR)

import run_list
import numpy as np
import networkx as nx
from astropy import units as u

from satgen.tles import read_tles
from satgen.ground_stations import read_ground_stations_extended
from satgen.description import read_description
from satgen.isls import read_isls
from satgen.distance_tools import distance_m_between_satellites, distance_m_ground_station_to_satellite


def build_constellation_state(constellation_dir, time_ns):
    """Build graph, dist, hop_meo, ground_station_satellites_in_range at time_ns."""
    tles = read_tles(os.path.join(constellation_dir, 'tles.txt'))
    satellites = tles["satellites"]
    epoch = tles["epoch"]
    time = epoch + time_ns * u.ns
    num_sats = len(satellites)

    description = read_description(os.path.join(constellation_dir, 'description.txt'))
    leo_num_sats = int(description.get('leo_num_sats', num_sats))
    max_gsl_length_m = float(description.get('max_gsl_length_m', 2e6))

    ground_stations = read_ground_stations_extended(os.path.join(constellation_dir, 'ground_stations.txt'))
    list_isls = read_isls(os.path.join(constellation_dir, 'isls.txt'), num_sats)

    # Satellite graph with weights at this time
    G = nx.Graph()
    for i in range(num_sats):
        G.add_node(i)
    for (a, b) in list_isls:
        d = distance_m_between_satellites(satellites[a], satellites[b], str(epoch), str(time))
        G.add_edge(a, b, weight=d)

    dist_np = np.asarray(nx.floyd_warshall_numpy(G))
    dist_np = np.where(np.isfinite(dist_np), dist_np, np.inf)

    # MEO hop distances
    meo_nodes = list(range(leo_num_sats, num_sats))
    meo_subgraph = G.subgraph(meo_nodes)
    hop_meo = dict(nx.all_pairs_shortest_path_length(meo_subgraph))

    # Ground station satellites in range (per GS)
    ground_station_satellites_in_range = []
    for gs in ground_stations:
        in_range = []
        for sid in range(num_sats):
            d = distance_m_ground_station_to_satellite(gs, satellites[sid], str(epoch), str(time))
            if d <= max_gsl_length_m:
                in_range.append((float(d), sid))
        ground_station_satellites_in_range.append(in_range)

    def is_leo(sid):
        return sid < leo_num_sats

    def is_meo(sid):
        return sid >= leo_num_sats

    return {
        'satellites': satellites,
        'ground_stations': ground_stations,
        'epoch': epoch,
        'time': time,
        'num_sats': num_sats,
        'leo_num_sats': leo_num_sats,
        'gs_start_id': num_sats,
        'G': G,
        'dist_np': dist_np,
        'hop_meo': hop_meo,
        'meo_nodes': meo_nodes,
        'ground_station_satellites_in_range': ground_station_satellites_in_range,
        'is_leo': is_leo,
        'is_meo': is_meo,
    }


def trace_path(fstate_dict, from_id, to_id, max_hops=25):
    """Return path as list of node IDs (including GS endpoints), or None."""
    if (from_id, to_id) not in fstate_dict or fstate_dict[(from_id, to_id)] == -1:
        return None
    path = [from_id]
    current = fstate_dict[(from_id, to_id)]
    hops = 0
    while current != to_id and current != -1 and hops < max_hops:
        path.append(current)
        if (current, to_id) not in fstate_dict:
            break
        next_hop = fstate_dict[(current, to_id)]
        if next_hop == to_id:
            path.append(to_id)
            break
        current = next_hop
        hops += 1
    if path[-1] != to_id:
        path.append(to_id)
    return path


def get_dst_sat_and_use_meo(state, curr, dst_gid, meo_threshold_distance_m=10e6, meo_threshold_hops=3):
    """Compute dst_sat and use_meo for (curr, dst_gs) as in the algorithm."""
    dst_gs_node_id = state['gs_start_id'] + dst_gid
    G = state['G']
    dist_np = state['dist_np']
    is_leo = state['is_leo']
    gs_in_range = state['ground_station_satellites_in_range'][dst_gid]

    possible_dst_sats = [(gsl_m, sid) for gsl_m, sid in gs_in_range if is_leo(sid)]
    possibilities = []
    for gsl_m, sat_id in possible_dst_sats:
        d = float(dist_np[curr, sat_id])
        if math.isinf(d):
            continue
        possibilities.append((d + gsl_m, sat_id))
    possibilities.sort()

    if not possibilities:
        return None, False, float('inf')

    dst_sat = possibilities[0][1]
    distance_to_ground_station_m = possibilities[0][0]

    use_meo = False
    if is_leo(curr):
        if distance_to_ground_station_m > meo_threshold_distance_m:
            use_meo = True
        else:
            d_c_dst = float(dist_np[curr, dst_sat])
            if not math.isinf(d_c_dst):
                avg_isl = 2000000.0
                estimated_hops = int(d_c_dst / avg_isl) + 1
                if estimated_hops > meo_threshold_hops:
                    use_meo = True

    return dst_sat, use_meo, distance_to_ground_station_m


def explain_hop(state, curr, next_hop, dst_gid, dst_gs_node_id, chosen_nh_from_fstate):
    """
    Explain why (curr -> chosen_nh_from_fstate) was chosen.
    Returns (case_str, target_id, list of (neighbor_id, edge_km, dist_to_target_km, score_km)).
    """
    G = state['G']
    dist_np = state['dist_np']
    hop_meo = state['hop_meo']
    meo_nodes = state['meo_nodes']
    is_leo = state['is_leo']
    is_meo = state['is_meo']

    dst_sat, use_meo, _ = get_dst_sat_and_use_meo(state, curr, dst_gid)
    if dst_sat is None:
        return "NO_PATH", None, []

    # Case A: curr == dst_sat -> deliver to GS
    if curr == dst_sat:
        return "Case A (deliver to GS)", dst_gs_node_id, []

    # Case B: LEO + use_meo
    if is_leo(curr) and use_meo:
        best_meo_sat = None
        best_total = float('inf')
        for m in meo_nodes:
            if math.isinf(float(dist_np[curr, m])) or math.isinf(float(dist_np[m, dst_sat])):
                continue
            t = float(dist_np[curr, m]) + float(dist_np[m, dst_sat])
            if t < best_total:
                best_total = t
                best_meo_sat = m

        if best_meo_sat is None:
            # Fallback LEO-only toward dst_sat
            candidates = []
            for n in G.neighbors(curr):
                if not is_leo(n):
                    continue
                w = G.edges[(curr, n)]['weight']
                d = float(dist_np[n, dst_sat])
                if math.isinf(d):
                    continue
                score = w + d
                candidates.append((n, w / 1000, d / 1000, score / 1000))
            candidates.sort(key=lambda x: x[3])
            return "Case B fallback (LEO-only toward dst_sat)", dst_sat, candidates

        # Target = best_meo_sat
        candidates = []
        for n in G.neighbors(curr):
            if not is_leo(n) and n != best_meo_sat:
                continue
            w = G.edges[(curr, n)]['weight']
            d = float(dist_np[n, best_meo_sat])
            if math.isinf(d):
                continue
            score = w + d
            candidates.append((n, w / 1000, d / 1000, score / 1000))
        candidates.sort(key=lambda x: x[3])
        return "Case B (enter MEO, target best_meo_sat)", best_meo_sat, candidates

    # Case C: LEO + not use_meo
    if is_leo(curr) and not use_meo:
        candidates = []
        for n in G.neighbors(curr):
            if not is_leo(n):
                continue
            w = G.edges[(curr, n)]['weight']
            d = float(dist_np[n, dst_sat])
            if math.isinf(d):
                continue
            score = w + d
            candidates.append((n, w / 1000, d / 1000, score / 1000))
        candidates.sort(key=lambda x: x[3])
        return "Case C (LEO-only to dst_sat)", dst_sat, candidates

    # MEO: gateway routing
    gateway_meo = None
    for g in meo_nodes:
        if G.has_edge(g, dst_sat):
            gateway_meo = g
            break

    if gateway_meo is None:
        return "MEO (no gateway)", None, []

    if G.has_edge(curr, dst_sat):
        w = G.edges[(curr, dst_sat)]['weight']
        return "MEO exit (curr is gateway → dst_sat)", dst_sat, [(dst_sat, w / 1000, 0, w / 1000)]

    try:
        h_curr = hop_meo[curr][gateway_meo]
    except KeyError:
        return "MEO (unreachable to gateway)", gateway_meo, []

    candidates = []
    for n in G.neighbors(curr):
        if not is_meo(n):
            continue
        try:
            h_nbr = hop_meo[n][gateway_meo]
        except KeyError:
            continue
        if h_nbr >= h_curr:
            continue
        w = G.edges[(curr, n)]['weight']
        d = float(dist_np[n, dst_sat])
        if math.isinf(d):
            continue
        score = w + d
        candidates.append((n, w / 1000, d / 1000, score / 1000))
    candidates.sort(key=lambda x: x[3])
    return "MEO (toward gateway_meo, then → dst_sat)", gateway_meo, candidates


def main():
    from_id = 1192
    to_id = 1204
    time_s = 0.0
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if len(args) >= 3:
        try:
            from_id = int(args[0])
            to_id = int(args[1])
            time_s = float(args[2])
        except ValueError:
            pass
    elif len(args) == 2:
        try:
            from_id = int(args[0])
            to_id = int(args[1])
        except ValueError:
            pass
    elif len(args) == 1:
        try:
            time_s = float(args[0])
        except ValueError:
            pass

    constellation_dir = os.path.abspath(os.path.join(
        SCRIPT_DIR, '../../satellite_networks_state/gen_data/', run_list.multilayer_satellite_network
    ))
    dynamic_dir = os.path.join(constellation_dir, 'dynamic_state_1000ms_for_5s')

    if not os.path.isdir(dynamic_dir):
        print("ERROR: Dynamic state dir not found:", dynamic_dir)
        return 1

    time_ns = int(time_s * 1e9)
    state = build_constellation_state(constellation_dir, time_ns)
    num_sats = state['num_sats']
    gs_start_id = state['gs_start_id']
    leo_num_sats = state['leo_num_sats']
    ground_stations = state['ground_stations']

    fstate_file = os.path.join(dynamic_dir, 'fstate_%d.txt' % time_ns)
    if not os.path.isfile(fstate_file):
        print("ERROR: fstate file not found:", fstate_file)
        return 1

    fstate_dict = {}
    with open(fstate_file, 'r') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 3:
                try:
                    src, dst, nh = int(parts[0]), int(parts[1]), int(parts[2])
                    fstate_dict[(src, dst)] = nh
                except (ValueError, IndexError):
                    pass

    path = trace_path(fstate_dict, from_id, to_id)
    if not path or len(path) < 2:
        print("No path from %d to %d at t=%.1fs" % (from_id, to_id, time_s))
        return 0

    from_gid = from_id - gs_start_id
    to_gid = to_id - gs_start_id
    dst_gs_node_id = to_id

    def label(n):
        if n >= gs_start_id:
            gid = n - gs_start_id
            return "GS %s (%d)" % (ground_stations[gid]["name"][:12], n) if 0 <= gid < len(ground_stations) else "GS(%d)" % n
        return "MEO %d" % n if n >= leo_num_sats else "LEO %d" % n

    print("=" * 72)
    print("Path decision explanation: %d → %d  at time %.1f s" % (from_id, to_id, time_s))
    print("Path: " + " → ".join([label(p) for p in path]))
    print("=" * 72)

    # Explain GS → first satellite (source satellite choice)
    first_sat = path[1]
    if first_sat < num_sats:
        gs_in_range_src = state['ground_station_satellites_in_range'][from_gid]
        leo_in_range = [(gsl_m, sid) for gsl_m, sid in gs_in_range_src if state['is_leo'](sid)]
        dist_to_gs = state['dist_np']  # dist[sat, dst_gs] not defined; we use dist_satellite_to_ground_station
        # For source GS we choose sat that minimizes gsl(sat) + min over dst_sats of (dist(sat, dst_sat) + gsl_dst(dst_sat))
        # Algorithm: possibilities = (gsl_dist_m + best_offered, sat_id) where best_offered = dist_satellite_to_ground_station[(sat_id, dst_gs)]
        # We need dist_satellite_to_ground_station for each candidate source sat - that's the min over dst_sats of dist(sat,dst_sat)+gsl_dst
        possible_src = [(gsl_m, sid) for gsl_m, sid in leo_in_range]
        scores_src = []
        for gsl_m, sat_id in possible_src:
            best_offered = float('inf')
            for gsl_dst, dst_sat_id in state['ground_station_satellites_in_range'][to_gid]:
                if not state['is_leo'](dst_sat_id):
                    continue
                d = float(state['dist_np'][sat_id, dst_sat_id])
                if math.isinf(d):
                    continue
                best_offered = min(best_offered, d + gsl_dst)
            if math.isinf(best_offered):
                continue
            total = gsl_m + best_offered
            scores_src.append((sat_id, gsl_m / 1000, best_offered / 1000, total / 1000))
        scores_src.sort(key=lambda x: x[3])
        print()
        print("Hop: %s → %s (source GS chooses first satellite)" % (label(from_id), label(first_sat)))
        print("  Candidates (LEO in range of source GS): minimize gsl_dist + dist(sat → dst_gs)")
        for sat_id, gsl_km, offered_km, total_km in scores_src[:15]:
            mark = " <-- chosen" if sat_id == first_sat else ""
            print("    %s: gsl = %.0f km, dist(sat→dst_gs) = %.0f km  => total = %.0f km%s" % (
                label(sat_id), gsl_km, offered_km, total_km, mark))
        if len(scores_src) > 15:
            print("    ... (%d more)" % (len(scores_src) - 15))
        print()

    # Explain each satellite → satellite (or satellite → GS) hop
    sat_path = [p for p in path if isinstance(p, int) and p < num_sats]
    for idx in range(len(sat_path)):
        curr = sat_path[idx]
        if idx + 1 >= len(sat_path):
            # curr is last satellite, next is GS (Case A)
            print("Hop: %s → %s" % (label(curr), label(to_id)))
            dst_sat, _, _ = get_dst_sat_and_use_meo(state, curr, to_gid)
            print("  Case A: curr == dst_sat (LEO %d). Deliver to GS." % curr)
            print()
            break
        next_node = sat_path[idx + 1]
        case_str, target_id, candidates = explain_hop(state, curr, next_node, to_gid, dst_gs_node_id, next_node)

        print("Hop: %s → %s" % (label(curr), label(next_node)))
        print("  %s" % case_str)
        if target_id is not None:
            print("  Target: %s" % label(target_id))
        if candidates:
            print("  Candidates (neighbor: edge_km, dist(neighbor→target)_km, score_km):")
            for n, w_km, d_km, score_km in candidates[:20]:
                mark = " <-- chosen" if n == next_node else ""
                print("    %s: edge = %.0f km, dist to target = %.0f km  => score = %.0f km%s" % (
                    label(n), w_km, d_km, score_km, mark))
            if len(candidates) > 20:
                print("    ... (%d more)" % (len(candidates) - 20))
        print()

    print("Formula: next_hop = argmin_{neighbor in candidates} [ edge(curr, neighbor) + dist(neighbor, target) ]")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())

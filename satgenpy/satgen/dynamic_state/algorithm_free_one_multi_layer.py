# FREE-ONE MULTI-LAYER (LEO+MEO as two separate subgraphs)
#
# Clean fallback policy:
# - LEO-only is always computed first and kept as baseline
# - MEO is only used if a FULL valid MEO route exists
# - otherwise the algorithm falls back to the already-computed LEO path
#
# Cases:
# Case A: curr == dst_sat -> go to GS
# Case B: curr is LEO and MEO route is fully valid:
#         Step 1: enter a reachable MEO (via some LEO handoff that has a cross-layer edge)
#         Step 2: ensure that entry MEO can reach a gateway MEO (MEO-only)
#         Step 3: gateway MEO exits to dst_sat
# Case C: curr is LEO and MEO is not needed or not fully valid -> LEO-only routing to dst_sat

from .fstate_calculation import *
import math
import networkx as nx


def algorithm_free_one_multi_layer(
        output_dynamic_state_dir,
        time_since_epoch_ns,
        satellites,
        ground_stations,
        sat_net_graph_only_satellites_with_isls,
        ground_station_satellites_in_range,
        num_isls_per_sat,
        sat_neighbor_to_if,
        list_gsl_interfaces_info,
        prev_output,
        enable_verbose_logs,
        leo_num_sats,
        meo_threshold_distance_m=10000000.0,
        meo_threshold_hops=3
):

    def is_leo(sid: int) -> bool:
        return sid < leo_num_sats

    def is_meo(sid: int) -> bool:
        return sid >= leo_num_sats

    if enable_verbose_logs:
        print("\nALGORITHM: FREE ONE MULTI-LAYER (LEO-first fallback)")
        print("  > LEO satellites: 0 to %d" % (leo_num_sats - 1))
        print("  > MEO satellites: %d to %d" % (leo_num_sats, len(satellites) - 1))
        print("  > MEO threshold distance: %.2f km" % (meo_threshold_distance_m / 1000.0))
        print("  > MEO threshold hops: %d" % meo_threshold_hops)

    # ----------------------------
    # Graph sanity
    # ----------------------------
    if sat_net_graph_only_satellites_with_isls.number_of_nodes() != len(satellites):
        raise ValueError("Number of nodes in the graph does not match the number of satellites")

    for sid in range(len(satellites)):
        for n in sat_net_graph_only_satellites_with_isls.neighbors(sid):
            if n >= len(satellites):
                raise ValueError("Graph cannot contain satellite-to-ground-station links")

    # ----------------------------
    # Split into subgraphs
    # ----------------------------
    leo_nodes = list(range(0, leo_num_sats))
    meo_nodes = list(range(leo_num_sats, len(satellites)))

    leo_subgraph = sat_net_graph_only_satellites_with_isls.subgraph(leo_nodes).copy()
    meo_subgraph = sat_net_graph_only_satellites_with_isls.subgraph(meo_nodes).copy()

    # Cross-layer edges: LEO -> [(MEO, weight)]
    leo_to_meo_neighbors = {l: [] for l in leo_nodes}
    for l in leo_nodes:
        for n in sat_net_graph_only_satellites_with_isls.neighbors(l):
            if is_meo(n):
                w = sat_net_graph_only_satellites_with_isls.edges[(l, n)]["weight"]
                leo_to_meo_neighbors[l].append((n, w))

    # Weighted shortest distances
    dist_leo = dict(nx.all_pairs_dijkstra_path_length(leo_subgraph, weight="weight"))
    dist_meo = dict(nx.all_pairs_dijkstra_path_length(meo_subgraph, weight="weight"))

    # hop counts
    hop_leo = dict(nx.all_pairs_shortest_path_length(leo_subgraph))
    hop_meo = dict(nx.all_pairs_shortest_path_length(meo_subgraph))

    def d_leo(a: int, b: int) -> float:
        return dist_leo.get(a, {}).get(b, float("inf"))

    def d_meo(a: int, b: int) -> float:
        return dist_meo.get(a, {}).get(b, float("inf"))

    # ----------------------------
    # Helper: pick gateway MEO reachable from meo_from for dst_sat
    # gateway = MEO with direct edge to dst_sat
    # ----------------------------
    def pick_gateway_from_meo(meo_from: int, dst_sat: int):
        best_g = None
        best_key = (float("inf"), float("inf"))  # (hop, exit_weight)

        for g in meo_nodes:
            if not sat_net_graph_only_satellites_with_isls.has_edge(g, dst_sat):
                continue

            h = hop_meo.get(meo_from, {}).get(g, float("inf"))
            if math.isinf(h):
                continue

            exit_w = sat_net_graph_only_satellites_with_isls.edges[(g, dst_sat)]["weight"]
            key = (float(h), float(exit_w))

            if key < best_key:
                best_key = key
                best_g = g

        return best_g

    # ----------------------------
    # Helper: cost from a MEO node to a LEO dst_sat via a gateway
    # ----------------------------
    def meo_to_leo_cost(curr_meo: int, dst_sat: int) -> float:
        best = float("inf")

        for g in meo_nodes:
            if not sat_net_graph_only_satellites_with_isls.has_edge(g, dst_sat):
                continue

            dm = d_meo(curr_meo, g)
            if math.isinf(dm):
                continue

            w_exit = sat_net_graph_only_satellites_with_isls.edges[(g, dst_sat)]["weight"]
            best = min(best, dm + w_exit)

        return best

    #################################
    # BANDWIDTH STATE
    #################################
    output_filename = output_dynamic_state_dir + "/gsl_if_bandwidth_" + str(time_since_epoch_ns) + ".txt"
    if enable_verbose_logs:
        print("  > Writing interface bandwidth state to: " + output_filename)

    with open(output_filename, "w+") as f_out:
        if time_since_epoch_ns == 0:
            for node_id in range(len(satellites)):
                f_out.write("%d,%d,%f\n" % (
                    node_id, num_isls_per_sat[node_id],
                    list_gsl_interfaces_info[node_id]["aggregate_max_bandwidth"]
                ))
            for node_id in range(len(satellites), len(satellites) + len(ground_stations)):
                f_out.write("%d,%d,%f\n" % (
                    node_id, 0, list_gsl_interfaces_info[node_id]["aggregate_max_bandwidth"]
                ))

    #################################
    # FORWARDING STATE
    #################################
    prev_fstate = prev_output["fstate"] if prev_output is not None else None
    gid_to_sat_gsl_if_idx = [0] * len(ground_stations)

    fstate = {}
    output_filename = output_dynamic_state_dir + "/fstate_" + str(time_since_epoch_ns) + ".txt"
    if enable_verbose_logs:
        print("  > Writing forwarding state to: " + output_filename)

    def if_pair(a: int, b: int):
        out_if = sat_neighbor_to_if.get((a, b), -1)
        in_if = sat_neighbor_to_if.get((b, a), -1)
        if out_if == -1 or in_if == -1:
            return None
        return out_if, in_if

    with open(output_filename, "w+") as f_out:
        dist_satellite_to_ground_station = {}

        # ----------------------------
        # SATELLITE -> GS
        # ----------------------------
        for curr in range(len(satellites)):
            for dst_gid in range(len(ground_stations)):

                dst_gs_node_id = len(satellites) + dst_gid
                next_hop_decision = (-1, -1, -1)
                distance_to_ground_station_m = float("inf")

                # Destination GS can connect only to LEO sats
                possible_dst_sats = []
                for gsl_dist_m, sat_id in ground_station_satellites_in_range[dst_gid]:
                    if is_leo(sat_id):
                        possible_dst_sats.append((gsl_dist_m, sat_id))

                # ============================================================
                # LEO CURRENT NODE: ALWAYS compute LEO-only first
                # ============================================================
                if is_leo(curr):
                    leo_possibilities = []
                    for gsl_dist_m, sat_id in possible_dst_sats:
                        d = d_leo(curr, sat_id)
                        if math.isinf(d):
                            continue
                        leo_possibilities.append((d + gsl_dist_m, sat_id))

                    leo_possibilities.sort()

                    if leo_possibilities:
                        dst_sat = leo_possibilities[0][1]
                        distance_to_ground_station_m = leo_possibilities[0][0]

                        # ----------------------------
                        # Build baseline LEO next hop first
                        # ----------------------------
                        baseline_next_hop_decision = (-1, -1, -1)

                        # CASE A: curr == dst_sat -> GS
                        if curr == dst_sat:
                            baseline_next_hop_decision = (
                                dst_gs_node_id,
                                num_isls_per_sat[dst_sat] + gid_to_sat_gsl_if_idx[dst_gid],
                                0
                            )
                        else:
                            best_score = float("inf")
                            best_next = None

                            for neighbor_id in leo_subgraph.neighbors(curr):
                                score = (
                                    leo_subgraph.edges[(curr, neighbor_id)]["weight"]
                                    + d_leo(neighbor_id, dst_sat)
                                )
                                if score < best_score:
                                    best_score = score
                                    best_next = neighbor_id

                            if best_next is not None:
                                baseline_next_hop_decision = (
                                    best_next,
                                    sat_neighbor_to_if[(curr, best_next)],
                                    sat_neighbor_to_if[(best_next, curr)]
                                )

                        # Decide if we SHOULD TRY MEO
                        use_meo = False
                        if curr != dst_sat:
                            if distance_to_ground_station_m > meo_threshold_distance_m:
                                use_meo = True
                            else:
                                hops = hop_leo.get(curr, {}).get(dst_sat, float("inf"))
                                if not math.isinf(hops) and hops > meo_threshold_hops:
                                    use_meo = True

                        # Default = LEO baseline
                        next_hop_decision = baseline_next_hop_decision

                        # ----------------------------
                        # Only if thresholds exceeded, TRY MEO
                        # If MEO is not fully valid, keep LEO
                        # ----------------------------
                        if use_meo:
                            best_handoff_leo = None
                            best_entry_meo = None
                            best_key = (float("inf"), float("inf"), float("inf")) 

                            # choose a LEO handoff node l, then cross-layer edge l->m
                            for l in leo_nodes:
                                d_curr_to_l = d_leo(curr, l)
                                if math.isinf(d_curr_to_l):
                                    continue

                                for m, w_lm in leo_to_meo_neighbors.get(l, []):
                                    g = pick_gateway_from_meo(m, dst_sat)
                                    if g is None:
                                        continue

                                    hop_m_to_g = hop_meo.get(m, {}).get(g, float("inf"))
                                    if math.isinf(hop_m_to_g):
                                        continue

                                    exit_w = sat_net_graph_only_satellites_with_isls.edges[(g, dst_sat)]["weight"]
                                    entry_cost = d_curr_to_l + w_lm
                                    key = (float(entry_cost), float(hop_m_to_g), float(exit_w))

                                    if key < best_key:
                                        best_key = key
                                        best_handoff_leo = l
                                        best_entry_meo = m

                            # Use MEO only if a complete valid entry plan exists
                            if best_entry_meo is not None and best_handoff_leo is not None:
                                w_handoff_to_entry = sat_net_graph_only_satellites_with_isls.edges[(best_handoff_leo, best_entry_meo)]["weight"]
                                best_score = float("inf")
                                best_next = None

                                # LEO neighbor candidates toward handoff
                                for neighbor_id in leo_subgraph.neighbors(curr):
                                    d_n_to_handoff = d_leo(neighbor_id, best_handoff_leo)
                                    if math.isinf(d_n_to_handoff):
                                        continue

                                    score = (
                                        leo_subgraph.edges[(curr, neighbor_id)]["weight"]
                                        + d_n_to_handoff
                                        + w_handoff_to_entry
                                    )
                                    if score < best_score:
                                        best_score = score
                                        best_next = neighbor_id

                                # Direct cross-link candidate: curr -> best_entry_meo
                                for m, w_cross in leo_to_meo_neighbors.get(curr, []):
                                    if m == best_entry_meo and w_cross < best_score:
                                        best_score = w_cross
                                        best_next = m
                                        break

                                if best_next is not None:
                                    pair = if_pair(curr, best_next)
                                    if pair is not None:
                                        out_if, in_if = pair
                                        next_hop_decision = (best_next, out_if, in_if)
                        # else: keep LEO 

                # ============================================================
                # MEO CURRENT NODE: must use gateway logic
                # ============================================================
                else:
                    possibilities = []
                    for gsl_dist_m, sat_id in possible_dst_sats:
                        d = meo_to_leo_cost(curr, sat_id)
                        if math.isinf(d):
                            continue
                        possibilities.append((d + gsl_dist_m, sat_id))

                    possibilities.sort()

                    if possibilities:
                        dst_sat = possibilities[0][1]
                        distance_to_ground_station_m = possibilities[0][0]

                        gateway_meo = pick_gateway_from_meo(curr, dst_sat)

                        if gateway_meo is None:
                            next_hop_decision = (-1, -1, -1)
                        else:
                            # If current MEO is itself a gateway -> exit to dst_sat
                            if sat_net_graph_only_satellites_with_isls.has_edge(curr, dst_sat):
                                pair = if_pair(curr, dst_sat)
                                if pair is not None:
                                    out_if, in_if = pair
                                    next_hop_decision = (dst_sat, out_if, in_if)
                                else:
                                    next_hop_decision = (-1, -1, -1)
                            else:
                                h_curr = hop_meo.get(curr, {}).get(gateway_meo, float("inf"))

                                if math.isinf(h_curr):
                                    next_hop_decision = (-1, -1, -1)
                                else:
                                    best_score = float("inf")
                                    best_next = None

                                    for neighbor_id in meo_subgraph.neighbors(curr):
                                        h_nbr = hop_meo.get(neighbor_id, {}).get(gateway_meo, float("inf"))
                                        if math.isinf(h_nbr) or h_nbr >= h_curr:
                                            continue

                                        score = (
                                            meo_subgraph.edges[(curr, neighbor_id)]["weight"]
                                            + d_meo(neighbor_id, gateway_meo)
                                        )
                                        if score < best_score:
                                            best_score = score
                                            best_next = neighbor_id

                                    if best_next is None:
                                        next_hop_decision = (-1, -1, -1)
                                    else:
                                        next_hop_decision = (
                                            best_next,
                                            sat_neighbor_to_if[(curr, best_next)],
                                            sat_neighbor_to_if[(best_next, curr)]
                                        )

                # Save for GS->GS stage
                dist_satellite_to_ground_station[(curr, dst_gs_node_id)] = distance_to_ground_station_m

                # Safety: only dst_sat (LEO) may forward directly to GS
                if next_hop_decision[0] >= len(satellites):
                    allowed = False
                    if is_leo(curr):
                        for _, sat_id in possible_dst_sats:
                            if curr == sat_id:
                                allowed = True
                                break
                    if not allowed:
                        next_hop_decision = (-1, -1, -1)

                # Write to forwarding state
                if not prev_fstate or prev_fstate.get((curr, dst_gs_node_id)) != next_hop_decision:
                    f_out.write("%d,%d,%d,%d,%d\n" % (
                        curr,
                        dst_gs_node_id,
                        next_hop_decision[0],
                        next_hop_decision[1],
                        next_hop_decision[2]
                    ))
                fstate[(curr, dst_gs_node_id)] = next_hop_decision

        # ----------------------------
        # GS -> GS
        # ----------------------------
        for src_gid in range(len(ground_stations)):
            for dst_gid in range(len(ground_stations)):
                if src_gid == dst_gid:
                    continue

                src_gs_node_id = len(satellites) + src_gid
                dst_gs_node_id = len(satellites) + dst_gid

                possible_src_sats = []
                for gsl_dist_m, sat_id in ground_station_satellites_in_range[src_gid]:
                    if is_leo(sat_id):
                        possible_src_sats.append((gsl_dist_m, sat_id))

                possibilities = []
                for gsl_dist_m, sat_id in possible_src_sats:
                    best_offered = dist_satellite_to_ground_station.get((sat_id, dst_gs_node_id), float("inf"))
                    if not math.isinf(best_offered):
                        possibilities.append((gsl_dist_m + best_offered, sat_id))
                possibilities.sort()

                next_hop_decision = (-1, -1, -1)
                if possibilities:
                    src_sat_id = possibilities[0][1]
                    next_hop_decision = (
                        src_sat_id,
                        0,
                        num_isls_per_sat[src_sat_id] + gid_to_sat_gsl_if_idx[src_gid]
                    )

                if not prev_fstate or prev_fstate.get((src_gs_node_id, dst_gs_node_id)) != next_hop_decision:
                    f_out.write("%d,%d,%d,%d,%d\n" % (
                        src_gs_node_id,
                        dst_gs_node_id,
                        next_hop_decision[0],
                        next_hop_decision[1],
                        next_hop_decision[2]
                    ))
                fstate[(src_gs_node_id, dst_gs_node_id)] = next_hop_decision

    if enable_verbose_logs:
        print("")

    return {"fstate": fstate}
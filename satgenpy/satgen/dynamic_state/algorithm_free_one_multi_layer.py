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
    """
    3-case structure (explicit):

      Case A: curr == dst_sat -> go to GS
      Case B: is_leo(curr) and use_meo -> enter MEO, then MEO routes to gateway, then exit to dst_sat
      Case C: is_leo(curr) and not use_meo -> LEO-only routing
      Else:   curr is MEO -> strict gateway routing inside MEO (toward a gateway MEO, then exit to dst_sat)

    Constraints:
    - GS connects only to LEO.
    - One-hop lookahead uses same-layer ISLs only.
    - Cross-layer is allowed only:
        * LEO -> best_meo_sat (entry)
        * gateway MEO -> dst_sat (exit)
    - MEO->MEO moves must strictly decrease hop distance to gateway (prevents loops).
    """

    def is_leo(sid: int) -> bool:
        return sid < leo_num_sats

    def is_meo(sid: int) -> bool:
        return sid >= leo_num_sats

    if enable_verbose_logs:
        print("\nALGORITHM: FREE ONE MULTI-LAYER (EXPLICIT CASES)")
        print("  > LEO satellites: 0 to %d" % (leo_num_sats - 1))
        print("  > MEO satellites: %d to %d" % (leo_num_sats, len(satellites) - 1))
        print("  > MEO threshold distance: %.2f km" % (meo_threshold_distance_m / 1000.0))
        print("  > MEO threshold hops: %d" % meo_threshold_hops)

    # Graph sanity
    if sat_net_graph_only_satellites_with_isls.number_of_nodes() != len(satellites):
        raise ValueError("Number of nodes in the graph does not match the number of satellites")
    for sid in range(len(satellites)):
        for n in sat_net_graph_only_satellites_with_isls.neighbors(sid):
            if n >= len(satellites):
                raise ValueError("Graph cannot contain satellite-to-ground-station links")

    #################################
    # BANDWIDTH STATE (unchanged)
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
    prev_fstate = None
    if prev_output is not None:
        prev_fstate = prev_output["fstate"]

    gid_to_sat_gsl_if_idx = [0] * len(ground_stations)

    if enable_verbose_logs:
        print("  > Calculating Floyd-Warshall for multi-layer graph")
    dist_sat_net_without_gs = nx.floyd_warshall_numpy(sat_net_graph_only_satellites_with_isls)

    # MEO hop distances for monotonic gateway routing
    meo_nodes = list(range(leo_num_sats, len(satellites)))
    meo_subgraph = sat_net_graph_only_satellites_with_isls.subgraph(meo_nodes)
    hop_meo = dict(nx.all_pairs_shortest_path_length(meo_subgraph))

    fstate = {}
    output_filename = output_dynamic_state_dir + "/fstate_" + str(time_since_epoch_ns) + ".txt"
    if enable_verbose_logs:
        print("  > Writing forwarding state to: " + output_filename)

    with open(output_filename, "w+") as f_out:

        dist_satellite_to_ground_station = {}

        # ----------------------------
        # SATELLITE -> GS
        # ----------------------------
        for curr in range(len(satellites)):
            for dst_gid in range(len(ground_stations)):

                dst_gs_node_id = len(satellites) + dst_gid

                # Candidate destination-side LEO satellites for this GS
                possible_dst_sats = []
                for b in ground_station_satellites_in_range[dst_gid]:
                    if is_leo(b[1]):  # b[0]=GSL dist, b[1]=sat id
                        possible_dst_sats.append(b)

                # Choose dst_sat that minimizes dist(curr->dst_sat) + gsl(dst_sat->GS)
                possibilities = []
                for gsl_dist_m, sat_id in possible_dst_sats:
                    if math.isinf(dist_sat_net_without_gs[(curr, sat_id)]):
                        continue
                    possibilities.append((dist_sat_net_without_gs[(curr, sat_id)] + gsl_dist_m, sat_id))
                possibilities.sort()

                next_hop_decision = (-1, -1, -1)
                distance_to_ground_station_m = float("inf")

                if possibilities:
                    dst_sat = possibilities[0][1]
                    distance_to_ground_station_m = possibilities[0][0]

                    # Decide use_meo only when curr is LEO
                    use_meo = False
                    if is_leo(curr):
                        if distance_to_ground_station_m > meo_threshold_distance_m:
                            use_meo = True
                        else:
                            if not math.isinf(dist_sat_net_without_gs[(curr, dst_sat)]):
                                avg_isl_length = 2000000.0
                                estimated_hops = int(dist_sat_net_without_gs[(curr, dst_sat)] / avg_isl_length) + 1
                                if estimated_hops > meo_threshold_hops:
                                    use_meo = True

                    # ============================================================
                    # Case A
                    # ============================================================
                    if curr == dst_sat:
                        next_hop_decision = (
                            dst_gs_node_id,
                            num_isls_per_sat[dst_sat] + gid_to_sat_gsl_if_idx[dst_gid],
                            0
                        )

                    # ============================================================
                    # Case B: LEO + use_meo -> enter MEO (toward best_meo_sat)
                    # ============================================================
                    elif is_leo(curr) and use_meo:

                        # Choose entry target best_meo_sat (must be reachable and must reach dst_sat)
                        best_meo_sat = None
                        best_total = float("inf")
                        for meo_sat in meo_nodes:
                            if math.isinf(dist_sat_net_without_gs[(curr, meo_sat)]):
                                continue
                            if math.isinf(dist_sat_net_without_gs[(meo_sat, dst_sat)]):
                                continue
                            total = dist_sat_net_without_gs[(curr, meo_sat)] + dist_sat_net_without_gs[(meo_sat, dst_sat)]
                            if total < best_total:
                                best_total = total
                                best_meo_sat = meo_sat

                        if best_meo_sat is None:
                            # If no entry MEO possible, fallback to LEO-only toward dst_sat
                            best_score = float("inf")
                            best_next = None
                            for neighbor_id in sat_net_graph_only_satellites_with_isls.neighbors(curr):
                                if not is_leo(neighbor_id):
                                    continue
                                score = (
                                    sat_net_graph_only_satellites_with_isls.edges[(curr, neighbor_id)]["weight"]
                                    + dist_sat_net_without_gs[(neighbor_id, dst_sat)]
                                )
                                if score < best_score:
                                    best_score = score
                                    best_next = neighbor_id
                            if best_next is not None:
                                next_hop_decision = (
                                    best_next,
                                    sat_neighbor_to_if[(curr, best_next)],
                                    sat_neighbor_to_if[(best_next, curr)]
                                )
                        else:
                            # One-hop lookahead: LEO neighbors + (optional) best_meo_sat
                            best_score = float("inf")
                            best_next = None
                            neighbors_curr = list(sat_net_graph_only_satellites_with_isls.neighbors(curr))
                            candidates = [n for n in neighbors_curr if is_leo(n) or n == best_meo_sat]
                            for neighbor_id in candidates:
                                score = (
                                    sat_net_graph_only_satellites_with_isls.edges[(curr, neighbor_id)]["weight"]
                                    + dist_sat_net_without_gs[(neighbor_id, best_meo_sat)]
                                )
                                if score < best_score:
                                    best_score = score
                                    best_next = neighbor_id

                            if best_next is not None:
                                next_hop_decision = (
                                    best_next,
                                    sat_neighbor_to_if[(curr, best_next)],
                                    sat_neighbor_to_if[(best_next, curr)]
                                )

                    # ============================================================
                    # Case C: LEO + not use_meo -> LEO-only routing to dst_sat
                    # ============================================================
                    elif is_leo(curr) and (not use_meo):

                        best_score = float("inf")
                        best_next = None
                        for neighbor_id in sat_net_graph_only_satellites_with_isls.neighbors(curr):
                            if not is_leo(neighbor_id):
                                continue  # LEO->LEO only
                            score = (
                                sat_net_graph_only_satellites_with_isls.edges[(curr, neighbor_id)]["weight"]
                                + dist_sat_net_without_gs[(neighbor_id, dst_sat)]
                            )
                            if score < best_score:
                                best_score = score
                                best_next = neighbor_id

                        if best_next is not None:
                            next_hop_decision = (
                                best_next,
                                sat_neighbor_to_if[(curr, best_next)],
                                sat_neighbor_to_if[(best_next, curr)]
                            )

                    # ============================================================
                    # Else: curr is MEO -> strict gateway routing inside MEO
                    # ============================================================
                    else:
                        # Find a gateway MEO that has direct edge to dst_sat (first found)
                        gateway_meo = None
                        for g in meo_nodes:
                            if sat_net_graph_only_satellites_with_isls.has_edge(g, dst_sat):
                                gateway_meo = g
                                break

                        if gateway_meo is None:
                            next_hop_decision = (-1, -1, -1)
                        else:
                            # If current MEO is gateway to dst_sat, exit now
                            if sat_net_graph_only_satellites_with_isls.has_edge(curr, dst_sat):
                                next_hop_decision = (
                                    dst_sat,
                                    sat_neighbor_to_if[(curr, dst_sat)],
                                    sat_neighbor_to_if[(dst_sat, curr)]
                                )
                            else:
                                # MEO->MEO only, strictly decreasing hop distance to gateway
                                try:
                                    h_curr = hop_meo[curr][gateway_meo]
                                except KeyError:
                                    h_curr = None

                                if h_curr is None:
                                    next_hop_decision = (-1, -1, -1)
                                else:
                                    best_score = float("inf")
                                    best_next = None

                                    for neighbor_id in sat_net_graph_only_satellites_with_isls.neighbors(curr):
                                        if not is_meo(neighbor_id):
                                            continue  # stay in MEO

                                        try:
                                            h_nbr = hop_meo[neighbor_id][gateway_meo]
                                        except KeyError:
                                            continue

                                        if h_nbr >= h_curr:
                                            continue  # must get strictly closer

                                        score = (
                                            sat_net_graph_only_satellites_with_isls.edges[(curr, neighbor_id)]["weight"]
                                            + dist_sat_net_without_gs[(neighbor_id, dst_sat)]
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

                # Safety: only dst_sat (LEO) may forward to GS; MEO must never forward to GS
                nh = next_hop_decision[0]
                if nh >= len(satellites) and curr != dst_sat:
                    next_hop_decision = (-1, -1, -1)

                # Write delta
                if not prev_fstate or prev_fstate.get((curr, dst_gs_node_id)) != next_hop_decision:
                    f_out.write("%d,%d,%d,%d,%d\n" % (
                        curr, dst_gs_node_id,
                        next_hop_decision[0], next_hop_decision[1], next_hop_decision[2]
                    ))
                fstate[(curr, dst_gs_node_id)] = next_hop_decision

        # ----------------------------
        # GS -> GS - routing
        # ----------------------------
        for src_gid in range(len(ground_stations)):
            for dst_gid in range(len(ground_stations)):
                if src_gid == dst_gid:
                    continue

                src_gs_node_id = len(satellites) + src_gid
                dst_gs_node_id = len(satellites) + dst_gid

                possible_src_sats = []
                for a in ground_station_satellites_in_range[src_gid]:
                    if is_leo(a[1]):
                        possible_src_sats.append(a)

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
                        src_gs_node_id, dst_gs_node_id,
                        next_hop_decision[0], next_hop_decision[1], next_hop_decision[2]
                    ))
                fstate[(src_gs_node_id, dst_gs_node_id)] = next_hop_decision

    if enable_verbose_logs:
        print("")

    return {"fstate": fstate}
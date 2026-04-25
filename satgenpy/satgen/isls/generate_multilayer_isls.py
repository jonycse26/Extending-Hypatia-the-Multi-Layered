# this is the file for the generation of the multilayer ISLs

import math

EARTH_RADIUS_M = 6378135.0  


def _walker_eci_position(
        orb_idx,
        sat_idx,
        n_orbits,
        n_sats_per_orbit,
        altitude_m,
        inclination_deg,
        phase_diff=True
):
    """Approximate circular Walker-like ECI position for geometry filtering."""
    r = EARTH_RADIUS_M + float(altitude_m)
    raan_deg = orb_idx * 360.0 / n_orbits
    orbit_wise_shift = 0.0
    if phase_diff and (orb_idx % 2 == 1):
        orbit_wise_shift = 360.0 / (n_sats_per_orbit * 2.0)
    mean_anomaly_deg = orbit_wise_shift + (sat_idx * 360.0 / n_sats_per_orbit)

    omega = math.radians(raan_deg)
    u = math.radians(mean_anomaly_deg)
    inc = math.radians(float(inclination_deg))
    x = r * (math.cos(u) * math.cos(omega) - math.sin(u) * math.sin(omega) * math.cos(inc))
    y = r * (math.cos(u) * math.sin(omega) + math.sin(u) * math.cos(omega) * math.cos(inc))
    z = r * math.sin(u) * math.sin(inc)
    return (x, y, z)


def _euclidean_distance(p0, p1):
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    dz = p1[2] - p0[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _segment_is_earth_clear(p0, p1, earth_radius_m=EARTH_RADIUS_M):
    """
    True when the straight segment p0->p1 stays strictly outside Earth sphere.
    """
    ax, ay, az = p0
    bx, by, bz = p1
    ux, uy, uz = (bx - ax, by - ay, bz - az)
    uu = ux * ux + uy * uy + uz * uz
    if uu <= 1e-18:
        return (ax * ax + ay * ay + az * az) > (earth_radius_m * earth_radius_m)
    t = -((ax * ux) + (ay * uy) + (az * uz)) / uu
    t = max(0.0, min(1.0, t))
    cx = ax + t * ux
    cy = ay + t * uy
    cz = az + t * uz
    return (cx * cx + cy * cy + cz * cz) > (earth_radius_m * earth_radius_m * (1.0 + 1e-12))


def generate_multilayer_isls(
        output_filename_isls,
        leo_n_orbits,
        leo_n_sats_per_orbit,
        meo_n_orbits,
        meo_n_sats_per_orbit,
        leo_num_sats,
        isl_shift=0,
        max_cross_layer_isl_length_m=None,
        leo_altitude_m=630000.0,
        meo_altitude_m=10000000.0,
        leo_inclination_degree=51.9,
        meo_inclination_degree=55.0,
        leo_phase_diff=True,
        meo_phase_diff=True
):
    """
    Generate multi-layer ISL file with LEO ISLs, MEO ISLs, and cross-layer ISLs.

    :param output_filename_isls:      Output filename
    :param leo_n_orbits:              Number of LEO orbits
    :param leo_n_sats_per_orbit:      Number of satellites per LEO orbit
    :param meo_n_orbits:              Number of MEO orbits
    :param meo_n_sats_per_orbit:      Number of satellites per MEO orbit
    :param leo_num_sats:              Total number of LEO satellites (for MEO offset)
    :param isl_shift:                 ISL shift between orbits (for LEO and MEO grid links)
    :param max_cross_layer_isl_length_m: Maximum distance for cross-layer ISLs (optional)
    :param leo_altitude_m:            LEO altitude for geometry checks
    :param meo_altitude_m:            MEO altitude for geometry checks
    :param leo_inclination_degree:    LEO inclination for geometry checks
    :param meo_inclination_degree:    MEO inclination for geometry checks
    :param leo_phase_diff:            Whether odd/even LEO planes are half-slot shifted
    :param meo_phase_diff:            Whether odd/even MEO planes are half-slot shifted
    """

    list_isls = []

    # Generate LEO ISLs (plus grid pattern)
    if leo_n_orbits < 3 or leo_n_sats_per_orbit < 3:
        raise ValueError("LEO: Number of orbits and satellites per orbit must each be at least 3")

    for i in range(leo_n_orbits):
        for j in range(leo_n_sats_per_orbit):
            sat = i * leo_n_sats_per_orbit + j
            sat_same_orbit = i * leo_n_sats_per_orbit + ((j + 1) % leo_n_sats_per_orbit)
            sat_adjacent_orbit = ((i + 1) % leo_n_orbits) * leo_n_sats_per_orbit + ((j + isl_shift) % leo_n_sats_per_orbit)
            list_isls.append((min(sat, sat_same_orbit), max(sat, sat_same_orbit)))
            list_isls.append((min(sat, sat_adjacent_orbit), max(sat, sat_adjacent_orbit)))

    # Generate MEO ISLs (plus grid pattern)
    if meo_n_orbits < 3 or meo_n_sats_per_orbit < 3:
        raise ValueError("MEO: Number of orbits and satellites per orbit must each be at least 3")

    meo_idx_offset = leo_num_sats
    for i in range(meo_n_orbits):
        for j in range(meo_n_sats_per_orbit):
            sat = meo_idx_offset + i * meo_n_sats_per_orbit + j
            sat_same_orbit = meo_idx_offset + i * meo_n_sats_per_orbit + ((j + 1) % meo_n_sats_per_orbit)
            sat_adjacent_orbit = meo_idx_offset + ((i + 1) % meo_n_orbits) * meo_n_sats_per_orbit + ((j + isl_shift) % meo_n_sats_per_orbit)
            list_isls.append((min(sat, sat_same_orbit), max(sat, sat_same_orbit)))
            list_isls.append((min(sat, sat_adjacent_orbit), max(sat, sat_adjacent_orbit)))

    # Generate cross-layer ISLs (LEO to MEO)
    # Policy: each LEO connects to exactly one nearest MEO that
    meo_n_sats = meo_n_orbits * meo_n_sats_per_orbit

    meo_positions = {}
    for meo_i in range(meo_n_orbits):
        for meo_j in range(meo_n_sats_per_orbit):
            meo_sat = meo_idx_offset + meo_i * meo_n_sats_per_orbit + meo_j
            meo_positions[meo_sat] = _walker_eci_position(
                meo_i,
                meo_j,
                meo_n_orbits,
                meo_n_sats_per_orbit,
                meo_altitude_m,
                meo_inclination_degree,
                meo_phase_diff
            )

    for leo_sat in range(leo_num_sats):
        leo_i = leo_sat // leo_n_sats_per_orbit
        leo_j = leo_sat % leo_n_sats_per_orbit
        leo_pos = _walker_eci_position(
            leo_i,
            leo_j,
            leo_n_orbits,
            leo_n_sats_per_orbit,
            leo_altitude_m,
            leo_inclination_degree,
            leo_phase_diff
        )

        best_meo = None
        best_dist = float("inf")
        for meo_sat, meo_pos in meo_positions.items():
            if not _segment_is_earth_clear(leo_pos, meo_pos, EARTH_RADIUS_M):
                continue
            d = _euclidean_distance(leo_pos, meo_pos)
            if max_cross_layer_isl_length_m is not None and d > max_cross_layer_isl_length_m:
                continue
            if d < best_dist:
                best_dist = d
                best_meo = meo_sat

        if best_meo is not None:
            list_isls.append((min(leo_sat, best_meo), max(leo_sat, best_meo)))
        else:
            raise ValueError(
                "No Earth-clear MEO candidate found for LEO sat %d; "
                "cannot satisfy one-LEO-to-one-MEO policy." % leo_sat
            )

    # Remove duplicates and sort
    list_isls = list(set(list_isls))
    list_isls.sort()

    # Write to file
    with open(output_filename_isls, "w+") as f:
        for (a, b) in list_isls:
            f.write(str(a) + " " + str(b) + "\n")

    return list_isls

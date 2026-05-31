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
        max_leo_per_meo=5,
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
    :param max_cross_layer_isl_length_m: Maximum distance for cross-layer ISLs (optional; reserved)
    :param max_leo_per_meo:           Max LEO satellites connected to each MEO (orbit/slot mapping)
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
    # Each LEO maps to one MEO by (orbit, slot) quantization; cap links per MEO with max_leo_per_meo.
    meo_n_sats = meo_n_orbits * meo_n_sats_per_orbit
    leo_count_per_meo = {}

    for leo_i in range(leo_n_orbits):
        for leo_j in range(leo_n_sats_per_orbit):
            leo_sat = leo_i * leo_n_sats_per_orbit + leo_j
            if leo_sat >= leo_num_sats:
                continue
            meo_orbit_idx = (leo_i * meo_n_orbits) // leo_n_orbits
            meo_sat_idx = (leo_j * meo_n_sats_per_orbit) // leo_n_sats_per_orbit
            meo_sat = meo_idx_offset + meo_orbit_idx * meo_n_sats_per_orbit + meo_sat_idx
            if meo_sat >= leo_num_sats + meo_n_sats:
                continue
            n = leo_count_per_meo.get(meo_sat, 0)
            if n < max_leo_per_meo:
                list_isls.append((min(leo_sat, meo_sat), max(leo_sat, meo_sat)))
                leo_count_per_meo[meo_sat] = n + 1

    # Remove duplicates and sort
    list_isls = list(set(list_isls))
    list_isls.sort()

    # Write to file
    with open(output_filename_isls, "w+") as f:
        for (a, b) in list_isls:
            f.write(str(a) + " " + str(b) + "\n")

    return list_isls

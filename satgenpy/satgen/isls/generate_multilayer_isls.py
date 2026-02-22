# this is the file for the generation of the multilayer ISLs


def generate_multilayer_isls(
        output_filename_isls,
        leo_n_orbits,
        leo_n_sats_per_orbit,
        meo_n_orbits,
        meo_n_sats_per_orbit,
        leo_num_sats,  # Total number of LEO satellites (for offset)
        isl_shift=0,
        max_cross_layer_isl_length_m=None
):
    """
    Generate multi-layer ISL file with LEO ISLs, MEO ISLs, and cross-layer ISLs.

    :param output_filename_isls:     Output filename
    :param leo_n_orbits:              Number of LEO orbits
    :param leo_n_sats_per_orbit:      Number of satellites per LEO orbit
    :param meo_n_orbits:              Number of MEO orbits
    :param meo_n_sats_per_orbit:      Number of satellites per MEO orbit
    :param leo_num_sats:              Total number of LEO satellites (for MEO offset)
    :param isl_shift:                 ISL shift between orbits (for LEO)
    :param max_cross_layer_isl_length_m: Maximum distance for cross-layer ISLs (optional)
    """
    
    list_isls = []
    
    # Generate LEO ISLs (plus grid pattern)
    if leo_n_orbits < 3 or leo_n_sats_per_orbit < 3:
        raise ValueError("LEO: Number of orbits and satellites per orbit must each be at least 3")
    
    for i in range(leo_n_orbits):
        for j in range(leo_n_sats_per_orbit):
            sat = i * leo_n_sats_per_orbit + j
            
            # Link to the next in the orbit
            sat_same_orbit = i * leo_n_sats_per_orbit + ((j + 1) % leo_n_sats_per_orbit)
            sat_adjacent_orbit = ((i + 1) % leo_n_orbits) * leo_n_sats_per_orbit + ((j + isl_shift) % leo_n_sats_per_orbit)
            
            # Same orbit
            list_isls.append((min(sat, sat_same_orbit), max(sat, sat_same_orbit)))
            
            # Adjacent orbit
            list_isls.append((min(sat, sat_adjacent_orbit), max(sat, sat_adjacent_orbit)))
    
    # Generate MEO ISLs (plus grid pattern)
    if meo_n_orbits < 3 or meo_n_sats_per_orbit < 3:
        raise ValueError("MEO: Number of orbits and satellites per orbit must each be at least 3")
    
    meo_idx_offset = leo_num_sats  # MEO satellites start after LEO satellites
    
    for i in range(meo_n_orbits):
        for j in range(meo_n_sats_per_orbit):
            sat = meo_idx_offset + i * meo_n_sats_per_orbit + j
            
            # Link to the next in the orbit
            sat_same_orbit = meo_idx_offset + i * meo_n_sats_per_orbit + ((j + 1) % meo_n_sats_per_orbit)
            sat_adjacent_orbit = meo_idx_offset + ((i + 1) % meo_n_orbits) * meo_n_sats_per_orbit + ((j + isl_shift) % meo_n_sats_per_orbit)
            
            # Same orbit
            list_isls.append((min(sat, sat_same_orbit), max(sat, sat_same_orbit)))
            
            # Adjacent orbit
            list_isls.append((min(sat, sat_adjacent_orbit), max(sat, sat_adjacent_orbit)))
    
    # Generate cross-layer ISLs (LEO to MEO)
    # Strategy: Connect every LEO satellite to at least one MEO satellite
    # This ensures every LEO can directly access MEO for routing, simplifying the proof-of-concept
    
    # For each LEO satellite, find at least one MEO satellite to connect to
    # Use a regular spacing pattern to distribute connections across MEO satellites
    for leo_i in range(leo_n_orbits):
        for leo_j in range(leo_n_sats_per_orbit):
            leo_sat = leo_i * leo_n_sats_per_orbit + leo_j
            
            # Ensure we don't exceed LEO satellite count
            if leo_sat < leo_num_sats:
                # Find a corresponding MEO satellite
                # Map LEO orbit to MEO orbit (distribute LEO orbits across MEO orbits)
                meo_orbit_idx = (leo_i * meo_n_orbits) // leo_n_orbits
                # Map LEO satellite position to MEO satellite position
                meo_sat_idx = (leo_j * meo_n_sats_per_orbit) // leo_n_sats_per_orbit
                meo_sat = meo_idx_offset + meo_orbit_idx * meo_n_sats_per_orbit + meo_sat_idx
                
                # Ensure we don't exceed MEO satellite count
                if meo_sat < leo_num_sats + (meo_n_orbits * meo_n_sats_per_orbit):
                    # Add cross-layer ISL
                    list_isls.append((min(leo_sat, meo_sat), max(leo_sat, meo_sat)))
    
    # Remove duplicates and sort
    list_isls = list(set(list_isls))
    list_isls.sort()
    
    # Write to file
    with open(output_filename_isls, 'w+') as f:
        for (a, b) in list_isls:
            f.write(str(a) + " " + str(b) + "\n")
    
    return list_isls


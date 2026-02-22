# This is the main file for the Kuiper-630 MEO constellation

import sys
import math
from main_helper_multilayer import MainHelperMultiLayer

# WGS72 value; taken from https://geographiclib.sourceforge.io/html/NET/NETGeographicLib_8h_source.html
EARTH_RADIUS = 6378135.0

# GENERATION CONSTANTS

BASE_NAME = "kuiper_630_meo"
NICE_NAME = "Kuiper-630-MEO"

# KUIPER 630 LEO SHELL

LEO_ECCENTRICITY = 0.0000001  # Circular orbits are zero, but pyephem does not permit 0, so lowest possible value
LEO_ARG_OF_PERIGEE_DEGREE = 0.0
LEO_PHASE_DIFF = True

################################################################
# The below constants are taken from Kuiper's FCC filing as below:
# [1]: https://www.itu.int/ITU-R/space/asreceived/Publication/DisplayPublication/8716
################################################################

LEO_MEAN_MOTION_REV_PER_DAY = 14.80  # Altitude ~630 km
LEO_ALTITUDE_M = 630000  # Altitude ~630 km

LEO_NUM_ORBS = 34
LEO_NUM_SATS_PER_ORB = 34
LEO_INCLINATION_DEGREE = 51.9

# MEO SHELL
# Example MEO configuration: Medium Earth Orbit at ~10,000 km altitude
# This is a simplified example - actual MEO constellations may have different parameters

MEO_ECCENTRICITY = 0.0000001
MEO_ARG_OF_PERIGEE_DEGREE = 0.0
MEO_PHASE_DIFF = True

# MEO at ~10,000 km altitude
# Mean motion calculation: n = sqrt(GM / a^3) * (86400 / (2*pi))
# For 10,000 km altitude: a = 6378135 + 10000000 = 16378135 m
# GM = 3.986004418e14 m^3/s^2
# n = sqrt(3.986004418e14 / (16378135^3)) * (86400 / (2*pi)) ≈ 2.0 rev/day
MEO_MEAN_MOTION_REV_PER_DAY = 2.0  # Approximate for ~10,000 km altitude
MEO_ALTITUDE_M = 10000000  # 10,000 km altitude

# Smaller MEO constellation (fewer satellites needed due to higher altitude)
MEO_NUM_ORBS = 6
MEO_NUM_SATS_PER_ORB = 6
MEO_INCLINATION_DEGREE = 55.0  # Similar inclination to LEO

################################################################

main_helper = MainHelperMultiLayer(
        BASE_NAME,
        NICE_NAME,
        # LEO parameters
        LEO_ECCENTRICITY,
        LEO_ARG_OF_PERIGEE_DEGREE,
        LEO_PHASE_DIFF,
        LEO_MEAN_MOTION_REV_PER_DAY,
        LEO_ALTITUDE_M,
        LEO_NUM_ORBS,
        LEO_NUM_SATS_PER_ORB,
        LEO_INCLINATION_DEGREE,
        # MEO parameters
        MEO_ECCENTRICITY,
        MEO_ARG_OF_PERIGEE_DEGREE,
        MEO_PHASE_DIFF,
        MEO_MEAN_MOTION_REV_PER_DAY,
        MEO_ALTITUDE_M,
        MEO_NUM_ORBS,
        MEO_NUM_SATS_PER_ORB,
        MEO_INCLINATION_DEGREE,
        # Cross-layer ISL parameters
        MAX_CROSS_LAYER_ISL_LENGTH_M=None,  # Auto-calculate
)


def main():
    args = sys.argv[1:]
    if len(args) != 6:
        print("Must supply exactly six arguments")
        print("Usage: python main_kuiper_630_meo.py [duration (s)] [time step (ms)] "
              "[isls_plus_grid / isls_plus_grid_with_cross_layer / isls_none] "
              "[ground_stations_{top_100, paris_moscow_grid}] "
              "[algorithm_{free_one_only_over_isls, free_one_multi_layer}] "
              "[num threads]")
        exit(1)
    else:
        main_helper.calculate(
            "gen_data",
            int(args[0]),
            int(args[1]),
            args[2],
            args[3],
            args[4],
            int(args[5]),
        )


if __name__ == "__main__":
    main()


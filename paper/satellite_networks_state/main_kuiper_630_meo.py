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
LEO_ECCENTRICITY = 0.0000001  
LEO_ARG_OF_PERIGEE_DEGREE = 0.0
LEO_PHASE_DIFF = True


LEO_MEAN_MOTION_REV_PER_DAY = 14.80  
LEO_ALTITUDE_M = 630000  

LEO_NUM_ORBS = 34
LEO_NUM_SATS_PER_ORB = 34
LEO_INCLINATION_DEGREE = 51.9

# MEO SHELL
MEO_ECCENTRICITY = 0.0000001
MEO_ARG_OF_PERIGEE_DEGREE = 0.0
MEO_PHASE_DIFF = True

# MEO at ~10,000 km altitude
MEO_MEAN_MOTION_REV_PER_DAY = 2.0  
MEO_ALTITUDE_M = 10000000  

# Smaller MEO constellation 
MEO_NUM_ORBS = 6
MEO_NUM_SATS_PER_ORB = 6
MEO_INCLINATION_DEGREE = 55.0  

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
        MAX_CROSS_LAYER_ISL_LENGTH_M=None,  
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


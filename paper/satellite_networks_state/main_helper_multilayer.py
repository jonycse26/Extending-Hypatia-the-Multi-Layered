# this is the main helper for the multilayer satellite constellation

import sys
sys.path.append("../../satgenpy")
import satgen
from satgen.tles import calculate_tle_line_checksum
import os
import math


class MainHelperMultiLayer:

    def __init__(
            self,
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
    ):
        self.BASE_NAME = BASE_NAME
        self.NICE_NAME = NICE_NAME
        
        # LEO parameters
        self.LEO_ECCENTRICITY = LEO_ECCENTRICITY
        self.LEO_ARG_OF_PERIGEE_DEGREE = LEO_ARG_OF_PERIGEE_DEGREE
        self.LEO_PHASE_DIFF = LEO_PHASE_DIFF
        self.LEO_MEAN_MOTION_REV_PER_DAY = LEO_MEAN_MOTION_REV_PER_DAY
        self.LEO_ALTITUDE_M = LEO_ALTITUDE_M
        self.LEO_NUM_ORBS = LEO_NUM_ORBS
        self.LEO_NUM_SATS_PER_ORB = LEO_NUM_SATS_PER_ORB
        self.LEO_INCLINATION_DEGREE = LEO_INCLINATION_DEGREE
        
        # MEO parameters
        self.MEO_ECCENTRICITY = MEO_ECCENTRICITY
        self.MEO_ARG_OF_PERIGEE_DEGREE = MEO_ARG_OF_PERIGEE_DEGREE
        self.MEO_PHASE_DIFF = MEO_PHASE_DIFF
        self.MEO_MEAN_MOTION_REV_PER_DAY = MEO_MEAN_MOTION_REV_PER_DAY
        self.MEO_ALTITUDE_M = MEO_ALTITUDE_M
        self.MEO_NUM_ORBS = MEO_NUM_ORBS
        self.MEO_NUM_SATS_PER_ORB = MEO_NUM_SATS_PER_ORB
        self.MEO_INCLINATION_DEGREE = MEO_INCLINATION_DEGREE
        
        # Calculate derived parameters
        # WGS72 value; taken from https://geographiclib.sourceforge.io/html/NET/NETGeographicLib_8h_source.html
        EARTH_RADIUS = 6378135.0
        
        # LEO GSL and ISL ranges
        # Using elevation angle of 10 degrees 
        LEO_SATELLITE_CONE_RADIUS_M = LEO_ALTITUDE_M / math.tan(math.radians(10.0))
        self.LEO_MAX_GSL_LENGTH_M = math.sqrt(math.pow(LEO_SATELLITE_CONE_RADIUS_M, 2) + math.pow(LEO_ALTITUDE_M, 2))
        # ISLs are not allowed to dip below 80 km altitude
        self.LEO_MAX_ISL_LENGTH_M = 2 * math.sqrt(
            math.pow(EARTH_RADIUS + LEO_ALTITUDE_M, 2) - math.pow(EARTH_RADIUS + 80000, 2)
        )
        
        # MEO GSL and ISL ranges
        # Using elevation angle of 5 degrees
        MEO_SATELLITE_CONE_RADIUS_M = MEO_ALTITUDE_M / math.tan(math.radians(5.0))
        self.MEO_MAX_GSL_LENGTH_M = math.sqrt(math.pow(MEO_SATELLITE_CONE_RADIUS_M, 2) + math.pow(MEO_ALTITUDE_M, 2))
        self.MEO_MAX_ISL_LENGTH_M = 2 * math.sqrt(
            math.pow(EARTH_RADIUS + MEO_ALTITUDE_M, 2) - math.pow(EARTH_RADIUS + 80000, 2)
        )
        
        # Cross-layer ISL range
        if MAX_CROSS_LAYER_ISL_LENGTH_M is None:
            
            max_altitude = max(LEO_ALTITUDE_M, MEO_ALTITUDE_M)
            min_altitude = min(LEO_ALTITUDE_M, MEO_ALTITUDE_M)

            self.MAX_CROSS_LAYER_ISL_LENGTH_M = 2 * math.sqrt(
                math.pow(EARTH_RADIUS + max_altitude, 2) - math.pow(EARTH_RADIUS + 80000, 2)
            )
            # Add some margin for cross-layer links 
            self.MAX_CROSS_LAYER_ISL_LENGTH_M *= 1.2  
        else:
            self.MAX_CROSS_LAYER_ISL_LENGTH_M = MAX_CROSS_LAYER_ISL_LENGTH_M
        
        # Use LEO GSL range for ground stations 
        self.MAX_GSL_LENGTH_M = self.LEO_MAX_GSL_LENGTH_M
        # Use maximum ISL length for overall ISL range
        self.MAX_ISL_LENGTH_M = max(self.LEO_MAX_ISL_LENGTH_M, self.MEO_MAX_ISL_LENGTH_M, self.MAX_CROSS_LAYER_ISL_LENGTH_M)
        
        # Total satellites
        self.LEO_NUM_SATS = LEO_NUM_ORBS * LEO_NUM_SATS_PER_ORB
        self.MEO_NUM_SATS = MEO_NUM_ORBS * MEO_NUM_SATS_PER_ORB
        self.TOTAL_NUM_SATS = self.LEO_NUM_SATS + self.MEO_NUM_SATS

    def calculate(
            self,
            output_generated_data_dir,      
            duration_s,
            time_step_ms,
            isl_selection,           
            gs_selection,             
            dynamic_state_algorithm,  
            num_threads
    ):

        # Add base name to setting
        name = self.BASE_NAME + "_" + isl_selection + "_" + gs_selection + "_" + dynamic_state_algorithm

        # Create output directories
        if not os.path.isdir(output_generated_data_dir):
            os.makedirs(output_generated_data_dir, exist_ok=True)
        if not os.path.isdir(output_generated_data_dir + "/" + name):
            os.makedirs(output_generated_data_dir + "/" + name, exist_ok=True)

        # Ground stations
        print("Generating ground stations...")
        if gs_selection == "ground_stations_top_100":
            satgen.extend_ground_stations(
                "input_data/ground_stations_cities_sorted_by_estimated_2025_pop_top_100.basic.txt",
                output_generated_data_dir + "/" + name + "/ground_stations.txt"
            )
        elif gs_selection == "ground_stations_paris_moscow_grid":
            satgen.extend_ground_stations(
                "input_data/ground_stations_paris_moscow_grid.basic.txt",
                output_generated_data_dir + "/" + name + "/ground_stations.txt"
            )
        else:
            raise ValueError("Unknown ground station selection: " + gs_selection)

        # TLEs - Generate for both LEO and MEO
        print("Generating TLEs for LEO shell...")
        satgen.generate_tles_from_scratch_manual(
            output_generated_data_dir + "/" + name + "/tles_leo.txt",
            self.NICE_NAME + "-LEO",
            self.LEO_NUM_ORBS,
            self.LEO_NUM_SATS_PER_ORB,
            self.LEO_PHASE_DIFF,
            self.LEO_INCLINATION_DEGREE,
            self.LEO_ECCENTRICITY,
            self.LEO_ARG_OF_PERIGEE_DEGREE,
            self.LEO_MEAN_MOTION_REV_PER_DAY
        )
        
        print("Generating TLEs for MEO shell...")
        satgen.generate_tles_from_scratch_manual(
            output_generated_data_dir + "/" + name + "/tles_meo.txt",
            self.NICE_NAME + "-MEO",
            self.MEO_NUM_ORBS,
            self.MEO_NUM_SATS_PER_ORB,
            self.MEO_PHASE_DIFF,
            self.MEO_INCLINATION_DEGREE,
            self.MEO_ECCENTRICITY,
            self.MEO_ARG_OF_PERIGEE_DEGREE,
            self.MEO_MEAN_MOTION_REV_PER_DAY
        )
        
        # Merge TLE files
        print("Merging TLE files...")
        with open(output_generated_data_dir + "/" + name + "/tles.txt", "w+") as f_out:
          
            
            total_sats = self.LEO_NUM_SATS + self.MEO_NUM_SATS
            f_out.write("%d %d\n" % (1, total_sats))  
            
            # Read and write LEO TLEs 
            with open(output_generated_data_dir + "/" + name + "/tles_leo.txt", "r") as f_leo:
                lines = f_leo.readlines()
                for line in lines[1:]:  
                    f_out.write(line)
            
            # Read and write MEO TLEs 
            with open(output_generated_data_dir + "/" + name + "/tles_meo.txt", "r") as f_meo:
                lines = f_meo.readlines()[1:]  
                
                # Process in groups of 3 lines 
                for i in range(0, len(lines), 3):
                    if i + 2 >= len(lines):
                        break
                    
                    name_line = lines[i].strip()
                    tle_line1 = lines[i + 1].strip()
                    tle_line2 = lines[i + 2].strip()
                    
                    # Adjust name line: update satellite ID
                    parts = name_line.split()
                    if len(parts) >= 2:
                        old_id = int(parts[1])
                        new_id = old_id + self.LEO_NUM_SATS
                        f_out.write(parts[0] + " " + str(new_id) + "\n")
                    else:
                        f_out.write(name_line + "\n")
                    
                    # Adjust TLE line 1: update satellite number
                    if len(tle_line1) >= 8 and tle_line1[0] == '1':
                        try:
                            old_satnum = int(tle_line1[2:7])
                            new_satnum = old_satnum + self.LEO_NUM_SATS
                            # Reconstruct line with new satnum
                            new_line = "1 %05dU" % new_satnum + tle_line1[8:68]
                            # Recalculate checksum
                            checksum = calculate_tle_line_checksum(new_line[:68])
                            f_out.write(new_line[:68] + str(checksum) + "\n")
                        except:
                            f_out.write(tle_line1 + "\n")
                    else:
                        f_out.write(tle_line1 + "\n")
                    
                    # Adjust TLE line 2: update satellite number
                    if len(tle_line2) >= 7 and tle_line2[0] == '2':
                        try:
                            old_satnum = int(tle_line2[2:7])
                            new_satnum = old_satnum + self.LEO_NUM_SATS
                            # Reconstruct line with new satnum
                            new_line = "2 %05d" % new_satnum + tle_line2[7:68]
                            # Recalculate checksum
                            checksum = calculate_tle_line_checksum(new_line[:68])
                            f_out.write(new_line[:68] + str(checksum) + "\n")
                        except:
                            f_out.write(tle_line2 + "\n")
                    else:
                        f_out.write(tle_line2 + "\n")

        # ISLs
        print("Generating ISLs...")
        if isl_selection == "isls_plus_grid":
            # Only LEO ISLs
            satgen.generate_plus_grid_isls(
                output_generated_data_dir + "/" + name + "/isls.txt",
                self.LEO_NUM_ORBS,
                self.LEO_NUM_SATS_PER_ORB,
                isl_shift=0,
                idx_offset=0
            )
        elif isl_selection == "isls_plus_grid_with_cross_layer":
            # LEO ISLs + MEO ISLs + Cross-layer ISLs.
            _max_leo_per_meo = max(40, (self.LEO_NUM_SATS + self.MEO_NUM_SATS - 1) // self.MEO_NUM_SATS)
            satgen.generate_multilayer_isls(
                output_generated_data_dir + "/" + name + "/isls.txt",
                self.LEO_NUM_ORBS,
                self.LEO_NUM_SATS_PER_ORB,
                self.MEO_NUM_ORBS,
                self.MEO_NUM_SATS_PER_ORB,
                self.LEO_NUM_SATS,
                isl_shift=0,
                max_cross_layer_isl_length_m=self.MAX_CROSS_LAYER_ISL_LENGTH_M,
                max_leo_per_meo=_max_leo_per_meo
            )
        elif isl_selection == "isls_none":
            satgen.generate_empty_isls(
                output_generated_data_dir + "/" + name + "/isls.txt"
            )
        else:
            raise ValueError("Unknown ISL selection: " + isl_selection)

        # Description
        print("Generating description...")
        satgen.generate_description(
            output_generated_data_dir + "/" + name + "/description.txt",
            self.MAX_GSL_LENGTH_M,
            self.MAX_ISL_LENGTH_M,
            leo_num_sats=self.LEO_NUM_SATS  
        )

        # GSL interfaces
        ground_stations = satgen.read_ground_stations_extended(
            output_generated_data_dir + "/" + name + "/ground_stations.txt"
        )
        if dynamic_state_algorithm == "algorithm_free_one_only_gs_relays" \
                or dynamic_state_algorithm == "algorithm_free_one_only_over_isls" \
                or dynamic_state_algorithm == "algorithm_free_one_multi_layer":
            gsl_interfaces_per_satellite = 1
        elif dynamic_state_algorithm == "algorithm_paired_many_only_over_isls":
            gsl_interfaces_per_satellite = len(ground_stations)
        else:
            raise ValueError("Unknown dynamic state algorithm: " + dynamic_state_algorithm)

        print("Generating GSL interfaces info..")
        satgen.generate_simple_gsl_interfaces_info(
            output_generated_data_dir + "/" + name + "/gsl_interfaces_info.txt",
            self.TOTAL_NUM_SATS,  
            len(ground_stations),
            gsl_interfaces_per_satellite,  
            1,  
            1,  
            1   
        )

        # Forwarding state
        print("Generating forwarding state...")
        satgen.help_dynamic_state(
            output_generated_data_dir,
            num_threads,  
            name,
            time_step_ms,
            duration_s,
            self.MAX_GSL_LENGTH_M,
            self.MAX_ISL_LENGTH_M,
            dynamic_state_algorithm,
            True
        )


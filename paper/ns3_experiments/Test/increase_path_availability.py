#!/usr/bin/env python3
"""
Script to analyze and suggest ways to increase path availability.
"""

import math

def calculate_gsl_range(altitude_m, elevation_deg):
    """Calculate GSL range for given altitude and elevation angle."""
    cone_radius_m = altitude_m / math.tan(math.radians(elevation_deg))
    earth_radius = 6378135.0
    gsl_length_m = math.sqrt(math.pow(cone_radius_m, 2) + math.pow(altitude_m, 2))
    return gsl_length_m / 1000.0  # Return in km

def main():
    print("=" * 70)
    print("Ways to Increase Path Availability")
    print("=" * 70)
    print()
    
    # Current settings
    LEO_ALTITUDE_M = 630000  # 630 km
    MEO_ALTITUDE_M = 8063000  # 8,063 km
    
    print("1. INCREASE GSL RANGE (Easiest - No regeneration needed)")
    print("-" * 70)
    print("Current LEO GSL range: 10° elevation = {:.1f} km".format(
        calculate_gsl_range(LEO_ALTITUDE_M, 10.0)))
    print("Current MEO GSL range: 30° elevation = {:.1f} km".format(
        calculate_gsl_range(MEO_ALTITUDE_M, 30.0)))
    print()
    print("Options:")
    print("  a) Lower LEO elevation to 5°:  {:.1f} km (+{:.1f} km)".format(
        calculate_gsl_range(LEO_ALTITUDE_M, 5.0),
        calculate_gsl_range(LEO_ALTITUDE_M, 5.0) - calculate_gsl_range(LEO_ALTITUDE_M, 10.0)))
    print("  b) Lower MEO elevation to 10°: {:.1f} km (+{:.1f} km)".format(
        calculate_gsl_range(MEO_ALTITUDE_M, 10.0),
        calculate_gsl_range(MEO_ALTITUDE_M, 10.0) - calculate_gsl_range(MEO_ALTITUDE_M, 30.0)))
    print("  c) Lower MEO elevation to 5°:  {:.1f} km (+{:.1f} km)".format(
        calculate_gsl_range(MEO_ALTITUDE_M, 5.0),
        calculate_gsl_range(MEO_ALTITUDE_M, 5.0) - calculate_gsl_range(MEO_ALTITUDE_M, 30.0)))
    print()
    print("⚠ Note: Lower elevation angles may cause interference issues in real systems")
    print()
    
    print("2. USE DIFFERENT GROUND STATION PAIRS")
    print("-" * 70)
    print("Current pair: Rio de Janeiro (index 18) → St. Petersburg (index 73)")
    print()
    print("Alternative pairs with better coverage:")
    print("  a) São Paulo (index 3) → Moscow (index 21): ~11,200 km")
    print("     - São Paulo is near Rio, may have better coverage")
    print("     - Moscow is near St. Petersburg, may have better coverage")
    print()
    print("  b) Buenos Aires (index 12) → Moscow (index 21): ~12,500 km")
    print("     - Different location, may have better satellite coverage")
    print()
    print("  c) New York (index 9) → Moscow (index 21): ~7,500 km")
    print("     - Shorter distance, but still long enough to show MEO benefits")
    print()
    print("  d) Los Angeles (index 20) → Moscow (index 21): ~9,500 km")
    print("     - Good coverage in both regions")
    print()
    
    print("3. USE MORE GROUND STATIONS")
    print("-" * 70)
    print("Current: Using top 100 cities")
    print("Option: Use top 1000 cities (more ground stations = more coverage)")
    print("  - File: ground_stations_cities_sorted_by_estimated_2025_pop_top_1000.basic.txt")
    print("  - Requires: Regenerating constellation")
    print()
    
    print("4. INCREASE CONSTELLATION SIZE")
    print("-" * 70)
    print("Current: 1,156 LEO satellites (35.7% of planned Kuiper-630)")
    print("Options:")
    print("  a) Use Starlink-550 constellation: 4,408 satellites (better coverage)")
    print("  b) Extend Kuiper-630: Use more satellites from planned constellation")
    print("  - Requires: Modifying constellation generation code")
    print()
    
    print("=" * 70)
    print("RECOMMENDED APPROACH (Easiest to implement):")
    print("=" * 70)
    print("1. Lower MEO GSL elevation from 30° to 10° (or 5°)")
    print("   - This will significantly increase MEO coverage")
    print("   - MEO satellites can help relay when LEO coverage is poor")
    print()
    print("2. Try São Paulo → Moscow instead of Rio → St. Petersburg")
    print("   - Similar distance (~11,200 km)")
    print("   - May have better coverage")
    print()
    print("3. Regenerate constellation with new settings")
    print("=" * 70)

if __name__ == "__main__":
    main()


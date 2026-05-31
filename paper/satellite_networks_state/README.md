# Satellite network state generation

Generates static and time-varying state for Kuiper, Starlink, and Telesat
constellations used in the Hypatia paper. Output under `gen_data/` feeds
`satgenpy_analysis` and `ns3-sat-sim`.

It builds upon:

* `satgenpy` : Python framework for TLEs, ISLs, ground stations, and dynamic state

  Located at: `satgenpy/`

## Getting started

1. Install dependencies:
   ```
   See satgenpy/README.md
   ```

2. Generate all constellations used in the paper (local):
   ```
   cd paper/satellite_networks_state
   bash generate_all_local.sh
   ```
   Or distribute work remotely:
   ```
   python generate_all_remote.py
   ```

3. Expect output similar to:
   ```
   gen_data/
   |-- 25x25_algorithm_free_one_only_over_isls
   |-- kuiper_630_isls_none_ground_stations_paris_moscow_grid_algorithm_free_one_only_gs_relays
   |-- kuiper_630_isls_plus_grid_ground_stations_top_100_algorithm_free_one_only_over_isls
   |-- starlink_550_isls_plus_grid_ground_stations_top_100_algorithm_free_one_only_over_isls
   |-- telesat_1015_isls_plus_grid_ground_stations_top_100_algorithm_free_one_only_over_isls
   ```

Ground-station input files live in `input_data/` (see `input_data/README.md`).

# Satellite network input data

Ground-station lists and helper scripts used when generating constellation state
with `satgenpy`. These files are read by the generators under
`paper/satellite_networks_state/`.

* `ground_stations_cities_sorted_by_estimated_2025_pop_top_1000.basic.txt` : Top 1000 cities by estimated 2025 population
* `ground_stations_cities_sorted_by_estimated_2025_pop_top_100.basic.txt` : First 100 cities (used in most paper experiments)
* `ground_stations_paris_moscow_grid.basic.txt` : Paris, Moscow, and a relay grid between them
* `generate_paris_moscow_grid.py` : Script that generates the Paris–Moscow grid file
* `legacy/` : Older data files (may be removed later)

## Getting started

1. Use the top-100 list in constellation generators (default in `generate_all_local.sh`):
   ```
   ground_stations_top_100
   ```
   which resolves to `ground_stations_cities_sorted_by_estimated_2025_pop_top_100.basic.txt`.

2. For the Paris–Moscow ground-relay experiment, use `ground_stations_paris_moscow_grid.basic.txt`
   via the `ground_stations_paris_moscow_grid` preset in the relevant `main_*.py` scripts.

3. Regenerate the grid file after changing coordinates:
   ```
   cd paper/satellite_networks_state/input_data
   python generate_paris_moscow_grid.py
   ```

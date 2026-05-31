# Satellite network visualization with Cesium

Interactive 3D visualizations of constellations, paths, and link utilization.
Scripts emit CesiumJS HTML under `viz_output/`.

It makes use of:

* `Cesium Ion` : Online globe API (access token required)

  https://cesium.com/

## Getting started

1. Obtain a Cesium access token at https://cesium.com/

2. Insert the token in `static_html/top.html` (line 10):
   ```javascript
   Cesium.Ion.defaultAccessToken = '<CESIUM_ACCESS_TOKEN>';
   ```

3. Run a script from `scripts/` (example: constellation view):
   ```
   cd satviz/scripts
   python visualize_constellation.py
   ```

4. Open the generated HTML under `satviz/viz_output/`.

## Scripts

* `visualize_constellation.py` : Full constellation (Starlink / Kuiper / Telesat blocks in file)

* `visualize_horizon_over_time.py` : Satellite sky plot for a fixed observer

* `visualize_path.py` : Shortest path at a time instant

* `visualize_path_no_isl.py` : Paths without ISLs (ground relays)

* `visualize_path_wise_utilization.py` : Per-path link utilization

* `visualize_utilization.py` : Constellation-wide utilization

## Paper figures (satviz)

| Paper fig. | Script | Notes |
|------------|--------|--------|
| Fig. 11 | `visualize_constellation.py` | Uncomment one constellation block |
| Fig. 12 | `visualize_horizon_over_time.py` | Default observer: St. Petersburg |
| Fig. 13, 16(a), 17(a) | `visualize_path.py` | Set `GEN_TIME`, `path_file` |
| Fig. 14 | `visualize_path_wise_utilization.py` | Set `GEN_TIME`, `path_file`, `IN_UTIL_FILE` |
| Fig. 15 | `visualize_utilization.py` | Set `GEN_TIME`, `IN_UTIL_FILE` |
| Fig. 16(b), 17(b) | `visualize_path_no_isl.py` | No ISL topology |

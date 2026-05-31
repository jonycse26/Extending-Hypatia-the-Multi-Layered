# ns-3 packet-level experiments

Runs ns-3 simulations using forwarding state from `satellite_networks_state/`.
Each subdirectory is a self-contained step pipeline (generate runs → simulate → plot).

Prerequisites:

* Built `ns3-sat-sim` (see `ns3-sat-sim/README.md`)

* Generated dynamic state under `paper/satellite_networks_state/gen_data/`

## Getting started

1. Build the simulator:
   ```
   See ns3-sat-sim/README.md
   ```

2. Run an experiment folder (example: A-to-B pairs):
   ```
   cd paper/ns3_experiments/a_b
   python step_1_generate_runs.py
   python step_2_run.py
   python step_3_generate_plots.py
   ```

## Experiment folders

* `a_b/` : Directed ground-station pairs (RTT, CWND, ISL vs ground-relay cases)

* `traffic_matrix/` : Rio de Janeiro → St. Petersburg with background permutation traffic

* `traffic_matrix_load/` : Scalability vs link rate and simulation duration

* `multilayer/` : LEO + MEO Kuiper experiments (see `multilayer/README.md`)

### A-to-B ground stations (Kuiper-610)

Ground stations are the top-100 cities file:

```
satgenpy/data/ground_stations_cities_sorted_by_estimated_2025_pop_top_100.basic.txt
```

Kuiper has 34×34 = 1156 satellites; ground-station node IDs are 1156–1255.
Directed pairs run in `a_b/` include Rio→St. Petersburg, Manila→Dalian,
Istanbul→Nairobi, and Paris→Moscow (plus Paris–Moscow ground-relay variant).

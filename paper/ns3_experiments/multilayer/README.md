# Multi-layer satellite constellation experiments

Packet-level evaluation of Kuiper LEO + MEO vs LEO-only for long-haul pairs.
Uses forwarding state from `paper/satellite_networks_state/` and `ns3-sat-sim`.

Main pieces:

* `step_0_generate_constellation.py` : Generate multilayer and LEO-only `gen_data/`

* `step_1_generate_runs.py` : Create run configs under `runs/`

* `step_2_run.py` : Execute ns-3 simulations

* `step_3_generate_plots.py` : Gnuplot PDFs under `pdf/`

* `evaluation_utils.py` : Metrics extraction and CSV export

* `run_list.py` : Experiment pairs, timing (`dynamic_state_500ms_for_50s` by default)

* `example_1_threshold_sensitivity.py` : MEO hop/distance threshold sweep (standalone)

* `example_2_comparison.py` : Experiment 1 comparison helper (standalone)

* `example_3_distance_based_scenario_analysis.py` : Short / medium / long pairs (standalone)

See `EXAMPLES.md` and `QUICK_START.md` for detail.

## Getting started

1. Install Hypatia dependencies and build ns-3:
   ```
   See <hypatia>/README.md and ns3-sat-sim/README.md
   ```

2. Generate constellation state (first time; 50 s, 500 ms timesteps):
   ```
   cd paper/ns3_experiments/multilayer
   python step_0_generate_constellation.py
   ```
   Check progress:
   ```
   python check_progress.py
   ```

3. Generate run directories:
   ```
   python step_1_generate_runs.py
   ```

4. Run simulations (up to 4 parallel):
   ```
   python step_2_run.py
   ```

5. Generate plots:
   ```
   python step_3_generate_plots.py
   ```

6. Export scorecard metrics and figures (optional):
   ```
   python export_multilayer_metrics_table.py --duration-s 25 --time-step-ms 1000
   python plot_figure_h_multilayer_advantage.py --duration-s 25 --time-step-ms 1000
   python plot_figure_y_multilayer_improvement_ratios.py --duration-s 25 --time-step-ms 1000
   ```

## Experiments (step pipeline)

* **Experiment 1** : Multilayer vs LEO-only — Mumbai–Lima, Lima–Karachi, Tokyo–Buenos Aires (`experiment1_pairs_*` in `run_list.py`)

* **Experiment 2** : `threshold_test_*` — same three pairs, distance-tier labels

* **Experiment 3** : `example3_distance_{short,medium,long}_*_tcp` — Manila–Dalian, Istanbul–Nairobi, Rio–St. Petersburg

Multilayer ground-station node IDs are **LEO id + 36** (`run_list.OFFSET_DIFF`).

## Results

* `runs/<run_name>/logs_ns3/` — TCP RTT, CWND, `isl_utilization.csv`, etc.

* `pdf/<run_name>/` — Plots after step 3

* `multilayer_all_experiments_metrics.csv` — Per-run scalars for Figure H / Y

## Notes

* Default routing uses MEO when path distance or hop count exceeds thresholds in `run_list.py`.

* Kuiper-630 is a partial constellation (~1,156 LEO sats); coverage gaps affect both LEO-only and multilayer runs equally.

# Plot Overview (A to L)

This file summarizes how to calculate the data files and generate Figures A-L in `paper/ns3_experiments/multilayer`.

## 1) Global timing baseline

All figure scripts are aligned to:

- `simulation_end_time_s = 25`
- `dynamic_state_update_interval_ms = 1000`

from `run_list.py`.

## 2) Core pipeline (data generation)

Run from this directory:

```bash
cd paper/ns3_experiments/multilayer
```

Generate and simulate runs:

```bash
python3 step_1_generate_runs.py
python3 step_2_run.py
python3 step_3_generate_plots.py
```

This populates:

- `runs/<run_name>/logs_ns3/` (raw ns-3 logs)
- `data/<run_name>/` (derived CSVs used by plotting scripts)

## 3) Common calculated CSV files

For each TCP run (`*_tcp`), key files under `data/<run_name>/`:

- `tcp_flow_0_rtt.csv` (RTT samples from ns-3 TCP trace)
- `tcp_flow_0_cwnd.csv` (CWND trace)
- `tcp_flow_0_progress.csv` (cumulative bytes over time)
- `tcp_flow_0_rate_in_intervals.csv` (interval throughput, Mbps)
- `computed_rtt_ms_ts.csv` (used by Figure A; can be derived from RTT CSV)
- `bdp_plus_q_packets_ts.csv` (used by Figure B)

For pings (`*_pings`):

- `ping_<from>_to_<to>_rtt.csv`
- `ping_<from>_to_<to>_out_of_order_in_intervals.csv`

Aggregate metrics table:

```bash
python3 export_multilayer_metrics_table.py
```

Produces:

- `multilayer_all_experiments_metrics.csv`

## 4) Metrics: list and how they are calculated

Most scalar metrics are computed in `evaluation_utils.extract_metrics()` and exported by:

```bash
python3 export_multilayer_metrics_table.py
```

which writes `multilayer_all_experiments_metrics.csv`.

### 4.1 Transport metrics (from TCP logs)

- `avg_throughput_mbps`
  - Primary: mean of `tcp_flow_0_rate_in_intervals.csv` (uses non-zero rates if available).
  - Fallback: from progress slope:
    - `((bytes_last - bytes_first) * 8) / ((time_last - time_first) * 1e6)`.

- `avg_rtt_ms`
  - Mean of RTT samples from `tcp_flow_0_rtt.csv` converted ns to ms.

- `rtt_variation_ms`
  - `max(rtt_ms) - min(rtt_ms)` from TCP RTT samples.

- `rtt_variation_ratio`
  - `max(rtt_ms) / min(rtt_ms)` (if min > 0).

- `geodesic_rtt_ms`
  - In this implementation, set to `min(rtt_ms)` as a best-effort baseline.

- `rtt_stretch`
  - `avg_rtt_ms / min(rtt_ms)` (if min > 0).

- `bytes_transferred_final`
  - Last byte counter from `tcp_flow_0_progress.csv`.

- `active_transfer_duration_s`
  - `(last_progress_time - first_time_with_bytes_gt_0) / 1e9`.

- `completion_time_s`
  - If schedule target bytes is reached: `(first_time_bytes_ge_target - first_time_with_bytes_gt_0) / 1e9`.
  - Otherwise `NaN`.

- `transfer_complete`
  - `True` if completion criterion above is met; else `False`.

### 4.2 Ping/out-of-order metric

- `out_of_order_rate`
  - Derived from `logs_ns3/pingmesh.csv` for pings runs, using interval counting in evaluation utils.
  - Units: events per second.

### 4.3 ISL utilization metrics (from `logs_ns3/isl_utilization.csv`)

Classification is by satellite IDs and constellation type:

- `leo_leo_isl_max_util`: max utilization over LEO-LEO ISLs.
- `leo_leo_isl_mean_util_nz`: mean utilization over non-zero LEO-LEO samples.
- `meo_touching_isl_max_util`: max utilization on links where either endpoint is MEO.
- `meo_touching_isl_mean_util_nz`: mean non-zero utilization for MEO-touching links.
- `meo_meo_isl_max_util`: max utilization over MEO-MEO ISLs.
- `meo_meo_isl_mean_util_nz`: mean non-zero utilization over MEO-MEO ISLs.
- `meo_used_any`: `True` if any MEO-touching utilization sample is non-zero.

### 4.4 Path-based metrics (from forwarding snapshots `fstate_*.txt`)

Computed by reconstructing source-to-destination forwarding paths over time:

- `avg_hop_count`
  - Mean hop count over valid reconstructed snapshots.

- `avg_path_stretch`
  - For each valid snapshot: `hop_count / min_hop_count_over_snapshots`; then averaged.

- `path_stability_ratio`
  - Ratio of unchanged path signatures across consecutive valid snapshots.

- `path_change_count`
  - Number of times path signature changes between consecutive valid snapshots.

- `hop_count_variation`
  - `max(hop_count) - min(hop_count)` over valid snapshots.

- `hop_count_ratio`
  - `max(hop_count) / min(hop_count)` (if min > 0).

- `meo_usage_ratio`
  - Per snapshot: `meo_sat_count / hop_count` (or `0` when no MEO on valid path).
  - Exported value is average over valid snapshots.

- `bottleneck_utilization`
  - For each valid reconstructed path, find minimum ISL utilization across path edges.
  - Metric is average of those per-snapshot minima.

### 4.5 Metadata / bookkeeping columns in the CSV

- `run_name`, `experiment`, `scenario_type`, `distance_tier`, `from_id`, `to_id`, `error`.

---

## 5) Figure-by-figure mapping

- **Figure A**: `plot_figure_a_rtt_behavior.py`
  - Inputs: `computed_rtt_ms_ts.csv` (fallback from `tcp_flow_0_rtt.csv`)

- **Figure B**: `plot_figure_b_cwnd_vs_bdp.py`
  - Inputs: `tcp_flow_0_cwnd.csv`, `bdp_plus_q_packets_ts.csv`

- **Figure C**: `plot_figure_c_protocol_outcome.py`
  - Inputs: `tcp_flow_0_rtt.csv`, `tcp_flow_0_rate_in_intervals.csv`
  - Note: CWND is intentionally removed from Figure C.

- **Figure D**: `plot_figure_d_rtt_stretch.py`
  - Inputs: RTT-related series from `data/` (clipped to `duration_s`)

- **Figure E**: `plot_figure_e_rtt_variation.py`
  - Inputs: RTT series from `data/` (clipped)

- **Figure F**: `plot_figure_f_path_dynamics.py`
  - Inputs: `multilayer_all_experiments_metrics.csv`

- **Figure G**: `plot_figure_g_out_of_order.py`
  - Inputs: ping OOO CSV + TCP CWND/rate CSV

- **Figure H**: `plot_figure_h_multilayer_advantage.py`
  - Inputs: `multilayer_all_experiments_metrics.csv`

- **Figure I**: `plot_figure_i_long_path_comparison.py`
  - Inputs: experiment-3 run folders + extracted metrics

- **Figure J**: `plot_figure_j_load_shift.py`
  - Inputs: `multilayer_all_experiments_metrics.csv`

- **Figure K**: `plot_figure_k_cumulative_bytes.py`
  - Inputs: `tcp_flow_0_progress.csv`

- **Figure L**: `plot_figure_l_load_curve.py`
  - Inputs:
    - `figure-l load-curve/figure_l_load_curve_runs.csv` (manifest)
    - `multilayer_all_experiments_metrics.csv`
  - Needs at least 2 distinct load points for a real curve.

## 6) Regenerate all figures quickly

```bash
python3 export_multilayer_metrics_table.py

python3 plot_figure_a_rtt_behavior.py
python3 plot_figure_b_cwnd_vs_bdp.py
python3 plot_figure_c_protocol_outcome.py
python3 plot_figure_d_rtt_stretch.py
python3 plot_figure_e_rtt_variation.py
python3 plot_figure_f_path_dynamics.py
python3 plot_figure_g_out_of_order.py
python3 plot_figure_h_multilayer_advantage.py
python3 plot_figure_i_long_path_comparison.py
python3 plot_figure_j_load_shift.py
python3 plot_figure_k_cumulative_bytes.py --all-pairs
python3 plot_figure_l_load_curve.py --with-isl-panel
```

## 7) If a CSV is missing for one pair

Regenerate only that pair (example index `0` = Mumbai-Lima):

```bash
python3 example_2_comparison.py --only-pair-indices 0 --run-ns3 --skip-bar-metrics
```

Pair indices:

- `0` Mumbai-Lima
- `1` Lima-Karachi
- `2` Tokyo-Buenos-Aires


# Paper figure plotting

Gnuplot-based scripts to reproduce PDF/PNG figures after `ns3_experiments` and
`satgenpy_analysis` data exist.

It makes use of:

* `gnuplot` : Figure rendering

* `exputil` : Plot orchestration (via `plot_all.py`)

## Getting started

1. Install gnuplot:
   ```
   sudo apt-get install gnuplot
   ```

2. Generate all PDF figures:
   ```
   cd paper/figures
   python plot_all.py
   ```

3. Convert PDFs to PNG (faster to view large plots):
   ```
   python generate_pngs.py
   ```

## Mapping paper figures to PDFs

* Fig. 1: (Made with draw.io)
* Fig. 2: `traffic_matrix_load_scalability/pdf/plot_goodput_rate_vs_slowdown.pdf`
* Fig. 3(a–c): `a_b/multiple_rtt_matching/pdf/time_vs_multiple_rtt_pair_*.pdf`
* Fig. 4(a–c): `a_b/tcp_cwnd/pdf/time_vs_cwnd_and_bdp_plus_queue_pair_*.pdf`
* Fig. 5(a–c): `a_b/tcp_mayhem/pdf/time_vs_*.pdf`
* Fig. 6–9: `constellation_comparison/general_ecdfs/pdf/...`
* Fig. 10: `traffic_matrix_unused_bandwidth/pdf/plot_specific_tm_time_vs_available_bandwidth_over_path.pdf`
* Fig. 11–17: satviz (see `satviz/README.md`)
* Fig. 18–19: `a_b/tcp_isls_vs_gs_relays/pdf/...`

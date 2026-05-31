# Constellation analysis with satgenpy

Offline analysis of forwarding-state time series produced in
`paper/satellite_networks_state/`. Computes path, RTT, and hop statistics for
Kuiper, Starlink, and Telesat scenarios used in the paper.

It builds upon:

* `satgenpy` : Constellation generation and routing (see `satgenpy/README.md`)

  Located at: `satgenpy/`

## Getting started

1. Install dependencies (same as satgenpy):
   ```
   See satgenpy/README.md
   ```

2. Generate satellite network state first:
   ```
   See paper/satellite_networks_state/README.md
   ```

3. Run the full analysis (can take a long time):
   ```
   cd paper/satgenpy_analysis
   python perform_full_analysis.py
   ```

4. Results are written under `paper/satgenpy_analysis/data/<constellation name>/`.

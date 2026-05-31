"""
Shared experiment-1 scalars for Figure H and Figure Y.

Both figures use the same fields from ``multilayer_all_experiments_metrics.csv``:
  - ``avg_hop_count``
  - ``bottleneck_utilization``
"""

import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_METRICS = os.path.join(SCRIPT_DIR, "multilayer_all_experiments_metrics.csv")

from plot_figure_h_multilayer_advantage import _collect_pairwise, _load_rows


def collect_figure_y_pairs(rows):
    """Map Figure H pairwise dicts to Figure Y connected-dot records."""
    out = []
    for p in _collect_pairwise(rows):
        out.append(
            {
                "pair": p["pair"],
                "run_leo": p["rn_leo"],
                "run_ml": p["rn_ml"],
                "hop_leo": p["leo"]["avg_hop_count"],
                "hop_ml": p["ml"]["avg_hop_count"],
                "util_leo": p["leo"]["bottleneck_utilization"],
                "util_ml": p["ml"]["bottleneck_utilization"],
            }
        )
    return out


def load_experiment1_pairs(metrics_csv=DEFAULT_METRICS):
    if not metrics_csv:
        raise ValueError("metrics_csv path required")
    return collect_figure_y_pairs(_load_rows(metrics_csv))

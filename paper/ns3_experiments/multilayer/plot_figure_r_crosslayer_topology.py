#!/usr/bin/env python3
"""
Figure R — Topology + physical sanity (Option B companion to Figure N)

**Purpose:** separate (i) what the **ISL generator** installs from (ii) what a **straight chord**
through ECI would do relative to the Earth sphere.

Panels:

- **(a)** LEO cross-layer **degree** from the generator (0 vs 1): driven by orbit/slot mapping
  plus ``max_leo_per_meo`` (not nearest-MEO).
- **(b)** Histogram: assigned MEO vs geometrically nearest MEO (3-D distance ratio).
- **(c)** LEO **orbit × slot** heatmap: which cells receive a topological cross-layer edge.
- **(d)** Among **topological** cross-layer edges only: chords **Earth-clear** vs **Earth-blocked**
  (same LOS test as Figure N ``--link-mode physical``).

Outputs ``figure_r_crosslayer_topology_summary.csv`` with the same counts.
"""

import argparse
import csv
import os
import sys
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import numpy.ma as ma

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURE_DIR = os.path.join(SCRIPT_DIR, "figure-r crosslayer topology")
STATE_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "../../satellite_networks_state"))
REPO_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "../../.."))
SATGENPY = os.path.join(REPO_ROOT, "satgenpy")

# Reuse Walker + ISL load from Figure N (same file-level helpers would duplicate); import run.
sys.path.insert(0, SCRIPT_DIR)
import plot_figure_n_multilayer_constellation as fig_n  # noqa: E402


def _cross_layer_pairs(pairs, leo_n):
    """List of (leo_idx, meo_idx) for LEO–MEO edges."""
    out = []
    for a, b in pairs:
        if a < leo_n and b >= leo_n:
            out.append((a, b))
        elif b < leo_n and a >= leo_n:
            out.append((b, a))
    return out


def _wrap_paragraphs(s, width=88):
    """Hard-wrap lines so ``bbox_inches='tight'`` does not blow figure width to thousands of px."""
    blocks = []
    for para in s.split("\n\n"):
        lines_out = []
        for line in para.split("\n"):
            if not line.strip():
                lines_out.append("")
                continue
            lines_out.append(textwrap.fill(line, width=width, break_long_words=False, replace_whitespace=False))
        blocks.append("\n".join(lines_out))
    return "\n\n".join(blocks)


def _los_counts_by_layer(pairs, leo_n, n_sat, x, y, z):
    """Count topological edges and how many straight chords are clear of the Earth sphere."""
    leo_e, meo_e, cross_e = [], [], []
    for a, b in pairs:
        if a < 0 or b < 0 or a >= n_sat or b >= n_sat:
            continue
        la, lb = a < leo_n, b < leo_n
        ma, mb = a >= leo_n, b >= leo_n
        pa = (float(x[a]), float(y[a]), float(z[a]))
        pb = (float(x[b]), float(y[b]), float(z[b]))
        if la and lb:
            leo_e.append((pa, pb))
        elif ma and mb:
            meo_e.append((pa, pb))
        else:
            cross_e.append((pa, pb))

    def _n_clear(segs):
        return sum(1 for s in segs if fig_n.earth_los_clear(s[0], s[1]))

    return {
        "leo_topo": len(leo_e),
        "leo_clear": _n_clear(leo_e),
        "meo_topo": len(meo_e),
        "meo_clear": _n_clear(meo_e),
        "cross_topo": len(cross_e),
        "cross_clear": _n_clear(cross_e),
    }


def _nearest_meo_idx(leo_i, x, y, z, leo_n, n_sat):
    p = np.array([x[leo_i], y[leo_i], z[leo_i]], dtype=float)
    best_j = leo_n
    best_d = 1e300
    for j in range(leo_n, n_sat):
        q = np.array([x[j], y[j], z[j]], dtype=float)
        d = float(np.linalg.norm(p - q))
        if d < best_d:
            best_d = d
            best_j = j
    return best_j, best_d


def main():
    p = argparse.ArgumentParser(description="Figure R: cross-layer topology explanation + stats.")
    p.add_argument(
        "--out-prefix",
        default=os.path.join(FIGURE_DIR, "figure_r_crosslayer_topology"),
        help="Output prefix (.png / .pdf / .csv).",
    )
    p.add_argument(
        "--max-leo-per-meo",
        type=int,
        default=5,
        help="Must match Figure N / constellation (default 5).",
    )
    p.add_argument("--isl-shift", type=int, default=0)
    args = p.parse_args()

    if not os.path.isdir(SATGENPY):
        print("ERROR: satgenpy not found at", SATGENPY)
        return 1

    x, y, z, pairs, leo_n, kmod = fig_n._load_constellation_and_isls(args.max_leo_per_meo, args.isl_shift)
    n_sat = len(x)
    meo_n = kmod.MEO_NUM_ORBS * kmod.MEO_NUM_SATS_PER_ORB

    cross = _cross_layer_pairs(pairs, leo_n)
    leo_with = set(leo for leo, _meo in cross)
    n_cross = len(cross)
    n_leo_with = len(leo_with)
    n_leo_without = leo_n - n_leo_with

    los_stats = _los_counts_by_layer(pairs, leo_n, n_sat, x, y, z)
    cross_blocked = los_stats["cross_topo"] - los_stats["cross_clear"]
    max_if_uncapped = min(leo_n, meo_n * args.max_leo_per_meo)

    rel_overhead = []
    for leo_i, meo_assigned in cross:
        d_ass = float(
            np.linalg.norm(
                np.array([x[leo_i], y[leo_i], z[leo_i]])
                - np.array([x[meo_assigned], y[meo_assigned], z[meo_assigned]])
            )
        )
        _nearest_j, d_near = _nearest_meo_idx(leo_i, x, y, z, leo_n, n_sat)
        if d_near > 1e-9:
            rel_overhead.append((d_ass - d_near) / d_near)

    csv_path = args.out_prefix + "_summary.csv"
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
    with open(csv_path, "w", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(
            [
                "leo_num_sats",
                "meo_num_sats",
                "max_leo_per_meo",
                "cross_layer_isl_count",
                "leo_with_cross_layer",
                "leo_without_cross_layer",
                "max_cross_if_uncapped_estimate",
                "cross_layer_earth_clear_chords",
                "cross_layer_earth_blocked_chords",
                "leo_isl_topo_count",
                "leo_isl_earth_clear",
                "meo_isl_topo_count",
                "meo_isl_earth_clear",
            ]
        )
        w.writerow(
            [
                leo_n,
                meo_n,
                args.max_leo_per_meo,
                n_cross,
                n_leo_with,
                n_leo_without,
                max_if_uncapped,
                los_stats["cross_clear"],
                cross_blocked,
                los_stats["leo_topo"],
                los_stats["leo_clear"],
                los_stats["meo_topo"],
                los_stats["meo_clear"],
            ]
        )
    print("Wrote:", csv_path)

    fig = plt.figure(figsize=(10, 10.8))
    gs = fig.add_gridspec(
        3,
        2,
        height_ratios=[1.0, 1.05, 1.12],
        width_ratios=[1.0, 1.0],
        hspace=0.36,
        wspace=0.30,
        left=0.09,
        right=0.97,
        top=0.93,
        bottom=0.05,
    )

    ax_bar = fig.add_subplot(gs[0, 0])
    ax_hist = fig.add_subplot(gs[0, 1])
    ax_heat = fig.add_subplot(gs[1, 0])
    ax_los = fig.add_subplot(gs[1, 1])
    ax_txt = fig.add_subplot(gs[2, :])
    ax_txt.axis("off")

    ax_bar.bar(
        [0, 1],
        [n_leo_without, n_leo_with],
        color=["#bcbd22", "#7b1fa2"],
        edgecolor="#333333",
        width=0.55,
    )
    ax_bar.set_xticks([0, 1])
    ax_bar.set_xticklabels(["LEO without\ncross-layer ISL", "LEO with\nexactly one"], fontsize=9)
    ax_bar.set_ylabel("Number of LEO satellites", fontsize=10)
    ax_bar.set_title("(a) Cross-layer degree per LEO (generator + cap)", fontsize=11)
    ax_bar.grid(True, axis="y", linestyle=":", alpha=0.65)
    ymax = max(n_leo_without, n_leo_with, 1)
    yoff = max(1.0, ymax * 0.02)
    for xi, v in enumerate([n_leo_without, n_leo_with]):
        ax_bar.text(xi, v + yoff, str(v), ha="center", va="bottom", fontsize=10)

    if rel_overhead:
        ax_hist.hist(rel_overhead, bins=min(40, max(10, len(rel_overhead) // 8)), color="#1f77b4", edgecolor="white")
        ax_hist.axvline(0.0, color="crimson", linestyle="--", linewidth=1.2, label="nearest-MEO (0 excess)")
        ax_hist.set_xlabel("(d_assigned − d_nearest) / d_nearest", fontsize=10)
        ax_hist.set_ylabel("Count (LEO with a cross-layer link)", fontsize=10)
        ax_hist.set_title("(b) Assignment vs geometric nearest MEO (3-D distance)", fontsize=11)
        ax_hist.legend(fontsize=8, loc="upper right")
        ax_hist.grid(True, linestyle=":", alpha=0.55)
    else:
        ax_hist.text(0.5, 0.5, "No cross-layer links", ha="center", va="center", transform=ax_hist.transAxes)

    norb = int(kmod.LEO_NUM_ORBS)
    nslot = int(kmod.LEO_NUM_SATS_PER_ORB)
    grid = np.full((norb, nslot), np.nan, dtype=float)
    for io in range(norb):
        for js in range(nslot):
            s = io * nslot + js
            if s < leo_n:
                grid[io, js] = 1.0 if s in leo_with else 0.0
    him = ax_heat.imshow(
        ma.masked_invalid(grid),
        origin="lower",
        aspect="equal",
        cmap="RdYlGn",
        vmin=0.0,
        vmax=1.0,
        interpolation="nearest",
    )
    ax_heat.set_xlabel("LEO slot index j", fontsize=9)
    ax_heat.set_ylabel("LEO orbit index i", fontsize=9)
    ax_heat.set_title("(c) Generator cross-layer ISL on LEO grid (green=yes, red=no)", fontsize=10)
    fig.colorbar(him, ax=ax_heat, fraction=0.046, pad=0.04, ticks=[0.0, 1.0], label="Has edge")

    if los_stats["cross_topo"] > 0:
        ax_los.barh(
            [0],
            [los_stats["cross_clear"]],
            height=0.45,
            color="#7b1fa2",
            label="Chord clear of Earth",
        )
        ax_los.barh(
            [0],
            [cross_blocked],
            height=0.45,
            left=los_stats["cross_clear"],
            color="#bdbdbd",
            edgecolor="#555555",
            linewidth=0.6,
            label="Chord intersects Earth",
        )
        ax_los.set_yticks([])
        ax_los.set_xlabel("Topological cross-layer ISLs (count)", fontsize=9)
        ax_los.set_title("(d) Straight-line geometry vs Earth (same test as Fig. N physical)", fontsize=10)
        tot_x = max(1, los_stats["cross_topo"])
        ax_los.set_xlim(0, tot_x)
        ax_los.legend(loc="upper right", fontsize=7.5, ncol=1, framealpha=0.92)
        ax_los.grid(True, axis="x", linestyle=":", alpha=0.55)
    else:
        ax_los.text(0.5, 0.5, "No cross-layer edges", ha="center", va="center", transform=ax_los.transAxes)

    note = (
        "Figure R — Option B: topology (satgen) vs physical chord (Earth sphere)\n\n"
        "• Cross-layer rule (not nearest-MEO): "
        r"$\mathrm{meo\_orbit}=\lfloor i\,M_{\mathrm{orb}}/L_{\mathrm{orb}}\rfloor$, "
        r"$\mathrm{meo\_slot}=\lfloor j\,M_{\mathrm{slot}}/L_{\mathrm{slot}}\rfloor$ "
        "then one MEO node; each MEO accepts at most max_leo_per_meo=%d edges (FIFO). "
        "Here %d LEOs have 0 cross-layer ISL and %d have 1 (topological total %d; "
        "theoretical cap-bound upper bound min(LEO, MEO×cap) = %d).\n\n"
        "• Why some LEOs have no MEO link: the mapped MEO bucket is already full (per-MEO cap), "
        "or the generator skips indices past leo_num_sats (not used when the LEO grid is full).\n\n"
        "• Earth panel (d): among those topological cross-layer ISLs, %d chords are strictly "
        "outside the Earth sphere; %d straight chords would intersect the globe in this ECI "
        "geometry (Figure N --link-mode physical omits those).\n\n"
        "• Figure N still uses matplotlib draw-order for depth; this is not an RF visibility model."
        % (
            args.max_leo_per_meo,
            n_leo_without,
            n_leo_with,
            n_cross,
            max_if_uncapped,
            los_stats["cross_clear"],
            cross_blocked,
        )
    )
    note_wrapped = _wrap_paragraphs(note, width=86)
    ax_txt.text(
        0.02,
        0.98,
        note_wrapped,
        transform=ax_txt.transAxes,
        va="top",
        ha="left",
        fontsize=8.8,
        family="sans-serif",
    )

    fig.suptitle(
        "Figure R — Topology vs physical chords (generator policy + Earth LOS)",
        fontsize=11.5,
        y=0.98,
    )

    out_png = args.out_prefix + ".png"
    out_pdf = args.out_prefix + ".pdf"
    # Do not use bbox_inches="tight" here: long caption lines previously forced ~5k px width
    # and made the bar/histogram panels vanishingly thin.
    fig.savefig(out_png, dpi=200, facecolor="white")
    fig.savefig(out_pdf, facecolor="white")
    plt.close(fig)
    print("Wrote:", out_png)
    print("Wrote:", out_pdf)
    return 0


if __name__ == "__main__":
    sys.exit(main())

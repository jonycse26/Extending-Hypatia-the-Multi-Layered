#!/usr/bin/env python3
"""
Figure N — Abstract 3D view: LEO + MEO shells (Kuiper-630 + MEO from main_kuiper_630_meo)

Renders Earth (wireframe sphere), all LEO and MEO satellites, and ISLs from the same
multilayer topology as ``satgen.isls.generate_multilayer_isls`` (plus-grid within each
shell + cross-layer links). Styling follows the usual paper figure: **light blue** thin LEO–LEO
mesh, **deeper blue** LEO nodes, **green** MEO mesh and nodes, **purple** cross-layer links
(slightly thicker than intra-layer), soft grey Earth.

No generated ``gen_data`` folder is required: geometry is reconstructed from
``paper/satellite_networks_state/main_kuiper_630_meo.py`` orbital parameters and the
ISL generator (same as constellation build).
"""

import argparse
import math
import os
import sys
import tempfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 — registers 3d projection
from mpl_toolkits.mplot3d.art3d import Line3DCollection

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURE_DIR = os.path.join(SCRIPT_DIR, "figure-n multilayer abstract")
STATE_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "../../satellite_networks_state"))
REPO_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "../../.."))
SATGENPY = os.path.join(REPO_ROOT, "satgenpy")

EARTH_RADIUS_M = 6378135.0  # WGS72, matches main_helper_multilayer


def _walker_shell_xyz(num_orbit, num_sats_per_orbit, altitude_m, inclination_deg, phase_diff):
    """
    Circular Walker-like shell: same phase layout as satviz/scripts/util.generate_sat_obj_list,
    positions via standard rotation from orbital plane to ECI (argument of latitude u).
    """
    r = EARTH_RADIUS_M + float(altitude_m)
    xs, ys, zs = [], [], []
    for orb in range(num_orbit):
        raan_deg = orb * 360.0 / num_orbit
        orbit_wise_shift = 0.0
        if orb % 2 == 1 and phase_diff:
            orbit_wise_shift = 360.0 / (num_sats_per_orbit * 2.0)
        for n_sat in range(num_sats_per_orbit):
            mean_anomaly_deg = orbit_wise_shift + (n_sat * 360.0 / num_sats_per_orbit)
            omega = math.radians(raan_deg)
            u = math.radians(mean_anomaly_deg)
            inc = math.radians(float(inclination_deg))
            x = r * (math.cos(u) * math.cos(omega) - math.sin(u) * math.sin(omega) * math.cos(inc))
            y = r * (math.cos(u) * math.sin(omega) + math.sin(u) * math.cos(omega) * math.cos(inc))
            z = r * math.sin(u) * math.sin(inc)
            xs.append(x)
            ys.append(y)
            zs.append(z)
    return np.array(xs), np.array(ys), np.array(zs)


def _sphere_mesh(radius, n=48):
    u = np.linspace(0, 2 * np.pi, n)
    v = np.linspace(0, np.pi, n // 2)
    uu, vv = np.meshgrid(u, v)
    x = radius * np.cos(uu) * np.sin(vv)
    y = radius * np.sin(uu) * np.sin(vv)
    z = radius * np.cos(vv)
    return x, y, z


def _load_constellation_and_isls(max_leo_per_meo, isl_shift):
    # satgen lives under satgenpy/; main_kuiper_630_meo pulls in main_helper_multilayer → satgen
    sys.path.insert(0, SATGENPY)
    sys.path.insert(0, STATE_DIR)
    import main_kuiper_630_meo as k  # noqa: E402

    from satgen.isls.generate_multilayer_isls import generate_multilayer_isls  # noqa: E402

    leo_n = k.LEO_NUM_ORBS * k.LEO_NUM_SATS_PER_ORB
    meo_n = k.MEO_NUM_ORBS * k.MEO_NUM_SATS_PER_ORB

    xl, yl, zl = _walker_shell_xyz(
        k.LEO_NUM_ORBS,
        k.LEO_NUM_SATS_PER_ORB,
        k.LEO_ALTITUDE_M,
        k.LEO_INCLINATION_DEGREE,
        k.LEO_PHASE_DIFF,
    )
    xm, ym, zm = _walker_shell_xyz(
        k.MEO_NUM_ORBS,
        k.MEO_NUM_SATS_PER_ORB,
        k.MEO_ALTITUDE_M,
        k.MEO_INCLINATION_DEGREE,
        k.MEO_PHASE_DIFF,
    )

    x = np.concatenate([xl, xm])
    y = np.concatenate([yl, ym])
    z = np.concatenate([zl, zm])

    fd, isl_path = tempfile.mkstemp(suffix="_isls.txt", text=True)
    os.close(fd)
    try:
        pairs = generate_multilayer_isls(
            isl_path,
            k.LEO_NUM_ORBS,
            k.LEO_NUM_SATS_PER_ORB,
            k.MEO_NUM_ORBS,
            k.MEO_NUM_SATS_PER_ORB,
            leo_n,
            isl_shift=isl_shift,
            max_cross_layer_isl_length_m=None,
            max_leo_per_meo=max_leo_per_meo,
        )
    finally:
        try:
            os.remove(isl_path)
        except OSError:
            pass

    return x, y, z, pairs, leo_n, k


def _plot_figure(
    x,
    y,
    z,
    pairs,
    leo_n,
    color_leo_node,
    color_leo_isl,
    color_meo,
    color_cross,
    elev,
    azim,
    title,
    out_prefix,
    dpi,
    earth_alpha,
    line_width_leo,
    line_width_meo,
    line_width_cross,
    alpha_leo_isl,
    alpha_meo_isl,
    alpha_cross,
    size_leo_pt,
    size_meo_pt,
):
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection="3d")

    sx, sy, sz = _sphere_mesh(EARTH_RADIUS_M * 0.999, n=48)
    ax.plot_surface(
        sx,
        sy,
        sz,
        color="#e8e8ea",
        edgecolor="#c8c8cc",
        linewidth=0.12,
        alpha=earth_alpha,
        shade=True,
        antialiased=True,
    )

    n_sat = len(x)

    def is_leo(i):
        return 0 <= i < leo_n

    def is_meo(i):
        return leo_n <= i < n_sat

    seg_leo, seg_meo, seg_cross = [], [], []
    for a, b in pairs:
        if a < 0 or b < 0 or a >= n_sat or b >= n_sat:
            continue
        la, lb = is_leo(a), is_leo(b)
        ma, mb = is_meo(a), is_meo(b)
        pa = (x[a], y[a], z[a])
        pb = (x[b], y[b], z[b])
        if la and lb:
            seg_leo.append((pa, pb))
        elif ma and mb:
            seg_meo.append((pa, pb))
        else:
            seg_cross.append((pa, pb))

    def _add_lc(segments, color, lw, alpha):
        if not segments:
            return
        arr = np.array(segments, dtype=float)
        lc = Line3DCollection(arr, colors=color, linewidths=lw, alpha=alpha)
        ax.add_collection3d(lc)

    _add_lc(seg_leo, color_leo_isl, line_width_leo, alpha_leo_isl)
    _add_lc(seg_meo, color_meo, line_width_meo, alpha_meo_isl)

    ax.scatter(
        x[:leo_n],
        y[:leo_n],
        z[:leo_n],
        c=color_leo_node,
        s=size_leo_pt,
        depthshade=True,
        edgecolors="none",
        linewidths=0,
        zorder=4,
    )
    ax.scatter(
        x[leo_n:],
        y[leo_n:],
        z[leo_n:],
        c=color_meo,
        s=size_meo_pt,
        depthshade=True,
        edgecolors="#1a5c1a",
        linewidths=0.25,
        zorder=5,
    )

    # Cross-layer: draw last so purple links read above the LEO mesh (reference-style).
    _add_lc(seg_cross, color_cross, line_width_cross, alpha_cross)

    ax.set_box_aspect((1, 1, 1))
    lim = float(np.max(np.sqrt(x * x + y * y + z * z)) * 1.12)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_zlim(-lim, lim)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_title(title, fontsize=12, pad=12)
    legend_handles = [
        Line2D(
            [0],
            [0],
            linestyle="",
            marker="o",
            markersize=4.5,
            markerfacecolor=color_leo_node,
            markeredgecolor=color_leo_node,
            label="LEO",
        ),
        Line2D(
            [0],
            [0],
            linestyle="",
            marker="o",
            markersize=6.5,
            markerfacecolor=color_meo,
            markeredgecolor="#1a5c1a",
            label="MEO",
        ),
        Line2D([0], [0], color=color_cross, linewidth=2.2, label="Cross-layer ISL"),
    ]
    ax.legend(handles=legend_handles, loc="upper left", fontsize=9, framealpha=0.9)

    fig.tight_layout()
    out_png = out_prefix + ".png"
    out_pdf = out_prefix + ".pdf"
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    fig.savefig(out_png, dpi=dpi, bbox_inches="tight", facecolor="white")
    fig.savefig(out_pdf, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Wrote:", out_png)
    print("Wrote:", out_pdf)


def main():
    p = argparse.ArgumentParser(description="Figure N: abstract LEO+MEO constellation (3D).")
    p.add_argument(
        "--out-prefix",
        default=os.path.join(FIGURE_DIR, "figure_n_multilayer_constellation"),
        help="Output path prefix (.png / .pdf).",
    )
    p.add_argument("--elev", type=float, default=18.0, help="Matplotlib 3D view elev (deg).")
    p.add_argument("--azim", type=float, default=-60.0, help="Matplotlib 3D view azim (deg).")
    p.add_argument("--dpi", type=int, default=200, help="PNG resolution.")
    p.add_argument(
        "--max-leo-per-meo",
        type=int,
        default=5,
        help="Cross-layer cap passed to generate_multilayer_isls (default 5).",
    )
    p.add_argument("--isl-shift", type=int, default=0, help="ISL shift between orbits (LEO/MEO grid).")
    p.add_argument(
        "--color-leo",
        default="#1565a8",
        help="LEO satellite markers (slightly deeper blue than the LEO mesh).",
    )
    p.add_argument(
        "--color-leo-isl",
        default="#9ec9e8",
        help="LEO–LEO ISLs (light blue mesh; reference-style).",
    )
    p.add_argument("--color-meo", default="#2ca02c", help="MEO edges / nodes.")
    p.add_argument(
        "--color-cross",
        default="#7b1fa2",
        help="Cross-layer ISLs (default: purple).",
    )
    p.add_argument("--earth-alpha", type=float, default=0.42, help="Earth surface alpha.")
    p.add_argument("--lw-leo", type=float, default=0.22, help="LEO intra-layer ISL line width (thin mesh).")
    p.add_argument("--lw-meo", type=float, default=0.42, help="MEO intra-layer ISL line width.")
    p.add_argument("--lw-cross", type=float, default=0.95, help="Cross-layer line width.")
    p.add_argument(
        "--alpha-leo-isl",
        type=float,
        default=0.52,
        help="LEO mesh line opacity (light + semi-transparent).",
    )
    p.add_argument(
        "--alpha-meo-isl",
        type=float,
        default=0.78,
        help="MEO mesh line opacity.",
    )
    p.add_argument(
        "--alpha-cross",
        type=float,
        default=0.9,
        help="Cross-layer link opacity.",
    )
    p.add_argument("--size-leo", type=float, default=4.8, help="LEO scatter point area (matplotlib s).")
    p.add_argument("--size-meo", type=float, default=11.0, help="MEO scatter point area.")
    args = p.parse_args()

    if not os.path.isdir(SATGENPY):
        print("ERROR: satgenpy not found at %s" % SATGENPY)
        return 1
    if not os.path.isfile(os.path.join(STATE_DIR, "main_kuiper_630_meo.py")):
        print("ERROR: main_kuiper_630_meo.py not under %s" % STATE_DIR)
        return 1

    x, y, z, pairs, leo_n, kmod = _load_constellation_and_isls(args.max_leo_per_meo, args.isl_shift)
    meo_n = kmod.MEO_NUM_ORBS * kmod.MEO_NUM_SATS_PER_ORB
    title = (
        "Figure N — LEO (%.0f km) vs MEO (%.0f km) abstract view\n"
        "%d LEO + %d MEO satellites; ISLs from multilayer generator"
        % (
            kmod.LEO_ALTITUDE_M / 1000.0,
            kmod.MEO_ALTITUDE_M / 1000.0,
            leo_n,
            meo_n,
        )
    )
    _plot_figure(
        x,
        y,
        z,
        pairs,
        leo_n,
        args.color_leo,
        args.color_leo_isl,
        args.color_meo,
        args.color_cross,
        args.elev,
        args.azim,
        title,
        args.out_prefix,
        args.dpi,
        args.earth_alpha,
        args.lw_leo,
        args.lw_meo,
        args.lw_cross,
        args.alpha_leo_isl,
        args.alpha_meo_isl,
        args.alpha_cross,
        args.size_leo,
        args.size_meo,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Figure N — LEO + MEO shells (Kuiper-630 + MEO from main_kuiper_630_meo), 3D schematic

**Purpose (default: physical link drawing — Option B):** only draw intra-layer and
cross-layer segments whose **straight-line** path stays strictly outside the Earth sphere
(WGS72 radius). Segments that would geometrically pass through the globe are omitted so the
figure is not misread as a “visibility map” of the abstract topology file.

**Alternative (``--link-mode abstract`` — Option A):** draw every ISL from
``generate_multilayer_isls`` regardless of Earth occlusion; the caption should then state
explicitly that the view is **topology-only**, not physical line-of-sight.

Topology is always from ``satgen.isls.generate_multilayer_isls``: plus-grid per shell,
cross-layer by **orbit/slot quantization** to a target MEO plus ``max_leo_per_meo`` (not
nearest-MEO; many LEOs have no cross-layer edge when the cap is hit — see Figure R).

**Depth cue (matplotlib 3D):** segments are split by projected midpoint depth (``proj3d``)
and drawn before/after the Earth surface for a clearer front/back read (approximate in
``mplot3d``).

No ``gen_data`` folder is required: Walker-style ECI positions from
``paper/satellite_networks_state/main_kuiper_630_meo.py`` and the same ISL generator as the
constellation build.

If you run plain ``python3`` on Ubuntu with a mixed pip/system Matplotlib, this script
detects ``hypatia/.venv`` and re-invokes itself with that interpreter (``sys.prefix`` check,
not symlink equality).
"""

import argparse
import math
import os
import subprocess
import sys
import tempfile


def _maybe_reexec_with_hypatia_venv():
    """
    If ``hypatia/.venv`` exists, re-run this script with that interpreter.

    Mixed installs (Debian ``/usr/lib/python3/dist-packages/mpl_toolkits`` + a pip
    ``~/.local`` Matplotlib) break ``Axes3D`` (``ImportError: cannot import name 'docstring'``).
    The project venv keeps Matplotlib, NumPy, and Astropy aligned.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.normpath(os.path.join(here, "../../.."))
    vpy = os.path.join(repo, ".venv", "bin", "python3")
    if not os.path.isfile(vpy):
        return
    # ``.venv/bin/python3`` is often a symlink to ``/usr/bin/python3``; ``samefile`` is not enough.
    # What matters is whether the venv's ``site-packages`` is active (``sys.prefix``).
    venv_home = os.path.abspath(os.path.join(repo, ".venv"))
    if os.path.abspath(sys.prefix) == venv_home:
        return
    rc = subprocess.call([vpy, os.path.abspath(__file__)] + sys.argv[1:])
    raise SystemExit(rc)


_maybe_reexec_with_hypatia_venv()

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
try:
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 — registers 3d projection
    from mpl_toolkits.mplot3d import proj3d
    from mpl_toolkits.mplot3d.art3d import Line3DCollection
except ImportError as exc:
    _here = os.path.dirname(os.path.abspath(__file__))
    _repo = os.path.normpath(os.path.join(_here, "../../.."))
    _vpy = os.path.join(_repo, ".venv", "bin", "python3")
    sys.stderr.write(
        "Failed to import mpl_toolkits.mplot3d (%r).\n"
        "This is usually a mixed Matplotlib install (system mpl_toolkits + pip user matplotlib).\n"
        "Fix: run with the Hypatia venv if present:\n  %s %s ...\n"
        "Or: PYTHONNOUSERSITE=1 python3 ...\n" % (exc, _vpy, os.path.abspath(__file__))
    )
    raise

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURE_DIR = os.path.join(SCRIPT_DIR, "figure-n multilayer abstract")
STATE_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "../../satellite_networks_state"))
REPO_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "../../.."))
SATGENPY = os.path.join(REPO_ROOT, "satgenpy")

EARTH_RADIUS_M = 6378135.0  # WGS72, matches main_helper_multilayer


def earth_los_clear(p0, p1, earth_radius_m=EARTH_RADIUS_M):
    """
    True if the closed segment p0–p1 lies strictly outside the Earth ball (geometric LOS).

    Uses the closest point on the segment to the origin; if that distance is greater than
    ``earth_radius_m``, the chord does not intersect the solid Earth. Endpoints are assumed
    outside the Earth (orbit altitudes).
    """
    a = np.asarray(p0, dtype=float).reshape(3)
    b = np.asarray(p1, dtype=float).reshape(3)
    u = b - a
    un = float(np.dot(u, u))
    if un < 1e-18:
        return float(np.dot(a, a)) > earth_radius_m**2
    t = float(-np.dot(a, u) / un)
    t = max(0.0, min(1.0, t))
    c = a + t * u
    # Strict inequality: grazing tangency treated as not “clear” for a conservative plot.
    return float(np.dot(c, c)) > earth_radius_m**2 * (1.0 + 1e-12)


def _filter_segments_earth_los(segments, earth_radius_m=EARTH_RADIUS_M):
    """Keep only segments with geometric line-of-sight clear of the Earth sphere."""
    return [s for s in segments if earth_los_clear(s[0], s[1], earth_radius_m)]


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


def _segment_midpoint_depth(ax, seg):
    """Projected depth of segment midpoint (for draw order in mplot3d)."""
    p0 = np.asarray(seg[0], dtype=float)
    p1 = np.asarray(seg[1], dtype=float)
    m = 0.5 * (p0 + p1)
    _xs, _ys, dz = proj3d.proj_transform(m[0], m[1], m[2], ax.get_proj())
    return float(dz)


def _split_segments_depth(ax, segments):
    """Split into far (draw before Earth) vs near (draw after Earth) by median depth."""
    if not segments:
        return [], []
    depths = [_segment_midpoint_depth(ax, s) for s in segments]
    med = float(np.median(depths))
    back = [s for s, d in zip(segments, depths) if d <= med]
    front = [s for s, d in zip(segments, depths) if d > med]
    return back, front


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
    filter_earth_los,
):
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection="3d")

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

    if filter_earth_los:
        seg_leo = _filter_segments_earth_los(seg_leo, EARTH_RADIUS_M)
        seg_meo = _filter_segments_earth_los(seg_meo, EARTH_RADIUS_M)
        seg_cross = _filter_segments_earth_los(seg_cross, EARTH_RADIUS_M)

    ax.set_box_aspect((1, 1, 1))
    lim = float(np.max(np.sqrt(x * x + y * y + z * z)) * 1.12)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_zlim(-lim, lim)
    ax.view_init(elev=elev, azim=azim)

    def _add_lc(segments, color, lw, alpha):
        if not segments:
            return
        arr = np.array(segments, dtype=float)
        lc = Line3DCollection(arr, colors=color, linewidths=lw, alpha=alpha)
        ax.add_collection3d(lc)

    leo_b, leo_f = _split_segments_depth(ax, seg_leo)
    meo_b, meo_f = _split_segments_depth(ax, seg_meo)
    cross_b, cross_f = _split_segments_depth(ax, seg_cross)

    alpha_back_scale = 0.5
    _add_lc(leo_b, color_leo_isl, line_width_leo, alpha_leo_isl * alpha_back_scale)
    _add_lc(meo_b, color_meo, line_width_meo, alpha_meo_isl * alpha_back_scale)
    _add_lc(cross_b, color_cross, line_width_cross, alpha_cross * 0.55)

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
        zorder=1,
    )

    _add_lc(leo_f, color_leo_isl, line_width_leo, alpha_leo_isl)
    _add_lc(meo_f, color_meo, line_width_meo, alpha_meo_isl)
    _add_lc(cross_f, color_cross, line_width_cross, alpha_cross)

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

    ax.set_axis_off()
    if title:
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
        Line2D(
            [0],
            [0],
            color=color_cross,
            linewidth=2.2,
            label=(
                "Cross-layer ISL (Earth-cleared only)"
                if filter_earth_los
                else "Cross-layer ISL (topology)"
            ),
        ),
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
        "--link-mode",
        choices=("physical", "abstract"),
        default="physical",
        help="physical: omit ISLs whose straight segment intersects the Earth sphere (default). "
        "abstract: draw full topology regardless of Earth occlusion (label as non-physical).",
    )
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
    title = ""
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
        args.link_mode == "physical",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

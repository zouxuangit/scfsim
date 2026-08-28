"""Generate Fig. 1 of the manuscript (docs/fig1_architecture.{png,pdf}).

The figure was previously a hand-made artefact that could not be
regenerated from the repository; it also predated the verification
modules, so it showed eight modules while the package has twelve. This
script draws all twelve so that the figure, the README module table and
Section 2.1 of the manuscript agree, and so that a future change to the
package layout can be reflected by re-running it:

    python docs/gen_fig1.py

Dependency-free beyond matplotlib. The output size matches the earlier
figure so the manuscript layout is unaffected when the image is replaced.
"""
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

OUT = pathlib.Path(__file__).parent / "fig1_architecture"

BLUE, PEACH, GREEN = "#dce9f5", "#fde5d6", "#e4f2e4"
LILAC, SAND = "#efe3f2", "#fdf3d8"
EDGE = "#3a3a3a"


def box(ax, x, y, w, h, title, lines, colour, title_size=11.0,
        line_size=9.2, line_gap=0.018):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.006",
                                fc=colour, ec=EDGE, lw=1.1, zorder=1))
    cx = x + w / 2
    ty = y + h - 0.03
    ax.text(cx, ty, title, ha="center", va="top", fontsize=title_size,
            fontweight="bold", zorder=2)
    yy = ty - 0.052
    for line in lines:
        ax.text(cx, yy, line, ha="center", va="top", fontsize=line_size,
                zorder=2)
        yy -= line_gap + 0.026


def arrow(ax, p, q, label=None, lx=0.0, ly=0.0):
    ax.annotate("", xy=q, xytext=p,
                arrowprops=dict(arrowstyle="-|>", lw=1.3, color=EDGE,
                                shrinkA=0, shrinkB=0))
    if label:
        mx, my = (p[0] + q[0]) / 2 + lx, (p[1] + q[1]) / 2 + ly
        ax.text(mx, my, label, fontsize=9.3, style="italic", ha="center",
                va="center", zorder=3,
                bbox=dict(fc="white", ec="none", pad=0.4))


def main():
    fig, ax = plt.subplots(figsize=(11.0, 5.9), dpi=168)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.set_xlim(-0.01, 1.01)
    ax.set_ylim(-0.075, 0.975)
    ax.axis("off")

    # ---- left column: inputs
    box(ax, 0.015, 0.615, 0.235, 0.325, "scfsim.config",
        ["NetworkConfig · FirmConfig", "BankConfig · ShockConfig",
         "ScenarioConfig (blockchain)", "ChannelConfig (4 channels)"], BLUE)
    box(ax, 0.015, 0.235, 0.235, 0.325, "scfsim.network",
        ["layered generator:", "core / tiered firms / banks",
         "or user NetworkX graph", "+ validate_network()"], BLUE)

    # ---- centre: state + engine
    box(ax, 0.325, 0.815, 0.315, 0.13, "scfsim.agents",
        ["FirmState · BankState"], PEACH)
    box(ax, 0.325, 0.32, 0.315, 0.49, "scfsim.simulation",
        ["per-period loop:", "1 settlement (recovery)",
         "2 orders & deliveries", "3 production & liquidity",
         "4 receivables financing", "(visibility · haircut · fraud)",
         "5 default resolution", "run_batch(): Monte-Carlo"], GREEN)

    # ---- bottom centre: the verification stack (Section 2.3)
    box(ax, 0.27, 0.05, 0.425, 0.2, "verification stack (five layers)",
        ["benchmark: reachability bounds · ablation designs",
         "invariants: accounting identities  ·  economics: properties",
         "metamorphic: invariances  ·  reference: differential test"],
        SAND, title_size=10.4, line_size=8.4, line_gap=0.008)

    # ---- right column: outputs and experiment drivers
    box(ax, 0.715, 0.66, 0.27, 0.28, "scfsim.metrics",
        ["RunResult time series", "cascade & tier summaries",
         "batch_summary()"], LILAC)
    box(ax, 0.715, 0.37, 0.27, 0.235, "scfsim.sweep",
        ["sweep() sensitivity", "ablation() experiments"], SAND)
    box(ax, 0.715, 0.09, 0.27, 0.225, "scfsim.viz",
        ["scenario comparison ·", "sensitivity · ablation"], LILAC)

    # ---- data flow
    arrow(ax, (0.25, 0.79), (0.325, 0.72), "scenario", lx=0.0, ly=0.035)
    arrow(ax, (0.25, 0.42), (0.325, 0.49), "graph", lx=0.0, ly=-0.035)
    ax.annotate("", xy=(0.4825, 0.812), xytext=(0.4825, 0.79),
                arrowprops=dict(arrowstyle="-|>", lw=1.3, color=EDGE))
    arrow(ax, (0.64, 0.7), (0.715, 0.76), "results", lx=0.0, ly=0.035)
    arrow(ax, (0.715, 0.49), (0.64, 0.49), "configs", lx=0.0, ly=0.035)
    arrow(ax, (0.85, 0.66), (0.85, 0.607))
    arrow(ax, (0.85, 0.37), (0.85, 0.317))
    arrow(ax, (0.4825, 0.32), (0.4825, 0.257), "verify", lx=0.05, ly=0.0)

    ax.text(0.5, -0.045,
            "every config JSON-serialisable  ·  every run seed-reproducible",
            ha="center", va="center", fontsize=9.4, color="#444444")

    for ext in ("png", "pdf"):
        fig.savefig(f"{OUT}.{ext}", dpi=168)
    print(f"wrote {OUT}.png / .pdf")


if __name__ == "__main__":
    main()

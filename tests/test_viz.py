"""Smoke tests for the plotting helpers.

These do not assert on pixels; they check that each helper builds a figure
from real result objects without raising, that composing panels via an
existing axis works, and that SCFSim never overrides the matplotlib
backend of the importing session.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from scfsim import (ScenarioConfig, SimulationConfig, ablation,  # noqa: E402
                    isolated_channel_configs, leave_one_out_configs,
                    plot_channel_ablation, plot_channel_contributions,
                    plot_scenario_comparison, plot_sensitivity, run_batch,
                    sweep)


def small(blockchain=False):
    cfg = SimulationConfig(n_periods=8, seed=2)
    cfg.network.n_tiers = 2
    cfg.network.firms_per_tier = (4, 6)
    cfg.network.seed = 2
    cfg.shock.seed_defaults = 1
    cfg.scenario = ScenarioConfig(blockchain=blockchain)
    return cfg


def test_scenario_comparison_builds_figure(tmp_path):
    batches = {
        "Traditional": run_batch(small(False), n_runs=4, base_seed=1),
        "Blockchain": run_batch(small(True), n_runs=4, base_seed=1),
    }
    out = tmp_path / "cmp.png"
    fig = plot_scenario_comparison(batches, save=str(out))
    assert len(fig.axes) == 2
    assert out.exists() and out.stat().st_size > 0
    plt.close(fig)


def test_sensitivity_accepts_existing_axis():
    rows = sweep(small(True), "scenario.bc_haircut", [0.05, 0.4],
                 n_runs=3, base_seed=1)
    fig, ax = plt.subplots()
    returned = plot_sensitivity({"Blockchain": rows}, xlabel="haircut",
                                baseline={"Traditional": 0.5}, ax=ax)
    assert returned is ax
    assert ax.get_xlabel() == "haircut"
    plt.close(fig)


def test_channel_plots_build():
    iso = ablation(isolated_channel_configs(small()), n_runs=3, base_seed=1)
    loo = ablation(leave_one_out_configs(small()), n_runs=3, base_seed=1)
    fig, axes = plt.subplots(1, 2)
    plot_channel_ablation(iso, order=["none", "all"], ax=axes[0])
    plot_channel_contributions(iso, loo, ax=axes[1])
    assert len(axes[1].patches) == 8      # 4 channels x 2 ablation designs
    plt.close(fig)


def test_importing_scfsim_does_not_override_backend():
    import importlib

    import scfsim.viz
    before = matplotlib.get_backend()
    importlib.reload(scfsim.viz)
    assert matplotlib.get_backend() == before

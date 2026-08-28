"""Minimal reproducible example: does blockchain-enabled deep-tier
financing dampen default cascades?

Runs two Monte-Carlo batches on identical networks and shock paths --
scenario A (traditional SCF, visibility depth 1) vs. scenario B
(blockchain-enabled, deep visibility, low haircut/fraud) -- and produces
the standard comparison figure plus a console summary. The comparison is
then repeated with suppliers paid on the same one-period terms as their
customers instead of on delivery (``firm.payables_delay = 1``), which is
the right-hand half of Table 5 in the paper: the working-capital gap that
receivables financing bridges closes, and the two scenarios nearly
converge in mean default share.

Run from the repository root:

    python examples/blockchain_switch.py

The configuration lives in :func:`stressed_base` so that
``tests/test_manuscript.py`` can pin the numbers quoted in the paper to
exactly the scenario this script runs.
"""
from scfsim import (ScenarioConfig, SimulationConfig, batch_summary,
                    plot_scenario_comparison, run_batch)

N_RUNS = 200
BASE_SEED = 42


def stressed_base(n_periods: int = 40) -> SimulationConfig:
    """A stressed environment in which the liquidity backstop actually binds:
    thin cash buffers, low recovery on defaulted buyers, frequent
    idiosyncratic liquidity shocks and volatile core demand."""
    base = SimulationConfig(n_periods=n_periods)
    base.firm.initial_cash_ratio = 0.15
    base.firm.receivable_recovery = 0.15
    base.shock.liquidity_shock_prob = 0.10
    base.shock.liquidity_shock_size = 0.6
    base.shock.demand_sigma = 0.18
    base.shock.seed_defaults = 3   # three seed defaults in tier 2 at t=2
    base.shock.seed_tier = 2
    return base


def scenario_configs(payables_delay: int = 0):
    """The two scenarios of the headline comparison (Table 5).

    ``payables_delay=0`` is the paper's default: suppliers are paid on
    delivery while their customers pay one period later. ``1`` gives the
    symmetric-terms columns of Table 5.
    """
    base = stressed_base()
    base.firm.payables_delay = payables_delay
    cfg_traditional = SimulationConfig.from_json(base.to_json())
    cfg_traditional.scenario = ScenarioConfig(blockchain=False)
    cfg_blockchain = SimulationConfig.from_json(base.to_json())
    cfg_blockchain.scenario = ScenarioConfig(blockchain=True)
    return cfg_traditional, cfg_blockchain


def main():
    print(f"Running {N_RUNS} Monte-Carlo paths per scenario ...")
    batches = {}
    for delay, terms in ((0, "payables on delivery"),
                         (1, "payables on one-period terms")):
        cfg_traditional, cfg_blockchain = scenario_configs(delay)
        batch_a = run_batch(cfg_traditional, n_runs=N_RUNS, base_seed=BASE_SEED)
        batch_b = run_batch(cfg_blockchain, n_runs=N_RUNS, base_seed=BASE_SEED)
        batches[delay] = (batch_a, batch_b)
        for label, batch in [("Traditional SCF", batch_a),
                             ("Blockchain-enabled SCF", batch_b)]:
            s = batch_summary(batch)
            print(f"\n{label} ({terms})")
            for k, v in s.items():
                print(f"  {k:>24}: {v:.4f}" if isinstance(v, float) else
                      f"  {k:>24}: {v}")

    batch_a, batch_b = batches[0]
    fig = plot_scenario_comparison(
        {"Traditional SCF": batch_a, "Blockchain-enabled SCF": batch_b})
    for ext in ("pdf", "png"):
        fig.savefig(f"example_output.{ext}", dpi=200, bbox_inches="tight")
    print("\nFigure written to example_output.pdf / .png")


if __name__ == "__main__":
    main()

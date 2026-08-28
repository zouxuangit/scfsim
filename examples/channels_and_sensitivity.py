"""Validation and sensitivity experiment.

Three questions that earlier audits of SCFSim left unanswered:

1. *Are the contagion channels doing separable work?* -- answered by two
   complementary ablations: each channel acting alone (first-order effect)
   and each channel removed from the fully coupled model (marginal effect).
   Channels whose two measurements disagree are interacting rather than
   adding up, and the gap between the coupled effect and the sum of the
   first-order effects quantifies that interaction.

2. *Does the benefit of blockchain-enabled deep-tier financing survive an
   imperfect platform?* -- answered by sweeping the three financing
   frictions against the traditional-SCF baseline.

3. *Under what conditions does the bank credit-crunch channel bind?* -- it
   is second order in supply chain finance because receivables lending is
   self-liquidating and capped by eligible collateral, so it is measured
   here against bank capitalisation rather than assumed to matter.

4. *Do the results survive the assumptions the default configuration
   makes?* -- suppliers paid on delivery while paying their own suppliers
   on terms (the widest working-capital gap), banks that never price
   risk, and a core enterprise that never defaults. Each is switched
   on here (``firm.payables_delay``, ``bank.pricing_slope``,
   ``shock.core_default_time``) and the headline comparison is re-run.

Usage:

    python examples/channels_and_sensitivity.py            # full run
    python examples/channels_and_sensitivity.py --quick    # fast preview
    python examples/channels_and_sensitivity.py --jobs 4   # parallel paths

"""
import argparse
import copy

import matplotlib.pyplot as plt
import numpy as np

from scfsim import (ScenarioConfig, SimulationConfig, ablation, batch_summary,
                    channel_decomposition, isolated_channel_configs,
                    leave_one_out_configs, plot_channel_contributions,
                    plot_sensitivity, run_batch, sweep)

N_RUNS_FULL, N_RUNS_QUICK = 100, 15
RATES_FULL = [0.0, 0.05, 0.1, 0.2, 0.35, 0.5, 0.65]
RATES_QUICK = [0.0, 0.2, 0.5]
CAPITAL_FULL = [0.20, 0.12, 0.06, 0.03, 0.015]
CAPITAL_QUICK = [0.12, 0.015]
SLOPES_FULL = [0.0, 0.1, 0.2, 0.4]
SLOPES_QUICK = [0.0, 0.4]
PAYABLES_FULL = [0, 1, 2]
PAYABLES_QUICK = [0, 1]
BASE_SEED = 42
CHANNELS = ("counterparty", "supply", "demand", "credit_crunch")


def stressed_base(n_periods: int = 40, strict: bool = True) -> SimulationConfig:
    """The same stressed environment as ``blockchain_switch.py``.

    Strict mode checks the accounting identities and the economic
    properties after every period. It costs about a quarter of runtime and is
    the setting to use whenever you have modified the model. The
    configuration is a function so that ``tests/test_manuscript.py`` can
    pin the numbers quoted in the paper to exactly this scenario.
    """
    base = SimulationConfig(n_periods=n_periods, strict=strict)
    base.firm.initial_cash_ratio = 0.15
    base.firm.receivable_recovery = 0.15
    base.shock.liquidity_shock_prob = 0.10
    base.shock.liquidity_shock_size = 0.6
    base.shock.demand_sigma = 0.18
    base.shock.seed_defaults = 3
    base.shock.seed_tier = 2
    return base


def decompose_channels(base, n_runs=N_RUNS_FULL, base_seed=BASE_SEED,
                       n_jobs=1):
    """Both ablation designs and their decomposition (panel (a))."""
    iso = ablation(isolated_channel_configs(base), n_runs=n_runs,
                   base_seed=base_seed, n_jobs=n_jobs)
    loo = ablation(leave_one_out_configs(base), n_runs=n_runs,
                   base_seed=base_seed, n_jobs=n_jobs)
    return iso, loo, channel_decomposition(iso, loo, channels=CHANNELS)


def relaxed_limitations(base, slopes=SLOPES_FULL, payables=PAYABLES_FULL,
                        n_runs=N_RUNS_FULL, base_seed=BASE_SEED, n_jobs=1):
    """Headline comparison with payables on terms, risk-based pricing and an
    anchor default.

    Returns ``{"payables": [{"delay", "traditional", "blockchain"}, ...],
    "pricing": [{"slope", "traditional", "blockchain"}, ...],
    "anchor": {"traditional", "blockchain"}}`` where each scenario entry is
    the batch summary. The anchor-default case replaces the three tier-2
    seeds with a default of the core enterprise itself at the same period,
    so it is the other kind of shock, not an additional one.
    """
    out = {"payables": [], "pricing": [], "anchor": {}}
    for delay in payables:
        row = {"delay": delay}
        for label, bc in (("traditional", False), ("blockchain", True)):
            cfg = copy.deepcopy(base)
            cfg.scenario = ScenarioConfig(blockchain=bc)
            cfg.firm.payables_delay = delay
            row[label] = batch_summary(run_batch(cfg, n_runs=n_runs,
                                                 base_seed=base_seed,
                                                 n_jobs=n_jobs))
        out["payables"].append(row)
    for slope in slopes:
        row = {"slope": slope}
        for label, bc in (("traditional", False), ("blockchain", True)):
            cfg = copy.deepcopy(base)
            cfg.scenario = ScenarioConfig(blockchain=bc)
            cfg.bank.pricing_slope = slope
            row[label] = batch_summary(run_batch(cfg, n_runs=n_runs,
                                                 base_seed=base_seed,
                                                 n_jobs=n_jobs))
        out["pricing"].append(row)
    for label, bc in (("traditional", False), ("blockchain", True)):
        cfg = copy.deepcopy(base)
        cfg.scenario = ScenarioConfig(blockchain=bc)
        cfg.shock.seed_defaults = 0
        cfg.shock.core_default_time = cfg.shock.seed_time
        runs = run_batch(cfg, n_runs=n_runs, base_seed=base_seed,
                         n_jobs=n_jobs)
        summary = batch_summary(runs)
        # the anchor is the chain's only customer, so every firm eventually
        # fails; what differs between scenarios is how fast, and how much
        # bank exposure is caught on the way down
        summary["default_share_at_10"] = float(
            np.mean([r.default_share[10] for r in runs]))
        out["anchor"][label] = summary
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true",
                        help="fewer Monte-Carlo paths and a coarser grid "
                             "(seconds instead of minutes)")
    parser.add_argument("--jobs", type=int, default=1,
                        help="worker processes for Monte-Carlo paths "
                             "(0 = all cores); results are identical")
    args = parser.parse_args()
    JOBS = args.jobs

    N_RUNS = N_RUNS_QUICK if args.quick else N_RUNS_FULL
    RATES = RATES_QUICK if args.quick else RATES_FULL
    CAPITAL = CAPITAL_QUICK if args.quick else CAPITAL_FULL
    base = stressed_base()

    # ------------------------------------------------------------ ablation
    print(f"Channel ablation ({N_RUNS} paths per variant) ...")
    iso, loo, dec = decompose_channels(base, n_runs=N_RUNS, n_jobs=JOBS)
    print(f"  no channel active : {dec['baseline_no_channels']:5.2f}")
    print(f"  all channels      : {dec['coupled']:5.2f}")
    print(f"  {'channel':>14} {'alone':>8} {'marginal':>10}")
    for c in CHANNELS:
        v = dec["channels"][c]
        print(f"  {c:>14} {v['alone']:+8.2f} {v['marginal']:+10.2f}")
    print(f"  sum of first-order effects : {dec['sum_of_first_order']:+.2f}")
    print(f"  effect of the coupled model: {dec['coupled_effect']:+.2f}")
    print(f"  interaction term           : {dec['interaction']:+.2f}"
          "   (negative = channels overlap)")

    # ------------------------------------------------- financing frictions
    print("\nFriction sensitivity ...")
    cfg_trad = copy.deepcopy(base)
    cfg_trad.scenario = ScenarioConfig(blockchain=False)
    trad = batch_summary(run_batch(cfg_trad, n_runs=N_RUNS, base_seed=BASE_SEED,
                                   n_jobs=JOBS))
    print(f"  traditional-SCF baseline = {trad['mean_default_share']:.3f}")

    cfg_bc = copy.deepcopy(base)
    cfg_bc.scenario = ScenarioConfig(blockchain=True)
    haircut = sweep(cfg_bc, "scenario.bc_haircut", RATES, n_runs=N_RUNS,
                    base_seed=BASE_SEED, n_jobs=JOBS)
    fraud = sweep(cfg_bc, "scenario.bc_fraud_prob", RATES, n_runs=N_RUNS,
                  base_seed=BASE_SEED, n_jobs=JOBS)
    depth = sweep(cfg_bc, "scenario.bc_visibility_depth", [1, 2, 3],
                  n_runs=N_RUNS, base_seed=BASE_SEED, n_jobs=JOBS)
    for name, rows in (("haircut", haircut), ("fraud", fraud), ("depth", depth)):
        pts = ", ".join(f"{r['value']}->{r['mean_default_share']:.3f}"
                        for r in rows)
        print(f"  {name:>8}: {pts}")

    # --------------------------------------------- credit-crunch binding
    print("\nWhen does the credit-crunch channel bind? ...")
    capital_rows = []
    for cap in CAPITAL:
        cfg = copy.deepcopy(base)
        cfg.bank.capital_ratio = cap
        sub = ablation({k: v for k, v in leave_one_out_configs(cfg).items()
                        if k in ("all", "without_credit_crunch")},
                       n_runs=N_RUNS, base_seed=BASE_SEED, n_jobs=JOBS)
        marginal = (sub["all"]["mean_cascade_size"]
                    - sub["without_credit_crunch"]["mean_cascade_size"])
        capital_rows.append({"value": cap, "marginal": marginal})
        print(f"  bank capital ratio {cap:>6}: marginal contribution "
              f"{marginal:+.2f} firms")

    # ----------------------------------------- relaxing two limitations
    print("\nRelaxing the default configuration's assumptions ...")
    relaxed = relaxed_limitations(base, slopes=SLOPES_QUICK if args.quick
                                  else SLOPES_FULL,
                                  payables=PAYABLES_QUICK if args.quick
                                  else PAYABLES_FULL, n_runs=N_RUNS,
                                  n_jobs=JOBS)
    print(f"  {'payables delay':>14} {'traditional':>12} {'blockchain':>11} "
          f"{'gap':>7}   credit drawn   systemic events")
    for row in relaxed["payables"]:
        a, b = row["traditional"], row["blockchain"]
        print(f"  {row['delay']:>14} {a['mean_default_share']:>12.3f} "
              f"{b['mean_default_share']:>11.3f} "
              f"{a['mean_default_share'] - b['mean_default_share']:>+7.3f}   "
              f"{a['mean_credit_extended']:>5.1f} / {b['mean_credit_extended']:<5.1f}  "
              f"{a['systemic_event_freq']:.2f} / {b['systemic_event_freq']:.2f}")
    print(f"  {'pricing slope':>14} {'traditional':>12} {'blockchain':>11} "
          f"{'gap':>7}   (mean default share)")
    for row in relaxed["pricing"]:
        a, b = (row["traditional"]["mean_default_share"],
                row["blockchain"]["mean_default_share"])
        print(f"  {row['slope']:>14} {a:>12.3f} {b:>11.3f} {a - b:>+7.3f}")
    a, b = relaxed["anchor"]["traditional"], relaxed["anchor"]["blockchain"]
    print(f"  anchor default at t={base.shock.seed_time} instead of tier-2 seeds:")
    for label, s_ in (("traditional", a), ("blockchain", b)):
        print(f"  {label:>14}: default share {s_['default_share_at_10']:.2f} "
              f"at t=10, {s_['mean_default_share']:.2f} at the end; "
              f"credit {s_['mean_credit_extended']:.1f}, "
              f"bank losses {s_['mean_bank_losses']:.2f}")

    # ------------------------------------------------------------------ figure
    fig, axes = plt.subplots(1, 4, figsize=(17.4, 3.9))
    plot_channel_contributions(iso, loo, channels=CHANNELS, ax=axes[0])
    axes[0].set_title("(a) Contribution of each channel", fontsize=10)

    plot_sensitivity({"Verification haircut": haircut,
                      "Residual fraud rate": fraud},
                     xlabel="Friction level",
                     baseline={"Traditional SCF": trad["mean_default_share"]},
                     ax=axes[1])
    axes[1].set_title("(b) Sensitivity to platform quality", fontsize=10)

    axes[2].bar([str(r["value"]) for r in depth],
                [r["mean_default_share"] for r in depth], color="#4c78a8",
                width=0.55)
    axes[2].axhline(trad["mean_default_share"], ls="--", lw=1.4, color="0.35")
    axes[2].text(-0.4, trad["mean_default_share"], "Traditional SCF", va="bottom",
                 ha="left", fontsize=8, color="0.35")
    for i, r in enumerate(depth):
        axes[2].text(i, r["mean_default_share"], f"{r['mean_default_share']:.2f}",
                     ha="center", va="bottom", fontsize=8.5)
    axes[2].set_ylim(0, 0.66)
    axes[2].set_xlabel("Financing visibility depth (tiers)")
    axes[2].set_ylabel("mean default share")
    axes[2].set_title("(c) Sensitivity to reach", fontsize=10)

    axes[3].plot([r["value"] for r in capital_rows],
                 [r["marginal"] for r in capital_rows], marker="o", ms=4,
                 lw=1.8, color="#e45756")
    axes[3].invert_xaxis()
    axes[3].set_xlabel("Bank capital / SCF credit book")
    axes[3].set_ylabel("marginal contribution (firms)")
    axes[3].set_title("(d) When the credit crunch binds", fontsize=10)

    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(f"channels_and_sensitivity.{ext}", dpi=200,
                    bbox_inches="tight")
    print("\nFigure written to channels_and_sensitivity.pdf / .png")


if __name__ == "__main__":
    main()

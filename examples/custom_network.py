"""Bringing your own supply network.

The paper's reuse claim is that ``validate_network`` is the extension
point for an empirically mapped supply network. This script is that claim
made runnable: a small mapped chain is written down as an edge list,
turned into a compliant network, checked, and put through the same
scenario comparison as the paper's synthetic network. Every path of the
Monte-Carlo batch runs on the *same* topology; only the shocks vary.

Run from the repository root:

    python examples/custom_network.py

The mapped chain below is illustrative. A real one would come from
invoice data, a supplier-mapping exercise or customs records: one row per
supplier-buyer relationship with the share of the buyer's purchases it
represents. Shares must sum to one per buyer; tiers are inferred from the
graph; house banks are assigned round-robin here but can be given per firm.
"""
from scfsim import (ScenarioConfig, SimulationConfig, batch_summary,
                    demand_reachable_set, network_from_edges, run_batch,
                    supply_reachable_set)

N_RUNS = 100
BASE_SEED = 7

#: (supplier, buyer, share of the buyer's inputs sourced from the supplier)
EDGES = [
    ("Alpha Castings", "Acme Motors", 0.35),
    ("Beta Electronics", "Acme Motors", 0.40),
    ("Gamma Interiors", "Acme Motors", 0.25),
    ("Delta Steel", "Alpha Castings", 0.60),
    ("Epsilon Alloys", "Alpha Castings", 0.25),
    ("Lambda Scrap", "Alpha Castings", 0.15),   # also a tier-1 supplier
    ("Zeta Chips", "Beta Electronics", 0.55),
    ("Eta Boards", "Beta Electronics", 0.45),
    ("Theta Textiles", "Gamma Interiors", 0.60),
    ("Iota Foams", "Gamma Interiors", 0.40),
    ("Kappa Ore", "Delta Steel", 1.00),
    ("Kappa Ore", "Epsilon Alloys", 0.50),
    ("Lambda Scrap", "Epsilon Alloys", 0.50),
    ("Mu Wafers", "Zeta Chips", 1.00),
    ("Mu Wafers", "Eta Boards", 0.40),
    ("Nu Resins", "Eta Boards", 0.60),
    ("Nu Resins", "Iota Foams", 1.00),
    ("Xi Fibres", "Theta Textiles", 1.00),
]


def mapped_network():
    """The chain above as a validated network. Kappa Ore, Mu Wafers and Nu
    Resins each sell to two buyers; Lambda Scrap sells both to a tier-1 and
    to a tier-2 buyer, and the inferred tiers place it above the deeper of
    the two (tier 3), which is what tier-by-tier order propagation needs."""
    return network_from_edges(EDGES, core="Acme Motors", banks=2)


def stressed_config(n_periods=40):
    cfg = SimulationConfig(n_periods=n_periods)
    cfg.firm.initial_cash_ratio = 0.15
    cfg.firm.receivable_recovery = 0.15
    cfg.shock.liquidity_shock_prob = 0.10
    cfg.shock.liquidity_shock_size = 0.6
    cfg.shock.demand_sigma = 0.18
    cfg.shock.seed_defaults = 0
    cfg.shock.seed_firms = ("Delta Steel",)     # a named tier-2 failure
    cfg.shock.seed_time = 2
    return cfg


def main():
    g = mapped_network()
    firms = [n for n in g if g.nodes[n]["kind"] == "firm"]
    tiers = {n: g.nodes[n]["tier"] for n in firms}
    print(f"{len(firms)} firms in {max(tiers.values())} tiers, "
          f"core enterprise {[n for n in g if g.nodes[n]['kind'] == 'core'][0]!r}")
    for t in range(1, max(tiers.values()) + 1):
        print(f"  tier {t}: " + ", ".join(sorted(n for n in firms if tiers[n] == t)))

    # what a Delta Steel failure can reach, before running anything
    seed = "Delta Steel"
    print(f"\nA {seed!r} default can reach, through lost supply: "
          f"{sorted(supply_reachable_set(g, [seed]) - {seed}) or 'nobody'}")
    print(f"... and through lost demand: "
          f"{sorted(demand_reachable_set(g, [seed]) - {seed}) or 'nobody'}")

    base = stressed_config()
    print(f"\nRunning {N_RUNS} shock paths per scenario on the fixed network ...")
    for label, bc in (("Traditional SCF", False), ("Blockchain-enabled SCF", True)):
        cfg = SimulationConfig.from_json(base.to_json())
        cfg.scenario = ScenarioConfig(blockchain=bc)
        runs = run_batch(cfg, n_runs=N_RUNS, base_seed=BASE_SEED, network=g)
        s = batch_summary(runs)
        hit = {}
        for r in runs:
            for n in r.defaulted_firms:
                hit[n] = hit.get(n, 0) + 1
        worst = sorted(hit.items(), key=lambda kv: -kv[1])[:3]
        print(f"\n{label}")
        print(f"  mean default share {s['mean_default_share']:.3f}, "
              f"systemic events {s['systemic_event_freq']:.2f}, "
              f"credit drawn {s['mean_credit_extended']:.1f}, "
              f"bank losses {s['mean_bank_losses']:.2f}")
        print("  most often defaulted: " + ", ".join(
            f"{n} ({c / N_RUNS:.0%})" for n, c in worst))


if __name__ == "__main__":
    main()

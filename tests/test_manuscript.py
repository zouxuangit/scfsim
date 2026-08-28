"""The numbers quoted in the manuscript reproduce from the shipped scripts.

Every previous audit of this project ended with the same instruction to
the authors: run both example scripts and confirm that every number in the
paper reproduces exactly from the stated seeds. That is a manual step that
has to be repeated after every change to the code or the text, and a
manual step that is repeated eight times is one that will eventually be
skipped. These tests make it part of the suite.

They are *not* a verification of the model — a wrong model reproduces its
wrong numbers perfectly well. They verify that the manuscript and the code
have not drifted apart: if a refactor changes a reported figure, or an
edit to the paper misquotes one, this file fails.

The expected values are the ones printed in the manuscript, to the
precision at which they are printed there; the scenarios are imported
from the example scripts rather than re-typed, so the test cannot pass on
a different configuration from the one the paper describes.
"""
import importlib.util
import pathlib

import pytest

from scfsim import batch_summary, run_batch

EXAMPLES = pathlib.Path(__file__).resolve().parent.parent / "examples"


def load_example(name):
    spec = importlib.util.spec_from_file_location(name, EXAMPLES / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.slow
def test_table_5_reproduces_from_blockchain_switch():
    """Table 5 and the text of Section 3, first example (~30 s)."""
    ex = load_example("blockchain_switch")
    cfg_trad, cfg_bc = ex.scenario_configs()
    trad = batch_summary(run_batch(cfg_trad, n_runs=ex.N_RUNS,
                                   base_seed=ex.BASE_SEED))
    bc = batch_summary(run_batch(cfg_bc, n_runs=ex.N_RUNS,
                                 base_seed=ex.BASE_SEED))

    # Table 5, row by row, at the precision printed in the paper
    assert round(100 * trad["mean_default_share"], 1) == 55.6
    assert round(100 * bc["mean_default_share"], 1) == 26.5
    assert round(trad["mean_cascade_size"], 1) == 28.1
    assert round(bc["mean_cascade_size"], 1) == 11.9
    assert round(100 * trad["systemic_event_freq"], 1) == 98.0
    assert round(100 * bc["systemic_event_freq"], 1) == 47.5

    # the prose below Table 5: "credit extended rises two and a half times
    # (9.7 to 24.8) and cumulative bank losses rise as well (2.29 to 2.59)"
    assert round(trad["mean_credit_extended"], 1) == 9.7
    assert round(bc["mean_credit_extended"], 1) == 24.8
    assert round(trad["mean_bank_losses"], 2) == 2.29
    assert round(bc["mean_bank_losses"], 2) == 2.59

    # and: "more than halves the mean cascade and the frequency of
    # systemic events"
    assert bc["mean_cascade_size"] < 0.5 * trad["mean_cascade_size"]
    assert bc["systemic_event_freq"] < 0.5 * trad["systemic_event_freq"]
    assert 2.4 < bc["mean_credit_extended"] / trad["mean_credit_extended"] < 2.6
    assert bc["mean_bank_losses"] > trad["mean_bank_losses"]

    # Table 5, right-hand columns: suppliers paid on one-period terms
    cfg_trad, cfg_bc = ex.scenario_configs(payables_delay=1)
    trad1 = batch_summary(run_batch(cfg_trad, n_runs=ex.N_RUNS,
                                    base_seed=ex.BASE_SEED))
    bc1 = batch_summary(run_batch(cfg_bc, n_runs=ex.N_RUNS,
                                  base_seed=ex.BASE_SEED))
    assert round(100 * trad1["mean_default_share"], 1) == 25.1
    assert round(100 * bc1["mean_default_share"], 1) == 23.5
    assert round(trad1["mean_cascade_size"], 1) == 11.1
    assert round(bc1["mean_cascade_size"], 1) == 10.2
    assert round(100 * trad1["systemic_event_freq"], 1) == 39.5
    assert round(100 * bc1["systemic_event_freq"], 1) == 25.5
    # the prose: "the traditional-SCF default share falls from 55.6% to
    # 25.1%, credit drawn falls by five sixths, and the gap between the
    # scenarios shrinks from 29 to 2 points, although deep-tier financing
    # still cuts the frequency of systemic events by a third"
    assert 0.14 < trad1["mean_credit_extended"] / trad["mean_credit_extended"] < 0.19
    gap0 = trad["mean_default_share"] - bc["mean_default_share"]
    gap1 = trad1["mean_default_share"] - bc1["mean_default_share"]
    assert round(100 * gap0) == 29 and round(100 * gap1) == 2
    assert 0.30 < 1 - bc1["systemic_event_freq"] / trad1["systemic_event_freq"] < 0.40


@pytest.mark.slow
def test_channel_decomposition_reproduces_from_channels_and_sensitivity():
    """Fig. 3(a) and the text of Section 3, second example (~1 min)."""
    ex = load_example("channels_and_sensitivity")
    _, _, dec = ex.decompose_channels(ex.stressed_base(strict=False))
    ch = dec["channels"]

    # "Acting alone, counterparty losses add 11.9 firms to the cascade,
    # demand contraction 7.8, supply disruption 1.9 and the credit crunch
    # essentially nothing."
    assert round(ch["counterparty"]["alone"], 1) == 11.9
    assert round(ch["demand"]["alone"], 1) == 7.8
    assert round(ch["supply"]["alone"], 1) == 1.9
    assert abs(ch["credit_crunch"]["alone"]) < 0.05

    # "Removed from the fully coupled model, however, supply disruption is
    # the largest contributor at 8.2 firms, counterparty losses fall to
    # 6.2 and demand contraction to 3.6."
    assert round(ch["supply"]["marginal"], 1) == 8.2
    assert round(ch["counterparty"]["marginal"], 1) == 6.2
    assert round(ch["demand"]["marginal"], 1) == 3.6
    assert ch["supply"]["marginal"] > ch["counterparty"]["marginal"]

    # "the coupled effect of 20.6 firms is 1.1 firms smaller than the sum
    # of the first-order effects"
    assert round(dec["coupled_effect"], 1) == 20.6
    assert round(-dec["interaction"], 1) == 1.1


@pytest.mark.slow
def test_relaxed_limitations_reproduce_from_channels_and_sensitivity():
    """Section 3, final paragraph: the three switched-off assumptions (~40 s)."""
    ex = load_example("channels_and_sensitivity")
    relaxed = ex.relaxed_limitations(ex.stressed_base(strict=False),
                                     slopes=[0.0, 0.4], payables=[0, 1])
    # the 100-path payables block must agree with Table 5's 200-path
    # right-hand columns to the precision the sentence relies on
    now, terms = relaxed["payables"]
    gap_now = now["traditional"]["mean_default_share"] - now["blockchain"]["mean_default_share"]
    gap_terms = terms["traditional"]["mean_default_share"] - terms["blockchain"]["mean_default_share"]
    assert round(100 * gap_now) == 29 and round(100 * gap_terms) == 2
    flat, steep = relaxed["pricing"]
    # "moves the mean default share by less than one point in either
    # scenario"
    for scenario in ("traditional", "blockchain"):
        delta = (steep[scenario]["mean_default_share"]
                 - flat[scenario]["mean_default_share"])
        assert abs(delta) < 0.01, (scenario, delta)
    # "deep-tier financing cuts the share defaulted by period 10 from 0.33
    # to 0.18 and ... leaves banks with about a sixth of the losses (0.12
    # against 0.74)"
    trad, bc = relaxed["anchor"]["traditional"], relaxed["anchor"]["blockchain"]
    assert round(trad["default_share_at_10"], 2) == 0.33
    assert round(bc["default_share_at_10"], 2) == 0.18
    assert round(trad["mean_bank_losses"], 2) == 0.74
    assert round(bc["mean_bank_losses"], 2) == 0.12
    # "ends the chain in both scenarios"
    assert trad["mean_default_share"] == bc["mean_default_share"] == 1.0

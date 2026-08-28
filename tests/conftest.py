"""Shared pytest configuration.

The comparative-statics layer is the most expensive part of the suite
because each prediction needs two matched Monte-Carlo batches. Its cost is
tunable from the command line so that it can be thinned on a slow runner
without editing test code:

    pytest tests/ --statics-runs=8      # quick sanity pass
    pytest tests/ --statics-runs=100    # a stricter nightly run

The differential and metamorphic layers are parameterised over many
credit-layer settings, chain lengths and magnitudes. Those extra cases are
tagged ``extra_case`` and can be thinned on a constrained runner:

    pytest tests/ --sample-parameterisations
"""


def pytest_addoption(parser):
    parser.addoption(
        "--sample-parameterisations", action="store_true",
        help="run only the first parameterisation of the heavily "
             "parameterised differential and metamorphic tests, for a fast "
             "pass on a constrained runner.")
    parser.addoption(
        "--statics-runs", action="store", default=24, type=int,
        help="Monte-Carlo paths per point in the comparative-statics tests "
             "(default 24). Lower values run faster but tolerate more "
             "sampling noise.")


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: randomised property tests and large ablations")
    config.addinivalue_line(
        "markers", "extra_case: an additional parameterisation, skipped "
                   "under --sample-parameterisations")


def pytest_collection_modifyitems(config, items):
    """Thin the parameterised layers when sampling is requested."""
    if not config.getoption("--sample-parameterisations"):
        return
    import pytest
    skip = pytest.mark.skip(reason="thinned by --sample-parameterisations")
    for item in items:
        if "extra_case" in item.keywords:
            item.add_marker(skip)

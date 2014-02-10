import pytest


def pytest_addoption(parser):
    parser.addoption("-L", "--live", action="store_true", default=False,
                     help="Run live StarCluster tests on a real AWS account")
    parser.addoption("-C", "--coverage", action="store_true", default=False,
                     help="Produce a coverage report for StarCluster")


def pytest_runtest_setup(item):
    if 'live' in item.keywords and not item.config.getoption("--live"):
        pytest.skip("pass --live option to run")


def pytest_configure(config):
    config.option.exitfirst = True
    config.option.verbose = True
    config.option.capture = 'no'
    if config.getoption("--coverage"):
        config.option.cov_source = ['starcluster']
        config.option.cov_report = ['term-missing']

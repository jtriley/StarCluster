import pytest


def pytest_addoption(parser):
    parser.addoption("-L", "--live", action="store_true", default=False,
                     help="Run live StarCluster tests on a real AWS account")


def pytest_runtest_setup(item):
    if 'live' in item.keywords and not item.config.getoption("--live"):
        pytest.skip("pass --live option to run")


def pytest_configure(config):
    config.option.exitfirst = True
    config.option.verbose = True
    config.option.capture = 'no'

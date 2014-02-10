import pytest

live = pytest.mark.live


@live
def test_flat_rate_cluster():
    pass


@live
def test_spot_cluster():
    pass


@live
def test_vpc_flat_rate_cluster():
    pass


@live
def test_vpc_spot_cluster():
    pass

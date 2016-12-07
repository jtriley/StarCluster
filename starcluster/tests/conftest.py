# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import pytest
try:
    from pytest_cov.plugin import CovPlugin
except:
    from pytest_cov import CovPlugin

from starcluster import static
from starcluster import config as sconfig
from starcluster import cluster as scluster

VPC_CIDR = '10.0.0.0/16'
SUBNET_CIDR = '10.0.0.0/24'


def pytest_addoption(parser):
    parser.addoption("-L", "--live", action="store_true", default=False,
                     help="Run live StarCluster tests on a real AWS account")
    parser.addoption("-C", "--coverage", action="store_true", default=False,
                     help="Produce a coverage report for StarCluster")


def pytest_runtest_setup(item):
    if 'live' in item.keywords and not item.config.getoption("--live"):
        pytest.skip("pass --live option to run")


def pytest_configure(config):
    if config.getoption("--coverage"):
        config.option.cov_source = ['starcluster']
        config.option.cov_report = ['term-missing']
        plugin = CovPlugin(config.option, config.pluginmanager)
        config.pluginmanager.register(plugin, '_cov')


@pytest.fixture(scope="module")
def keypair(ec2, config):
    keypairs = ec2.get_keypairs()
    for key in keypairs:
        if key.name in config.keys:
            key.key_location = config.keys[key.name].key_location
            return key
    raise Exception("no keypair on ec2 defined in config")


@pytest.fixture(scope="module")
def config():
    cfg = sconfig.StarClusterConfig().load()
    assert cfg.aws.aws_access_key_id
    assert cfg.aws.aws_secret_access_key
    return cfg


@pytest.fixture(scope="module")
def ec2(config):
    return config.get_easy_ec2()


@pytest.fixture(scope="module")
def vpc(ec2):
    vpcs = ec2.conn.get_all_vpcs(filters={'tag:test': True})
    if not vpcs:
        vpc = ec2.conn.create_vpc(VPC_CIDR)
        vpc.add_tag('test', True)
    else:
        vpc = vpcs.pop()
    return vpc


@pytest.fixture(scope="module")
def gw(ec2, vpc):
    igw = ec2.conn.get_all_internet_gateways(
        filters={'attachment.vpc-id': vpc.id})
    if not igw:
        gw = ec2.conn.create_internet_gateway()
        ec2.conn.attach_internet_gateway(gw.id, vpc.id)
    else:
        gw = igw.pop()
    return gw


@pytest.fixture(scope="module")
def subnet(ec2, vpc, gw):
    subnets = ec2.conn.get_all_subnets(
        filters={'vpcId': vpc.id, 'cidrBlock': SUBNET_CIDR})
    if not subnets:
        subnet = ec2.conn.create_subnet(vpc.id, SUBNET_CIDR)
    else:
        subnet = subnets.pop()
    rtables = ec2.get_route_tables(filters={'vpc-id': vpc.id})
    if not rtables:
        rt = ec2.conn.create_route_table(vpc.id)
    else:
        rt = rtables.pop()
    ec2.conn.associate_route_table(rt.id, subnet.id)
    ec2.conn.create_route(rt.id, static.WORLD_CIDRIP, gateway_id=gw.id)
    return subnet


@pytest.fixture(scope="module")
def ami(ec2):
    img = ec2.conn.get_all_images(
        filters={'owner_id': static.STARCLUSTER_OWNER_ID,
                 'name': 'starcluster-base-ubuntu-13.04-x86_64'})
    assert len(img) == 1
    return img[0]


@pytest.fixture(scope="module",
                params=['flat', 'spot', 'vpc-flat', 'vpc-spot'])
def cluster(request, ec2, keypair, subnet, ami):
    size = 2
    shell = 'bash'
    user = 'testuser'
    subnet_id = subnet.id if 'vpc' in request.param else None
    public_ips = True if 'vpc' in request.param else None
    spot_bid = 0.08 if 'spot' in request.param else None
    instance_type = 't1.micro'
    cl = scluster.Cluster(ec2_conn=ec2,
                          cluster_tag=request.param,
                          cluster_size=size,
                          cluster_user=user,
                          keyname=keypair.name,
                          key_location=keypair.key_location,
                          cluster_shell=shell,
                          master_instance_type=instance_type,
                          master_image_id=ami.id,
                          node_instance_type=instance_type,
                          node_image_id=ami.id,
                          spot_bid=spot_bid,
                          subnet_id=subnet_id,
                          public_ips=public_ips)
    cl.start()
    assert cl.master_node
    assert len(cl.nodes) == size

    def terminate():
        try:
            cl.terminate_cluster()
        except:
            cl.terminate_cluster(force=True)
    request.addfinalizer(terminate)
    return cl


@pytest.fixture(scope="module")
def nodes(cluster):
    return cluster.nodes

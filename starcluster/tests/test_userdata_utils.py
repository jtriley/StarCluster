# Copyright 2009-2013 Justin Riley
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

from starcluster import utils
from starcluster import userdata

IGNORED = '#ignored\nThis file will not be executed.'
BASH_SCRIPT = '#!/bin/bash\nhostname'


def _get_sample_userdata(scripts=[IGNORED, BASH_SCRIPT], compress=True,
                         use_cloudinit=True):
    files = utils.strings_to_files(scripts, fname_prefix='sc')
    return userdata.bundle_userdata_files(files, compress=compress,
                                          use_cloudinit=use_cloudinit)


def _test_bundle_userdata(compress=False, use_cloudinit=True):
    ud = _get_sample_userdata(compress=compress, use_cloudinit=use_cloudinit)
    unbundled = userdata.unbundle_userdata(ud, decompress=compress)
    if use_cloudinit:
        cloud_cfg = unbundled.get('starcluster_cloud_config.txt')
        assert cloud_cfg.startswith('#cloud-config')
    else:
        enable_root = unbundled.get('starcluster_enable_root_login.sh')
        assert enable_root == userdata.ENABLE_ROOT_LOGIN_SCRIPT
    # ignored files should have #!/bin/false prepended automagically
    ilines = unbundled.get('sc_0').splitlines()
    assert ilines[0] == '#!/bin/false'
    # removing the auto-inserted #!/bin/false should get us back to the
    # original ignored script
    ignored_mod = '\n'.join(ilines[1:])
    assert IGNORED == ignored_mod
    # check that second file is bscript
    assert unbundled.get('sc_1') == BASH_SCRIPT


def _test_append_userdata(compress=True, use_cloudinit=True):
    ud = _get_sample_userdata(compress=compress, use_cloudinit=use_cloudinit)
    unbundled = userdata.unbundle_userdata(ud, decompress=compress)
    new_script = '#!/bin/bash\ndate'
    new_fname = 'newfile.sh'
    assert new_fname not in unbundled
    unbundled[new_fname] = new_script
    new_fobj = utils.string_to_file(new_script, new_fname)
    new_ud = userdata.append_to_userdata(ud, [new_fobj], decompress=compress)
    new_unbundled = userdata.unbundle_userdata(new_ud, decompress=compress)
    assert new_unbundled == unbundled


def _test_remove_userdata(compress=True, use_cloudinit=True):
    ud = _get_sample_userdata(compress=compress, use_cloudinit=use_cloudinit)
    unbundled = userdata.unbundle_userdata(ud, decompress=compress)
    new_ud = userdata.remove_from_userdata(ud, ['sc_0'], decompress=compress)
    new_ud = userdata.unbundle_userdata(new_ud, decompress=compress)
    assert 'sc_0' in unbundled
    del unbundled['sc_0']
    assert unbundled == new_ud


def test_cloudinit_compessed():
    _test_bundle_userdata(compress=True, use_cloudinit=True)


def test_cloudinit_no_compression():
    _test_bundle_userdata(compress=False, use_cloudinit=True)


def test_non_cloudinit():
    _test_bundle_userdata(use_cloudinit=False)


def test_cloudinit_append():
    _test_append_userdata(compress=True, use_cloudinit=True)


def test_cloudinit_append_no_compression():
    _test_append_userdata(compress=False, use_cloudinit=True)


def test_non_cloudinit_append():
    _test_append_userdata(use_cloudinit=False)


def test_cloudinit_remove():
    _test_remove_userdata(compress=True, use_cloudinit=True)


def test_cloudinit_remove_no_compression():
    _test_remove_userdata(compress=False, use_cloudinit=True)


def test_non_cloudinit_remove():
    _test_remove_userdata(use_cloudinit=False)

from starcluster import utils
from starcluster import cloudinit


def _test_bundle_userdata(compress=False, use_cloudinit=True):
    ignored = '#ignored\nThis file will not be executed.'
    bscript = '#!/bin/bash\hostname'
    files = utils.strings_to_files([ignored, bscript], fname_prefix='sc')
    userdata = cloudinit.bundle_userdata_files(files, compress=compress,
                                               use_cloudinit=use_cloudinit)
    unbundled = cloudinit.unbundle_userdata(userdata, decompress=compress)
    if use_cloudinit:
        cloud_cfg = unbundled.get('starcluster_cloud_config.txt')
        assert cloud_cfg.startswith('#cloud-config')
    else:
        enable_root = unbundled.get('starcluster_enable_root_login.sh')
        assert enable_root == cloudinit.ENABLE_ROOT_LOGIN_SCRIPT
    # ignored files should have #!/bin/false prepended automagically
    ilines = unbundled.get('sc_0').splitlines()
    assert ilines[0] == '#!/bin/false'
    # removing the auto-inserted #!/bin/false should get us back to the
    # original ignored script
    ignored_mod = '\n'.join(ilines[1:])
    assert ignored == ignored_mod
    # check that second file is bscript
    assert unbundled.get('sc_1') == bscript


def test_cloudinit():
    _test_bundle_userdata(compress=False)
    _test_bundle_userdata(compress=True)


def test_non_cloudinit():
    _test_bundle_userdata(use_cloudinit=False)

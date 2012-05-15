from starcluster import cloudinit


def _test_mp_userdata_utils(compress=False):
    scstore, bscript = '#sc-store\nhi', '#!/bin/bash\nthere'
    userdata = cloudinit.mp_userdata_from_strings([scstore, bscript],
                                                  compress=compress)
    mp = cloudinit.get_mp_from_userdata(userdata, decompress=compress)
    store, script, phandler = mp.get_payload()
    assert store.get_payload() == scstore
    assert script.get_payload() == bscript
    assert phandler.get_payload() == cloudinit.sc_part_handler


def test_mp_userdata_utils():
    _test_mp_userdata_utils(compress=False)
    _test_mp_userdata_utils(compress=True)

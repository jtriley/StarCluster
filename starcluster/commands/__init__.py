#!/usr/bin/env python
from start import CmdStart
from stop import CmdStop
from sshmaster import CmdSshMaster
from sshnode import CmdSshNode
from sshinstance import CmdSshInstance
from listclusters import CmdListClusters
from createimage import CmdCreateImage
from downloadimage import CmdDownloadImage
from createvolume import CmdCreateVolume
from listkeypairs import CmdListKeyPairs
from listzones import CmdListZones
from listregions import CmdListRegions
from listimages import CmdListImages
from listbuckets import CmdListBuckets
from showimage import CmdShowImage
from showbucket import CmdShowBucket
from removevolume import CmdRemoveVolume
from removeimage import CmdRemoveImage
from listinstances import CmdListInstances
from listspots import CmdListSpots
from showconsole import CmdShowConsole
from listvolumes import CmdListVolumes
from listpublic import CmdListPublic
from runplugin import CmdRunPlugin
from spothistory import CmdSpotHistory
from shell import CmdShell
from createkey import CmdCreateKey
from help import CmdHelp

all_cmds = [
    CmdStart(),
    CmdStop(),
    CmdListClusters(),
    CmdSshMaster(),
    CmdSshNode(),
    CmdSshInstance(),
    CmdListInstances(),
    CmdListImages(),
    CmdListPublic(),
    CmdCreateKey(),
    CmdCreateImage(),
    CmdRemoveImage(),
    CmdDownloadImage(),
    CmdListVolumes(),
    CmdCreateVolume(),
    CmdRemoveVolume(),
    CmdListSpots(),
    CmdSpotHistory(),
    CmdShowConsole(),
    CmdListKeyPairs(),
    CmdListRegions(),
    CmdListZones(),
    CmdListBuckets(),
    CmdShowBucket(),
    CmdShowImage(),
    CmdRunPlugin(),
    CmdShell(),
    CmdHelp(),
]

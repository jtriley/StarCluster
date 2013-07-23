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

from start import CmdStart
from addnode import CmdAddNode
from removenode import CmdRemoveNode
from stop import CmdStop
from terminate import CmdTerminate
from restart import CmdRestart
from sshmaster import CmdSshMaster
from sshnode import CmdSshNode
from sshinstance import CmdSshInstance
from listclusters import CmdListClusters
from s3image import CmdS3Image
from ebsimage import CmdEbsImage
from downloadimage import CmdDownloadImage
from createvolume import CmdCreateVolume
from resizevolume import CmdResizeVolume
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
from loadbalance import CmdLoadBalance
from shell import CmdShell
from createkey import CmdCreateKey
from removekey import CmdRemoveKey
from put import CmdPut
from get import CmdGet
from help import CmdHelp

all_cmds = [
    CmdStart(),
    CmdStop(),
    CmdTerminate(),
    CmdRestart(),
    CmdListClusters(),
    CmdSshMaster(),
    CmdSshNode(),
    CmdPut(),
    CmdGet(),
    CmdAddNode(),
    CmdRemoveNode(),
    CmdLoadBalance(),
    CmdSshInstance(),
    CmdListInstances(),
    CmdListSpots(),
    CmdListImages(),
    CmdListPublic(),
    CmdListKeyPairs(),
    CmdCreateKey(),
    CmdRemoveKey(),
    CmdS3Image(),
    CmdEbsImage(),
    CmdShowImage(),
    CmdDownloadImage(),
    CmdRemoveImage(),
    CmdCreateVolume(),
    CmdListVolumes(),
    CmdResizeVolume(),
    CmdRemoveVolume(),
    CmdSpotHistory(),
    CmdShowConsole(),
    CmdListRegions(),
    CmdListZones(),
    CmdListBuckets(),
    CmdShowBucket(),
    CmdRunPlugin(),
    CmdShell(),
    CmdHelp(),
]

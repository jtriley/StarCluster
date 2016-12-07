#!/bin/bash

VOLUMES=""
for device in `curl -s 169.254.169.254/latest/meta-data/block-device-mapping/`
do
        if [[ $device == "ephemeral"* ]]
        then
                block=`curl -s 169.254.169.254/latest/meta-data/block-device-mapping/$device | awk -F/ '{print $NF}'`;
                if [[ -e /dev/$block ]]
                then
			#if [ ! -e /mnt/$device ]
			#then
	                #        mkfs.ext3 /dev/$block
	                #        mkdir /mnt/$device
	                #        mount /dev/$block /mnt/$device
			#	chmod 1777 /mnt/$device
			#fi
			pvcreate /dev/$block
			VOLUMES="${VOLUMES} /dev/$block"
                fi
        fi
done

vgcreate vg_ephemeral $VOLUMES
SIZE=`vgdisplay vg_ephemeral | grep "Total PE" | awk '{print $3}'`
lvcreate -l $SIZE vg_ephemeral -n ephemerallv
mkfs.ext3 /dev/mapper/vg_ephemeral-ephemerallv
mkdir /scratch
mount /dev/mapper/vg_ephemeral-ephemerallv /scratch
chmod 1777 /scratch

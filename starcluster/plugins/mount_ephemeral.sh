#!/bin/bash

for device in `curl -s 169.254.169.254/latest/meta-data/block-device-mapping/`
do
        if [[ $device == "ephemeral"* ]]
        then
                block=`curl -s 169.254.169.254/latest/meta-data/block-device-mapping/$device | awk -F/ '{print $NF}'`;
                if [[ -e /dev/$block ]]
                then
			if [ ! -e /mnt/$device ]
			then
	                        mkfs.ext3 /dev/$block
	                        mkdir /mnt/$device
	                        mount /dev/$block /mnt/$device
				chmod 1777 /mnt/$device
			fi
                fi
        fi
done


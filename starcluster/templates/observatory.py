# Copyright 2018 Daniel Treiman
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


install_script= """
#!/bin/bash

/bin/mkdir -p /etc/starcluster

/usr/local/bin/pip install git+https://github.com/dantreiman/StarCluster.git --upgrade

if [ -d /opt/starcluster-observatory ]
then
    # Update source code to latest stable.
    cd /opt/starcluster-observatory/ && /usr/bin/git pull
else
    # Clone latest stable version.
    /usr/bin/git clone https://github.com/dantreiman/starcluster-observatory.git /opt/starcluster-observatory
fi
"""


api_service= """
[Unit]
Description=Observatory API

[Service]
User=root
Environment="PATH=/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
Restart=on-failure
WorkingDirectory=/opt/starcluster-observatory/src/api
ExecStart=/usr/bin/python3 /opt/starcluster-observatory/src/api/api-server.py

[Install]
WantedBy=multi-user.target
"""


dashboard_service= """
[Unit]
Description=Observatory Dashboard

[Service]
User=root
Environment="PATH=/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
Restart=on-failure
WorkingDirectory=/opt/starcluster-observatory/src/dashboard
ExecStart=/usr/bin/python3 /opt/starcluster-observatory/src/dashboard/dashboard-server.py

[Install]
WantedBy=multi-user.target
"""

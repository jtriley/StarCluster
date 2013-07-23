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

import jinja2
import pkg_resources

__all__ = [
    'config',
    'sge',
    'condor',
    'user_msgs',
]

_web_tmpl_loader = jinja2.Environment(loader=jinja2.PrefixLoader({
    'web': jinja2.PackageLoader('starcluster.templates', 'web'),
}))

get_web_template = _web_tmpl_loader.get_template

_tmpl_loader = jinja2.Environment(
    loader=jinja2.PackageLoader('starcluster', 'templates'))

get_template = _tmpl_loader.get_template


def get_resource(pkg_data_path, stream=True):
    pkg_res_meth = pkg_resources.resource_filename
    if stream:
        pkg_res_meth = pkg_resources.resource_stream
    return pkg_res_meth('starcluster.templates', pkg_data_path)


TemplateNotFound = jinja2.TemplateNotFound

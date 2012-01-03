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

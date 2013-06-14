from completers import NodeCompleter
from starcluster import static, config, utils
import pprint


class CmdReloadConfig(NodeCompleter):
    """
    reloadconfig -c <cluster-template> <cluster-tag>

    Reloads and stores a new configuration within a running cluster.
    """
    names = ['reloadconfig', 'rc']

    def addopts(self, parser):
        if self.cfg:
            templates = self.cfg.clusters.keys()
        parser.add_option("-c", "--cluster-template", action="store",
                                dest="cluster_template", choices=templates,
                                default=False, help="cluster template to use "
                                "from the config file")

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please specify a cluster <cluster_tag>")
        if not self.opts.cluster_template:
            self.parser.error("please specify a cluster template")
        tag = self.tag = args[0]

        fieldsToUpdate = ["disable_queue", "disable_threads",
                          "force_spot_master", "master_image_id",
                          "master_instance_type", "node_image_id",
                          "node_instance_type", "spot_bid",
                          "disable_cloudinit", "plugins_order", "cluster_size"]

        cluster = self.cm.get_cluster(tag, load_plugins=False)
        new_cfg = self.cfg.get_cluster_template(self.opts.cluster_template,
                                                load_plugins=False)
        to_update = {}
        for field in fieldsToUpdate:
            old_val = getattr(cluster, field)
            new_val = getattr(new_cfg, field)
            if old_val != new_val:
                self.log.info("{0}: [{1}] -> [{2}]"
                    .format(field, old_val, new_val))
            to_update[field] = new_val

        if to_update:
            cluster.update(to_update)
            sg = cluster.cluster_group
            sg.remove_tag(static.CORE_TAG)
            cluster.save_core_settings(sg)
            sg.remove_tag(static.USER_TAG)
            cluster.save_user_settings(sg)

        current_plugins_conf = config.plugins_config_stored_to_json(
            cluster.master_node.get_plugins_full_metadata(
                cluster.plugins_order))
        new_plugins_conf = config.plugins_config_file_to_json(self.cfg.plugins)
        diff = config.json_diff(current_plugins_conf, new_plugins_conf)
        if len(diff['+']) or len(diff['-']):
            pprint.pprint(diff)
            org_plugins_confg = config.plugins_config_stored_to_json(
                cluster.master_node.get_plugins_org_metadata())
            diff_to_store = config.json_diff(org_plugins_confg,
                                             new_plugins_conf)
            diff_to_store = utils.dump_compress_encode(diff_to_store)
            if len(diff_to_store) > 255:
                raise Exception("New plugins config doesn't fit in a single "
                                "tag. Multiple tag save must be implemented")
            sg.remove_tag("@sc-plugins")
            sg.add_tag("@sc-plugins", diff_to_store)

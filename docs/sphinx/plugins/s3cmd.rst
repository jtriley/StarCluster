.. _s3cmd-plugin:

###########
S3cmd Plugin
###########

.. _s3cmd: http://s3tools.org/s3cmd

This plugin configures a $HOME/.s3cfg config file for the s3cmd_ utility in
the ``CLUSTER_USER``. It supports both copying an existing .s3cfg config file
and auto-generating a config file using the currently active StarCluster
credentials.

To use this plugin you must first define it in the StarCluster config file:

.. code-block:: ini

    [plugin s3cmd]
    setup_class = starcluster.plugins.s3cmd.S3CmdPlugin

By default the plugin auto-generates a .s3cmd config file for you using the
currently active AWS credentials and default options as set by s3cmd
at the time the plugin is executed. If you'd prefer to copy your own
config file instead add the ``s3cmd_cfg`` setting:

.. code-block:: ini

    [plugin s3cmd]
    setup_class = starcluster.plugins.s3cmd.S3CmdPlugin
    s3cmd_cfg = /path/to/your/s3cmd/.s3cfg

Once you've defined the plugin in your config, add the s3cmd plugin to the list
of plugins in one of your cluster templates:

.. code-block:: ini

    [cluster smallcluster]
    plugins = s3cmd

Now whenever you start a cluster using that cluster template the
``CLUSTER_USER`` will automatically be configured to use s3cmd.

Additional options for s3cmd can be included in the ``[plugin s3cmd]`` block:

.. code-block:: ini

    [plugin s3cmd]
    setup_class = starcluster.plugins.s3cmd.S3CmdPlugin
    gpg_command = /path/to/gpg
    gpg_passphrase = my_gpg_passphrase
    use_https = True

These options are then written into the .s3cfg configure file.
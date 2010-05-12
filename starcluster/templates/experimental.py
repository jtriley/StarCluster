spotmsg = """USING SPOT INSTANCES IS EXPERIMENTAL.

Spot instances can take a long time to come up and may not come
up at all depending on the current AWS load and your max spot bid
price.

For now, StarCluster will wait indefinitely until all instances come up. 
If this takes too long, you can cancel the start command using CTRL-C and 
manually wait for the spot instances to come up by periodically checking 
the output of: 

   $ starcluster listspots

Once all spot requests in the '%(launch_group)s' launch group are in an 
'active' state and have an instance_id (e.g. i-99999) associated with them 
re-execute this same start command with the --no-create option:

   $ starcluster %(cmd)s

This will use the existing spot instances launched previously and 
continue starting the cluster.
"""

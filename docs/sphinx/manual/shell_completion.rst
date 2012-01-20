Enabling Tab Completion for Bash/Zsh
====================================
StarCluster has support for tab completion in both Bash and Zsh. If you're not
familiar with tab completion, try typing **ls /** at a command prompt and then
pressing the **Tab** key::

    user@localhost % ls /
    files
    afs/         etc/         lib64/       mnt/         sbin/        usr/
    bin/         home/        lost+found/  opt/         sys/         var/
    boot/        lib@         media/       proc/        tera/
    dev/         lib32/       mit/         root/        tmp/

Notice how after you pressed the **Tab** key the shell displayed a list of
options for you to choose from. Typing a few more characters and pressing
**Tab** again will reduce the number of options displayed::

    user@localhost % ls /s
    files
    sbin/  sys/

Typing a **b** and pressing **Tab** would then automatically complete to **ls
/sbin**.

Enabling StarCluster Tab Completion in BASH
-------------------------------------------
To enable StarCluster bash-completion support for every shell you open, add the
following line to your ~/.bashrc file::

    source /path/to/starcluster/completion/starcluster-completion.sh

Enabling StarCluster Tab Completion in ZSH
-------------------------------------------
To enable StarCluster zsh-completion support for every
shell you open, add the following to the top of your ~/.zshrc file::

    autoload -U compinit && compinit
    autoload -U bashcompinit && bashcompinit
    source /path/to/starcluster/completion/starcluster-completion.sh

Using StarCluster Tab Completion
--------------------------------
After you've enabled StarCluster tab completion support in bash or zsh, you
should now be able to tab complete all options to StarCluster actions.

For example, typing "starcluster --" and pressing the **Tab** key will show you
a list of StarCluster's global options::

    user@localhost % starcluster --
    --config   --debug    --help     --version

This also works for each *action* in starcluster::

    user@localhost % starcluster start --
    --availability-zone     --help                  --master-instance-type
    --cluster-shell         --key-location          --no-create
    --cluster-size          --keyname               --node-image-id
    --cluster-user          --login-master          --node-instance-type
    --description           --master-image-id       --validate-only

Pressing **Tab** on just the start action will also list the possible
arguments.  Since start takes a *cluster template* as an argument, you'll
notice that the cluster templates you defined in the config file show up in the
list of suggestions::

    user@localhost % starcluster start
    -a                      -k                      -n
    --availability-zone     -K                      --no-create
    --cluster-shell         --key-location          --node-image-id
    --cluster-size          --keyname               --node-instance-type
    --cluster-user          -l                      -s
    -d                      largecluster            -S
    --description           --login-master          smallcluster
    eucatest                -m                      -u
    -h                      --master-image-id       -v
    --help                  --master-instance-type  --validate-only
    -i                      mediumcluster           -x
    -I                      molsim

In the example above, *smallcluster*, *mediumcluster*, *largecluster*, etc. are
all cluster templates defined in ~/.starcluster/config. Typing an **s**
character after the *start* action will autocomplete the first argument to
*smallcluster*

The *start* action is not the only action supporting tab completion.  Pressing
**Tab** on the *sshmaster*, *sshnode*, and *sshinstance* actions will also
complete based on active cluster names, instance ids, and dns names::

    user@localhost % starcluster sshmaster
    -h           --help       mycluster  -u           --user

In the above example, *mycluster* is a currently running StarCluster. Typing a **m** character
and pressing **Tab** would autocomplete the command to *starcluster sshmaster mycluster*::

    user@localhost % starcluster sshnode
    % starcluster sshnode
    0            3            6            9            mycluster
    1            4            7            -h           -u
    2            5            8            --help       --user

In the above example, *mycluster* is a currently running StarCluster. The shell
also suggests numbers 0-9 because there are 10 machines running in *mycluster*::

    user@localhost % starcluster sshinstance
    ec2-123-123-123-137.compute-1.amazonaws.com
    ec2-123-123-123-231.compute-1.amazonaws.com
    ec2-123-123-123-16.compute-1.amazonaws.com
    ec2-123-123-123-190.compute-1.amazonaws.com
    ec2-123-123-123-41.compute-1.amazonaws.com
    ec2-123-123-123-228.compute-1.amazonaws.com
    ec2-123-123-123-180.compute-1.amazonaws.com
    ec2-123-123-123-191.compute-1.amazonaws.com
    ec2-123-123-123-228.compute-1.amazonaws.com
    ec2-123-123-123-199.compute-1.amazonaws.com
    -h
    --help
    i-91zz1bea
    i-91zz1be8
    i-91zz1bee
    i-91zz1be6
    i-91zz1be4
    i-91zz1bf8
    i-91zz1bfe
    i-91zz1bfc
    i-91zz2eca
    i-91zz1bde
    -u
    --user

In the above example, pressing **Tab** after the *sshinstance* action will
present a list of dns names and instance ids to ssh to. Typing a few more
characters, such as *ec2-* will reduce the suggestions to only dns names::

    user@localhost % starcluster sshinstance ec2-
    ec2-123-123-123-137.compute-1.amazonaws.com
    ec2-123-123-123-231.compute-1.amazonaws.com
    ec2-123-123-123-16.compute-1.amazonaws.com
    ec2-123-123-123-190.compute-1.amazonaws.com
    ec2-123-123-123-41.compute-1.amazonaws.com
    ec2-123-123-123-228.compute-1.amazonaws.com
    ec2-123-123-123-180.compute-1.amazonaws.com
    ec2-123-123-123-191.compute-1.amazonaws.com
    ec2-123-123-123-228.compute-1.amazonaws.com
    ec2-123-123-123-199.compute-1.amazonaws.com

Similarly for instance ids::

    user@localhost % starcluster sshinstance i-
    i-91zz1bea  i-91zz1be8  i-91zz1bee  i-91zz1be6  i-91zz1be4
    i-91zz1bf8  i-91zz1bfe  i-91zz1bfc  i-91zz2eca  i-91zz1bde

These examples show a small subset of the actions that can be tab completed.
Try tab-completing the other actions in starcluster to see their available
options and suggestions for their arguments.

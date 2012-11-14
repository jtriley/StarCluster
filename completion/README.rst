############################
StarCluster Shell Completion
############################

Enabling shell completion allows you to automatically complete all StarCluster
commands and options simply by pressing the ``Tab`` key after typing
``starcluster`` in your shell.

You must configure your shell properly to use StarCluster's shell completion.
You will need to follow one of the `Bash Setup` or `ZSH Setup` sections below
depending on which shell you're using. If you're unsure which shell you're
using then more than likely it's Bash. You can check which shell you're
currently using by running the following command in terminal::

    $ echo $SHELL
    /bin/bash

Shells other than Bash and ZSH are not supported at this time.

**********
Bash Setup
**********
To enable StarCluster completion support for every Bash shell you open, add the
following line to your ``$HOME/.bashrc`` file::

    source /path/to/starcluster/completion/starcluster-completion.sh

*********
ZSH Setup
*********
To enable StarCluster completion support for every ZSH shell you open, add the
following to the top of your ``$HOME/.zshrc`` file::

    autoload -U compinit && compinit
    autoload -U bashcompinit && bashcompinit
    source /path/to/starcluster/completion/starcluster-completion.sh

*******************
Example Completions
*******************
Once you've configured completion in your shell you can, for example, type
``starcluster --`` and press the **Tab** key to show a list of StarCluster's
global options::

    user@localhost % starcluster --
    --config   --debug    --help     --version

This also works for each *action* in starcluster::

    user@localhost % starcluster start --
    --availability-zone     --help                  --master-instance-type
    --cluster-shell         --key-location          --no-create
    --cluster-size          --keyname               --node-image-id
    --cluster-user          --login-master          --node-instance-type
    --description           --master-image-id       --validate-only

The ``start`` action is not the only action supporting tab completion.
Pressing **Tab** on the ``sshmaster``, ``sshnode``, and ``sshinstance`` actions
will also complete based on active cluster names, instance ids, and dns names::

    user@localhost % starcluster sshmaster
    -h           --help       mycluster  -u           --user

In the above example, `mycluster` is a currently running StarCluster. Typing a
space character and an **m** character and pressing **Tab** in the above
example would autocomplete the command to ``starcluster sshmaster mycluster``::

    user@localhost % starcluster sshnode
    % starcluster sshnode
    0            3            6            9            mycluster
    1            4            7            -h           -u
    2            5            8            --help       --user

Similarly, the ``sshinstance`` command will tab complete instance ids::

    user@localhost % starcluster sshinstance i-
    i-91zz1bea  i-91zz1be8  i-91zz1bee  i-91zz1be6  i-91zz1be4
    i-91zz1bf8  i-91zz1bfe  i-91zz1bfc  i-91zz2eca  i-91zz1bde

These examples show only a small subset of the actions that can be tab
completed. Try tab-completing other actions in starcluster to see their
available options and suggestions for their arguments.

See the official tab completion docs for more examples:

http://star.mit.edu/cluster/docs/latest/manual/shell_completion.html

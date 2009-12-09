# StarCluster bash/zsh[bashcompinit] completion script
#
# source this file from your shell to enable starcluster completion support
#
# (see README.bash for bash-specific instructions)
# (see README.zsh for zsh-specific instructions)

_starcluster()
{
    COMPREPLY=( $( \
        COMP_LINE=$COMP_LINE  COMP_POINT=$COMP_POINT \
        COMP_WORDS="${COMP_WORDS[*]}"  COMP_CWORD=$COMP_CWORD \
        OPTPARSE_AUTO_COMPLETE=1 $1 ) )
}
complete -F _starcluster -o default starcluster

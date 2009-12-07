To enable StarCluster zsh-completion support for every 
shell you open, add the following to the top of your ~/.zshrc file:

autoload -U compinit && compinit
autoload -U bashcompinit && bashcompinit
source /path/to/starcluster/completion/starcluster-completion.sh

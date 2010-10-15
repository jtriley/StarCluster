#!/bin/bash
SRC=$(dirname $0)
echo ">>> Running pyflakes..."
find $SRC/starcluster -iname \*.py -exec pyflakes {} \;
echo ">>> Running pep8..."
find $SRC/starcluster -iname \*.py -exec pep8 {} \;
echo ">>> Done"

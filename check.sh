#!/bin/bash
echo ">>> Running pyflakes..."
find starcluster -iname \*.py -exec pyflakes {} \;
echo ">>> Running pep8..."
find starcluster -iname \*.py -exec pep8 {} \;
echo ">>> Done"

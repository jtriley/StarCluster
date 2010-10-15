#!/bin/bash
SRC=$(dirname $0)/starcluster
find $SRC -iname \*.pyc -exec rm {} \;
find $SRC -iname \*.pyo -exec rm {} \;

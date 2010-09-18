#!/bin/bash
find starcluster -iname \*.py -exec pyflakes {} \;
find starcluster -iname \*.py -exec pep8 {} \;

#!/bin/bash
find . -iname \*.pyc -exec rm {} \;
find . -iname \*.pyo -exec rm {} \;

#!/usr/bin/env bash

function getName {
    # searching in a file the following substrings
    cat setup.py \
    |grep -e "name=" \
    |awk '{split($0,a,"="); print a[2]}' \
    | sed 's/.$//' \
    | sed "s/'//g; s/\"//g"

}

script_name=$(getName)


pip uninstall $script_name
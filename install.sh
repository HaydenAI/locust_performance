#!/usr/bin/env bash
# Creating 'dist/auto_test_name2-0.2.0.tar.gz'


function getName {
    # searching in a file the following substrings
    cat setup.py \
    |grep -e "name=" \
    |awk '{split($0,a,"="); print a[2]}' \
    | sed 's/.$//' \
    | sed "s/'//g; s/\"//g"
}


script_name=$(getName)
version=$(getVersion)
echo "----> script_name: $(getName)"
package_name=$script_name-1.0.0.tar.gz

# Main routine for tar.gz deployment
echo "Building dist ... "
python3 setup.py sdist
echo "Deploying package: "$package_name
pip install dist/$package_name

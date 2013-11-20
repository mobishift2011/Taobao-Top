#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

sudo easy_install pip
sudo pip install virtualenvwrapper

source /usr/local/bin/virtualenvwrapper.sh
mkvirtualenv baokuan
workon baokuan

pip install --upgrade cython
# pip install https://github.com/SiteSupport/gevent/tarball/master

pip install -r "$DIR/../requirements.txt"
#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export DJANGO_SETTINGS_MODULE=baokuan.settings
export PYTHONPATH=$DIR:$PYTHONPATH
export ENV=$1
source /usr/local/bin/virtualenvwrapper.sh
workon baokuan

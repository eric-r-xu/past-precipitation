#!/bin/sh
sudo apt install -y python3-pip
sudo apt-get install python3-setuptools
cd past-precipitation;sudo apt-get install python3-venv
sudo apt install build-essential libssl-dev libffi-dev python-dev-is-python3
python3 -m venv env
. ./env/bin/activate
python -m pip install --upgrade pip
sudo apt-get install libsasl2-dev libsasl2-2 libsasl2-modules-gssapi-mit
sudo apt-get install libmysqlclient-dev
pip install -r ~/past-precipitation/py3requirements.txt

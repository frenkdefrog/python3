#!/bin/bash

HOME="/root"

echo "Obtaining the host ssh keys"
SSH_DIR=$HOME/.ssh
mkdir -p ${SSH_DIR}
cp ${SSH_DIR}-host/* ${SSH_DIR}

echo "Setting the right permissions"
chown root ${SSH_DIR}/*
chmod 400 ${SSH_DIR}/*

apt-get update && apt-get install -y git mariadb-client
git config --global --add safe.directory /workspace

python3 -m venv venv
source venv/bin/activate && pip3 install -r requirements.txt

echo "Done configuration on container"

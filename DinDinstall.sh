#!/bin/bash

GRN='\033[0;32m'
YLW='\033[1;33m'
NC='\033[0m'

echo -e "${GRN}Installing python3-pip, npm, redis-server,  unzip, postgresql, lib-pq-dev, and wget${NC}"
apt update
apt install -y python3-pip npm redis-server unzip wget postgresql libpq-dev &&
pip3 install -r requirements/dev.txt &&

cp .env.example .env
npm install && npm run build

mkdir data
mkdir data/tmp
mkdir logs

service postgresql start
su --login postgres -c "echo -e ALTER USER postgres WITH PASSWORD \'passwordfoo\'\; | psql"
su --login postgres -c "echo -e CREATE DATABASE namefoo\; | psql"

echo -e "${GRN}Downloading and setting up terraform${NC}"
wget https://releases.hashicorp.com/terraform/0.12.29/terraform_0.12.29_linux_amd64.zip
unzip terraform_0.12.29_linux_amd64.zip
mv terraform /usr/bin/terraform

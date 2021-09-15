#!/bin/bash

GRN='\033[0;32m'
YLW='\033[1;33m'
NC='\033[0m'
username=$(whoami)

# Add pip-executables to the path if they aren't already
if grep -q "export PATH=/home/$(whoami)/.local/bin:$PATH" ~/.bashrc; then
	:
else
	echo "export PATH=/home/$(whoami)/.local/bin:$PATH" >> ~/.bashrc &&
	source ~/.bashrc
fi

echo -e "${GRN}Installing python3-pip, npm, redis-server,  unzip, postgresql, lib-pq-dev, and wget${NC}"

apt update
apt install -y python3-pip npm redis-server unzip wget postgresql libpq-dev &&
pip3 install -r requirements/dev.txt &&

npm install &&
mkdir data
mkdir data/tmp
mkdir logs

su --login postgres -c "echo -e ALTER USER postgres WITH PASSWORD \'passwordfoo\'\; | psql"
su --login postgres -c "echo -e CREATE DATABASE namefoo\; | psql"

echo -e "${GRN}Downloading and setting up terraform${NC}"

wget https://releases.hashicorp.com/terraform/0.12.29/terraform_0.12.29_linux_amd64.zip
unzip terraform_0.12.29_linux_amd64.zip
mv terraform /usr/bin/terraform &&

echo -e "${GRN}Downloading and setting up docker${NC}"

wget -O docker.sh get.docker.com
chmod +x docker.sh
./docker.sh
echo -e "${GRN}Creating a user group for docker, and adding your account...${NC}"
groupadd docker
usermod -aG docker $username
su $USER --login

echo -e "${GRN}Done! Next run the first-run setup: ${NC} npm run build"
echo -e "${GRN}Then, you should be able to run the app any time with ${NC} npm start"
echo -e "${GRN}You may need to make sure that pip-executables are accessible${NC}"
echo -e "${GRN}If the ${NC} flask ${GRN} or ${NC} celery ${GRN} commands are not recognized, try:"
echo -e "${NC}source ~/.bashrc ${GRN} or ${NC} export PATH=/home/$username/.local/bin:\$PATH ${NC}"

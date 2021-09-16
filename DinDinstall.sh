apt update
apt install -y python3-pip npm redis-server unzip wget postgresql libpq-dev
pip3 install -r requirements/dev.txt

service postgresql start
cp .env.example .env
npm install && npm run build

mkdir data
mkdir data/tmp
mkdir logs

su --login postgres -c "echo -e ALTER USER postgres WITH PASSWORD \'passwordfoo\'\; | psql"
su --login postgres -c "echo -e CREATE DATABASE namefoo\; | psql"

wget https://releases.hashicorp.com/terraform/0.12.29/terraform_0.12.29_linux_amd64.zip
unzip terraform_0.12.29_linux_amd64.zip
mv terraform /usr/bin/terraform

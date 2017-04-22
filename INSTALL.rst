switch=# \COPY administration_currency from '/srv/applications/switch/administration_currency.csv' DELIMITERS ',' CSV;
switch=# SELECT setval('administration_currency_id_seq', (SELECT max(id) FROM administration_currency));
pip install pytz
pip install django-suit
pip install csvImporter
yum install python-psycopg2.x86_64
PGLIB=/usr/pgsql-9.1/lib
PGDATA=/var/lib/pgsql/9.1/data
PATH=$PATH:/usr/pgsql-9.1/bin
export PGLIB PGDATA PATH
yum groupinstall Development tools
\COPY vbs_responsestatus from '/srv/applications/mobiwallet/vbs_responsestatus.csv' DELIMITERS ',' CSV;
SELECT setval('crm_productitem_institution_till_id_seq', (SELECT max(id) FROM crm_productitem_institution_till));

#FOR REFERENCE ------> \copy (SELECT first_name, last_name, email FROM users) TO dump.csv CSV DELIMITER ','
pip install goslate

CREATE EXTENSION postgis;

celery -A switch worker -l info


>>> from switch.celery import app
>>> app.control.revoke('c189b22d-ef12-4063-af9f-ee790370f3c3')



rabbitmqctl stop_app
rabbitmqctl reset
rabbitmqctl start_app


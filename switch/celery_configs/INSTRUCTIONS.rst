chown root.root *

celeryd and celerybeat  permissions chmod 640

symlink celeryd_daemon as celeryd and celerybeat_daemon as celerybeat to /etc/init.d/
celeryd_daemon and celerybeat_daemon permissions chmod 755

chown system.system

symlink rabbitmq.config and rabbitmq-env.conf to /etc/rabbitmq/
rabbitmq.config and rabbitmq-env.conf permissions chmod 755


service nginx restart; service uwsgi restart; service celeryd stop; pkill -f celery; service celeryd restart; service celerybeat restart

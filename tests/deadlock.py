from django.db import transaction
from paygate.models import Endpoint

from celery import shared_task
#from celery.contrib.methods import task_method
from celery import task
from switch.celery import app
from switch.celery import single_instance_task

@app.task(ignore_result=True)
@transaction.atomic
def testing_deadlock():
    def check_count():
        e = Endpoint.objects.select_for_update().filter(id__in=[2,4,6,8])
        print e.count()
    import time
    for x in range(0,10):
        print x
        print check_count()
        time.sleep(5)

Endpoint.objects.get(id=4)

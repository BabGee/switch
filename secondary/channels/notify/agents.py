import faust
from faust.types import StreamT
#from primary.core.async.faust import app
from switch.faust import app
import requests, json


from django.db import transaction
from .models import *
from .service import *
from django.db.models import Q,F

import pandas as pd
import numpy as np
import time
from asgiref.sync import sync_to_async
import asyncio
import random
import logging
import aiohttp
from http.client import HTTPConnection  # py3
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    List,
    Mapping,
    MutableMapping,
    Set,
    Tuple,
    Type,
    cast,
)

lgr = logging.getLogger(__name__)
lgr.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s-%(name)s %(funcName)s %(process)d %(thread)d-(%(threadName)-2s) %(levelname)s-%(message)s')
ch.setFormatter(formatter)

lgr.addHandler(ch)

HTTPConnection.debuglevel = 1

s = time.perf_counter()


class Greeting(faust.Record):
    from_name: str
    to_name: str
    count: float
    records: int


topic = app.topic('switch-hello-topic', value_type=Greeting)

@app.agent(topic)
async def hello(greetings):
	async for greeting in greetings:
		lgr.info(f'Hello from {greeting.from_name} to {greeting.to_name} | Count {greeting.count} | Records {greeting.records}')

#@app.task
#@app.timer(interval=0.25)
@app.timer(interval=10)
async def example_sender_task(app):
    count = time.perf_counter() - s
    elapsed = "{0:.2f}".format(count)
    records = random.randint(1,1000) 
    await hello.send(
        value=Greeting(from_name='Switch Notify Task', to_name='you', count=float(elapsed), records=records),
    )
    count+=1


is_bulk = False
limit_batch = 100

#@app.task
@app.timer(interval=10)
#@transaction.atomic
async def send_outbound_messages(app):
	try:
		lgr.info(f'{app}')

		count = time.perf_counter() - s
		elapsed = "{0:.2f}".format(count)
		lgr.info(f'0:Elapsed {elapsed}')
		with transaction.atomic():
			#.order_by('contact__product__priority').select_related('contact','template','state').all
			def outbound_query():        
				return Outbound.objects.select_for_update(of=('self',)).filter(Q(contact__subscribed=True),Q(contact__product__notification__code__channel__name='WHATSAPP API'),~Q(recipient=None),
					Q(contact__status__name='ACTIVE',contact__product__is_bulk=is_bulk),
					Q(Q(contact__product__trading_box=None)|Q(contact__product__trading_box__open_time__lte=timezone.localtime().time(),
					contact__product__trading_box__close_time__gte=timezone.localtime().time())),
					Q(scheduled_send__lte=timezone.now(),state__name='CREATED',date_created__gte=timezone.now()-timezone.timedelta(hours=24))\
					|Q(state__name="PROCESSING",date_modified__lte=timezone.now()-timezone.timedelta(minutes=20),date_created__gte=timezone.now()-timezone.timedelta(minutes=60))\
					|Q(state__name="FAILED",date_modified__lte=timezone.now()-timezone.timedelta(minutes=20),date_created__gte=timezone.now()-timezone.timedelta(minutes=60)))\
					.select_related('contact','template','state').all

			#orig_outbound = await outbound_query()
			orig_outbound = await sync_to_async(outbound_query, thread_sensitive=True)()

			lgr.info('Orig Outbound: %s' % orig_outbound)

			outbound = orig_outbound()[:limit_batch].values_list('id','recipient','contact__product__id','contact__product__notification__endpoint__batch','ext_outbound_id',\
                                                'contact__product__notification__ext_service_id','contact__product__notification__code__code','message','contact__product__notification__endpoint__account_id',\
                                                'contact__product__notification__endpoint__password','contact__product__notification__endpoint__username','contact__product__notification__endpoint__api_key',\
                                                'contact__subscription_details','contact__linkid','contact__product__notification__endpoint__url')

			lgr.info(f'1:Elapsed {elapsed}')
			lgr.info('Outbound: %s' % outbound)
			if len(outbound):
				messages=np.asarray(outbound)

				lgr.info(f'2:Elapsed {elapsed}')
				lgr.info('Messages: %s' % messages)

				##Update State
				#processing = orig_outbound().filter(id__in=messages[:,0].tolist()).update(state=OutBoundState.objects.get(name='PROCESSING'), date_modified=timezone.now(), sends=F('sends')+1)

				await sync_to_async(send_outbound_message)(messages)

	except Exception as e: lgr.error(f'Send Outbound Messages Error: {e}')



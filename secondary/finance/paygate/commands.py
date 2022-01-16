import faust
from faust.types import StreamT
#from primary.core.async.faust import app
from switch.faust_app import app as _faust
#from switch.spark import app as _spark
#import requests, json, ast
#from pyspark.sql.functions import *
#from pyspark.sql.types import *

from django.db import transaction
from .models import *
from django.db.models import Q,F
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from functools import reduce
from concurrent.futures import ThreadPoolExecutor
from switch.kafka_app import app as kafka_producer
from mode import Service

from primary.core.bridge.tasks import Wrappers as BridgeWrappers

from itertools import islice, chain
import pandas as pd
import numpy as np
import time
from asgiref.sync import sync_to_async
import asyncio
import random
import logging
import aiohttp
import datetime
from http.client import HTTPConnection	# py3
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
thread_pool = ThreadPoolExecutor(max_workers=16)

@_faust.command()
async def paygate_process_incoming_poller():
	"""This docstring is used as the command help in --help.
	This service does not process transactions and only does an insert to the background service activity table.
	"""
	lgr.info('Paygate Process Incoming Poller.........')
	def poll_query(status, last_run):
		return IncomingPoller.objects.select_for_update(of=('self',)).filter(
								status__name__in=status, 
								last_run__lte=last_run
								)
	while 1:
		try:
			lgr.info('Incoming Poller Running')

			s = time.perf_counter()
			elapsed = lambda: time.perf_counter() - s

			tasks = list()
			with transaction.atomic():

				lgr.info(f'1:Poll-Elapsed {elapsed()}')
				orig_poll = await sync_to_async(poll_query, thread_sensitive=True)(status=['ACTIVE'], 
								last_run=timezone.now() - timezone.timedelta(seconds=1)*F("frequency__run_every"))

				lgr.info(f'{elapsed()}-Orig Incoming Poll: {orig_poll}')

				for p in orig_poll:

					lgr.info(f'Incoming Poller: {p}')
					params = p.remittance_product.endpoint.request
					if params: params.update(p.request)
					else: params = p.request

					params['account_id'] = p.remittance_product.endpoint.account_id
					params['username'] = p.remittance_product.endpoint.username
					params['password'] = p.remittance_product.endpoint.password

					url = p.remittance_product.endpoint.url

					lgr.info(f'Params: {params}')

					async with _faust.http_client.post(url, data=json.dumps(params), headers={'Content-Type': 'application/json'}, timeout=30) as response:
						lgr.info("Status: %s" % response.status)
						#lgr.info("Content-type: %s" % response.headers['content-type'])
						params = await response.json()

						lgr.info(f'Response: {params}')
						if 'data' in params.get('response') and params['response'].get('data'):
							for payload in json.loads(params['response']['data']):
								lgr.info(f'Payload: {payload}')

								incoming = Incoming.objects.filter(remittance_product=p.remittance_product, reference=payload['reference'],\
												 ext_inbound_id=payload['ext_inbound_id'])

								if incoming.exists(): pass
								else: 
								    lgr.info('Not Found: Process BG')

								    bg = sync_to_async(BridgeWrappers().background_service_call, thread_sensitive=True)(p.service, p.gateway_profile, payload)
								    tasks.append(bg)

				lgr.info(f'2:Incoming Poll-Elapsed {elapsed()}')
				#orig_poll.update(status=PollStatus.objects.get(name='PROCESSING'))

				if tasks:
					response = await asyncio.gather(*tasks)

				#Update Last Run if exists
				if len(orig_poll): orig_poll.update(last_run=timezone.now())

				lgr.info(f'3:Incoming Poll-Elapsed {elapsed()}')

			await asyncio.sleep(1.0)

		except Exception as e: 
			lgr.error(f'Paygate Incoming Poller Error: {e}')


@_faust.command()
async def paygate_process_incoming():
	"""This docstring is used as the command help in --help.
	This service does not process transactions and only does an insert to the background service activity table.
	"""
	lgr.info('Paygate Incoming.........')
	def incoming_query(state, response):
		return Incoming.objects.select_for_update(of=('self',)).filter(state__name=state, response_status__response=response,
								    date_modified__lte=timezone.now()-timezone.timedelta(seconds=2))

	while 1:
		try:
			lgr.info('Paygate Incoming Running')

			s = time.perf_counter()
			elapsed = lambda: time.perf_counter() - s

			tasks = list()
			with transaction.atomic():

				lgr.info(f'1:Incoming-Elapsed {elapsed()}')
				orig_incoming = await sync_to_async(incoming_query, thread_sensitive=True)(state='CREATED', 
													    response='DEFAULT')

				lgr.info(f'{elapsed()}-Orig Incoming: {orig_incoming}')

				for i in orig_incoming:
					lgr.info(f'Incoming: {i}')
					gateway_institution_notification = i.remittance_product.gatewayinstitutionnotification
					payload = i.request

					payload['paygate_incoming_id'] = i.id
					payload['amount'] = str(i.amount)
					payload['reference'] = i.reference
					if i.currency is not None:
					    payload['currency'] = i.currency.code

					lgr.info('Started Processing Gateway Institution Notification: %s | %s' % (gateway_institution_notification, payload))
					notification_key_list = gateway_institution_notification.notification_service.notification_key.all().values_list('key', flat=True)

					entry_keys = list(set(payload.keys()).intersection(set(list(notification_key_list))))
					#missing_keys = list(set(notification_key_list).difference(set(list(payload.keys()))))

					params = gateway_institution_notification.notification_service.request if isinstance(gateway_institution_notification.notification_service.request, dict) else {}

					for entry in entry_keys:
						params[entry] = payload[entry]

					lgr.info(f'1.1:-Elapsed {elapsed()} - {params}')
					##for missing in missing_keys:
					##	params[missing] = ''
				       
					bg = sync_to_async(BridgeWrappers().background_service_call, thread_sensitive=True)(gateway_institution_notification.notification_service.service,
															    gateway_institution_notification.gateway_profile, params)

					tasks.append(bg)

				lgr.info(f'2:Incoming-Elapsed {elapsed()}')
				if tasks:
					response = await asyncio.gather(*tasks)
					orig_incoming.update(state=IncomingState.objects.get(name='PROCESSED'), response_status=ResponseStatus.objects.get(response='00'))
				lgr.info(f'3:Incoming-Elapsed {elapsed()}')

			await asyncio.sleep(1.0)

		except Exception as e: 
			lgr.error(f'Paygate Incoming Error: {e}')



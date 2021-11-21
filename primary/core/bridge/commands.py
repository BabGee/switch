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
from primary.core.api.views import ServiceCall

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
async def bridge_background_service_poll():
	"""This docstring is used as the command help in --help.
	This service does not process transactions and only does an insert to the background service activity table.
	"""
	lgr.info('Bridge Background Service Poll.........')
	def poll_query(status, last_run):
		return Poll.objects.select_for_update(of=('self',)).filter(
								status__name=status, 
								last_run__lte=last_run
								)
	while 1:
		try:
			lgr.info('Poll Running')

			s = time.perf_counter()
			elapsed = lambda: time.perf_counter() - s

			tasks = list()
			with transaction.atomic():

				lgr.info(f'1:Poll-Elapsed {elapsed()}')
				orig_poll = await sync_to_async(poll_query, thread_sensitive=True)(status='PROCESSED', 
								last_run=timezone.now() - timezone.timedelta(seconds=1)*F("frequency__run_every"))

				lgr.info(f'{elapsed()}-Orig Poll: {orig_poll}')

				for p in orig_poll:
					lgr.info(f'Poll: {p}')
					bg = sync_to_async(BridgeWrappers().background_service_call, thread_sensitive=True)(p.service, p.gateway_profile, p.request)
					tasks.append(bg)

				lgr.info(f'2:Poll-Elapsed {elapsed()}')
				#orig_poll.update(status=PollStatus.objects.get(name='PROCESSING'))
				if tasks:
					response = await asyncio.gather(*tasks)
					orig_poll.update(last_run=timezone.now())
				lgr.info(f'3:Poll-Elapsed {elapsed()}')

			await asyncio.sleep(1.0)

		except Exception as e: 
			lgr.error(f'Bridge Background Service Poll Error: {e}')
			break

def process_bridge_background_service_call(activity_id, status):
	try:
		i = BackgroundServiceActivity.objects.get(id=activity_id)
		#Always copy json field as it updates back on save if you don't e.g. float/Decimal type on amount below
		payload = i.request.copy()

		lgr.info('\n\n\n\n\t########\Pre-Request: %s\n\n' % payload)
		payload['chid'] = i.channel.id
		payload['ip_address'] = '127.0.0.1'
		payload['gateway_host'] = '127.0.0.1'
		if i.institution:
			payload['institution_id'] = i.institution.id
		if i.currency:
			payload['currency'] = i.currency.code
		if i.amount:
			#payload['amount'] = float(i.amount)
			payload['amount'] = i.amount

		service = i.service
		gateway_profile = i.gateway_profile

		if i.service.retry and i.sends > i.service.retry.max_retry:
			payload['trigger'] = 'last_send%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')

		payload = dict(map(lambda x:(str(x[0]).lower(),json.dumps(x[1]) if isinstance(x[1], dict) else str(x[1])), payload.items()))

		lgr.info('\n\n\n\n\t########\Request: %s\n\n' % payload)
		payload = ServiceCall().api_service_call(service, gateway_profile, payload)

		lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)

		i.transaction_reference = '%s,%s' % (i.transaction_reference, payload['transaction_reference']) if 'transaction_reference' in payload.keys() else i.transaction_reference
		i.current_command = ServiceCommand.objects.get(id=payload['action_id']) if 'action_id' in payload.keys() else None

		#if 'last_response' in payload.keys():i.message = BridgeWrappers().response_payload(payload['last_response'])[:3839]
		if 'last_response' in payload.keys():i.message = str(payload['last_response'])[:3839]

		if 'response_status' in payload.keys():
			i.status = TransactionStatus.objects.get(name='PROCESSED')
			i.response_status = ResponseStatus.objects.get(response=payload['response_status'])
		else:
			payload['response_status'] = '20'
			i.status = TransactionStatus.objects.get(name='FAILED')
			i.response_status = ResponseStatus.objects.get(response='20')

		#Set for failed retries in every 6 hours within 24 hours
		if payload['response_status'] != '00':
			if i.service.retry:
				#Update Service Cut-off to service from BG service
				try: servicecutoff = i.service.servicecutoff #Not working
				except ServiceCutOff.DoesNotExist: servicecutoff = None
				if servicecutoff and servicecutoff.cut_off_command and i.current_command and i.current_command.level > servicecutoff.cut_off_command.level:
					pass
				elif  i.sends > i.service.retry.max_retry:
					pass
				else:
					i.status = TransactionStatus.objects.get(name='CREATED')
					i.response_status = ResponseStatus.objects.get(response='DEFAULT')
					retry_in = (i.service.retry.max_retry_hours)/(i.service.retry.max_retry)
					i.scheduled_send = timezone.now()+timezone.timedelta(hours=float(retry_in))

		i.save()

	except Exception as e:
		lgr.info('Unable to process bridge background service call: %s' % e)


@_faust.command()
async def bridge_background_service():
	"""This docstring is used as the command help in --help.
	This service processes transactions in the background service activity table hence requires a threadpool
	"""
	lgr.info('Bridge Background Service.........')

	def background_query(response, status, scheduled_send):
		return BackgroundServiceActivity.objects.select_for_update(of=('self',)).filter(response_status__response=response,\
								status__name=status,
								scheduled_send__lte=scheduled_send,
								 date_created__date=timezone.now().date())
	while 1:
		try:
			lgr.info('Background Running')
			s = time.perf_counter()
			elapsed = lambda: time.perf_counter() - s

			tasks = list()
			with transaction.atomic():
			    lgr.info(f'1:Background-Elapsed {elapsed()}')
			    orig_background = await sync_to_async(background_query, thread_sensitive=True)(response='DEFAULT', status='CREATED', scheduled_send=timezone.now()) 
			    #orig_background = BackgroundServiceActivity.objects.select_for_update().filter(response_status__response='DEFAULT',\
			    #    									    status__name='CREATED', 
			    #    									    scheduled_send__lte=timezone.now())

			    lgr.info(f'{elapsed()}-Orig Background: {orig_background}')
			    background = list(orig_background.values_list('id',flat=True)[:100])

			    processing = orig_background.filter(id__in=background).update(status=TransactionStatus.objects.get(name='PROCESSING'), date_modified=timezone.now(), sends=F('sends')+1)
			    for b in background:
				    lgr.info(f'Background: {b}')
				    bg = _faust.loop.run_in_executor(thread_pool, process_bridge_background_service_call, *[b, True])
				    #bg = sync_to_async(process_bridge_background_service_call, thread_sensitive=True)(b, True)

				    tasks.append(bg)
			#End Atomic Transaction
			lgr.info(f'2:Background-Elapsed {elapsed()}')
			if tasks: response = await asyncio.gather(*tasks)

			lgr.info(f'3:Background-Elapsed {elapsed()}')
			await asyncio.sleep(1.0)
		except Exception as e: 
			lgr.error(f'Bridge Background Service: {e}')
			break


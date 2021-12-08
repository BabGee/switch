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
async def paygate_process_incoming():
	"""This docstring is used as the command help in --help.
	This service does not process transactions and only does an insert to the background service activity table.
	"""
	lgr.info('Paygate Incoming.........')
	def incoming_query(state, response):
		return Incoming.objects.select_for_update(of=('self',)).filter(state__name=state,
									response_status__response=response)

	while 1:
		try:
			lgr.info('Paygate Incoming Running')

			s = time.perf_counter()
			elapsed = lambda: time.perf_counter() - s

			tasks = list()
			with transaction.atomic():

				lgr.info(f'1:Incoming-Elapsed {elapsed()}')
				#orig_incoming = await sync_to_async(incoming_query, thread_sensitive=True)(state='CREATED', 
				#									    response='DEFAULT')
				orig_incoming = await sync_to_async(incoming_query, thread_sensitive=True)(state='PROCESSED', 
													    response='00')

				lgr.info(f'{elapsed()}-Orig Incoming: {orig_incoming}')

				for i in orig_incoming:
					lgr.info(f'Incoming: {i}')
					gateway_institution_notification = i.remittance_product.gatewayinstitutionnotification
					payload = i.request
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
				       
					#bg = sync_to_async(BridgeWrappers().background_service_call, thread_sensitive=True)(gateway_institution_notification.notification_service.service,
					#										    gateway_institution_notification.gateway_profile, params)

					#tasks.append(bg)

				lgr.info(f'2:Incoming-Elapsed {elapsed()}')
				if tasks:
					response = await asyncio.gather(*tasks)
					orig_incoming.update(state=IncomingState.objects.get(name='PROCESSED'), response_status=ResponseStatus.objects.get(response='00'))
				lgr.info(f'3:Incoming-Elapsed {elapsed()}')

			await asyncio.sleep(1.0)

		except Exception as e: 
			lgr.error(f'Paygate Incoming Error: {e}')
			break



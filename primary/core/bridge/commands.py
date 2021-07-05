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

@_faust.command()
async def session_subscription_whatsapp_reminder():
	"""This docstring is used as the command help in --help."""
	lgr.info('Session Subscription.........')
	def poll_query(status, last_run):
		return Poll.objects.select_for_update(of=('self',)).filter(
								status__name=status, 
								last_run__lte=last_run
								)
	while 1:
		try:
			print('Session Subscription Running')

			s = time.perf_counter()
			elapsed = lambda: time.perf_counter() - s

			tasks = list()
			with transaction.atomic():

				lgr.info(f'1:Elapsed {elapsed()}')
				orig_poll = await sync_to_async(poll_query, thread_sensitive=True)(status='PROCESSED', 
								last_run=timezone.now() - timezone.timedelta(seconds=1)*F("frequency__run_every"))

				lgr.info(f'{elapsed()}-Orig Poll: {orig_poll}')

				for p in orig_poll:
					lgr.info(f'Poll: {p}')
					bg = sync_to_async(BridgeWrappers().background_service_call, thread_sensitive=True)(p.service, p.gateway_profile, p.request)
					tasks.append(bg)

				lgr.info(f'2:Elapsed {elapsed()}')
				#orig_poll.update(status=PollStatus.objects.get(name='PROCESSING'))
				if tasks:
					response = await asyncio.gather(*tasks)
					orig_poll.update(last_run=timezone.now())
				lgr.info(f'3:Elapsed {elapsed()}')
			break

			await asyncio.sleep(1.0)

		except Exception as e: 
			lgr.error(f'Session Subscription Error: {e}')
			break


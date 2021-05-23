import faust
from faust.types import StreamT
#from primary.core.async.faust import app
from switch.faust import app
import requests, json, ast


from django.db import transaction
from .models import *
from django.db.models import Q,F
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from functools import reduce
from concurrent.futures import ThreadPoolExecutor
from switch.kafka import app as kafka_producer
from mode import Service

from itertools import islice, chain
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

sent_messages_topic = app.topic('switch.secondary.channels.notify.sent_messages')
delivery_status_topic = app.topic('switch.secondary.channels.notify.delivery_status')

@app.agent(sent_messages_topic, concurrency=1)
async def sent_messages(messages):
	async for message in messages.take(30, within=1):
		try:
			s = time.perf_counter()
			
			elapsed = lambda: time.perf_counter() - s

			lgr.info(f'RECEIVED Sent Messages {len(message)}: {message}')
			df = await sync_to_async(pd.DataFrame)(message)

			outbound_list = []
			for r in zip(*df.to_dict("list").values()):
				batch_id, outbound_id, recipient, response_state, response_code = r
				#lgr.info(f'Batch ID {batch_id} | Outbound ID {outbound_id} | Recipient {recipient} | Response State {response_state} | Response Code {response_code}')
				try:
					outbound = await sync_to_async(Outbound.objects.get)(id=outbound_id)
					outbound.state = await sync_to_async(OutBoundState.objects.get)(name=response_state)
					outbound.response = response_code
					outbound.batch_id = batch_id
					outbound_list.append(outbound)
				except ObjectDoesNotExist: pass

			lgr.info(f'{elapsed()} Sent Messages Outbound List {len(outbound_list)}')
			await sync_to_async(Outbound.objects.bulk_update, thread_sensitive=True)(outbound_list, ['state','response','batch_id'])
			lgr.info(f'{elapsed()} Sent Messages Updated')
			await asyncio.sleep(2.0)
		except Exception as e: lgr.info(f'Error on Sent Messages: {e}')

@app.agent(delivery_status_topic, concurrency=1)
async def delivery_status(messages):
	async for message in messages.take(30, within=5):
		try:
			s = time.perf_counter()
			
			elapsed = lambda: time.perf_counter() - s

			lgr.info(f'RECEIVED Delivery Status {len(message)}: {message}')
			df = await sync_to_async(pd.DataFrame)(message)

			outbound_list = []
			for r in zip(*df.to_dict("list").values()):
				batch_id, recipient, response_state, response_code = r
				#lgr.info(f'Batch ID {batch_id} | Recipient {recipient} | Response State {response_state} | Response Code {response_code}')
				try:
					outbound = await sync_to_async(Outbound.objects.get)(batch_id=batch_id)
					outbound.state = await sync_to_async(OutBoundState.objects.get)(name=response_state)
					outbound.response = response_code
					outbound_list.append(outbound)
				except MultipleObjectsReturned:
					async def _update(response_state, response_code):
						state = await sync_to_async(OutBoundState.objects.get)(name=response_state)
						return sync_to_async(Outbound.objects.filter(batch_id=batch_id).\
							update)(state=state, response=response_code)

					outbound = await _update(response_state=response_state, response_code=response_code)
					lgr.info(f'{elapsed()} Delivery Status Outbound {outbound}')
				except ObjectDoesNotExist: pass


			lgr.info(f'{elapsed()} Delivery Status Outbound List {len(outbound_list)}')
			await sync_to_async(Outbound.objects.bulk_update, thread_sensitive=True)(outbound_list, ['state','response'])
			lgr.info(f'{elapsed()} Delivery Status Updated')
			await asyncio.sleep(10.0)
		except Exception as e: lgr.info(f'Error on Delivery Status: {e}')



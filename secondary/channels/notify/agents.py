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

##thread_pool = ThreadPoolExecutor(max_workers=16) #Heavy on database
#thread_pool = ThreadPoolExecutor(max_workers=1)

@app.agent(sent_messages_topic, concurrency=16)
async def sent_messages(messages):
	async for message in messages.take(15, within=1):
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

		except Exception as e: lgr.info(f'Error on Sent Messages: {e}')

@app.agent(delivery_status_topic, concurrency=16)
async def delivery_status(messages):
	async for message in messages.take(15, within=10):
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

		except Exception as e: lgr.info(f'Error on Delivery Status: {e}')

#@app.service
#class NotificationService(Service):
#	async def on_start(self):
#		print('NOTIFICATION SERVICEIS STARTING')
#
#	async def on_stop(self):
#		print('NOTIFICATION SERVICE IS STOPPING')
#
#	@Service.task
#	async def _notification(self):
#		while not self.should_stop:
#			print('NOTIFICATION SERVICE RUNNING')
#			try:
#				self.loop.run_in_executor(thread_pool, _send_outbound_messages, *[False, 60])
#				#await send_outbound_messages(is_bulk=False, limit_batch=60)
#			except Exception as e: lgr.error(f'Non-Bulk Send Outbound Messages Error: {e}')
#			await self.sleep(4.0)
#
#	@Service.task
#	async def _bulk_notification(self):
#		while not self.should_stop:
#			print('BULK NOTIFICATION SERVICE RUNNING')
#			try:
#				self.loop.run_in_executor(thread_pool, _send_outbound_messages, *[True, 240])
#				#await send_outbound_messages(is_bulk=True, limit_batch=240)
#			except Exception as e: lgr.error(f'Bulk Send Outbound Messages Error: {e}')
#			await self.sleep(4.0)



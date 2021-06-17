import faust
from faust.types import StreamT
#from primary.core.async.faust import app
from switch.faust import app as _faust
from cassandra.cqlengine.connection import session as _cassandra
import requests, json, ast
from aiocassandra import aiosession
import dateutil.parser

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

sent_messages_topic = _faust.topic('switch.secondary.channels.notify.sent_messages')
#delivery_status_topic = _faust.topic('switch.secondary.channels.notify.delivery_status')

thread_pool = ThreadPoolExecutor(max_workers=4)
#Cassandra Async Patching
session = _cassandra
aiosession(session)

@_faust.agent(sent_messages_topic, concurrency=1)
async def sent_messages(messages):
	#async for message in messages.take(1000, within=1):
	async for message in messages:
		try:
			s = time.perf_counter()
			elapsed = lambda: time.perf_counter() - s
			lgr.info(f'RECEIVED Sent Message {message}')

			timestamp = dateutil.parser.parse(message['timestamp'])
			date_created = timestamp.date()
			query = """INSERT INTO switch.notify_outbound (product_id, outbound_id, batch_id, 
				channel, code, date_created, date_modified, message, mno, recipient, response, state) 
				VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
			prepared_query = await session.prepare_future(query)
			bound = prepared_query.bind(dict(product_id=int(message['product_id']), outbound_id=int(message['outbound_id']), 
				batch_id=message['batch_id'], channel=message['channel'], code=message['code'], date_created=date_created, 
				date_modified=timestamp, message=message['message'], mno=message.get('mno'), 
				recipient=message['recipient'], response=message['response_code'], state=message['response_state']))
			lgr.info(f'Sent Message Query {bound}')
			result = await session.execute_future(bound)
			lgr.info(f'Sent Message Result {result}')
			lgr.info(f'{elapsed()} Sent Message Task Completed')
			#await asyncio.sleep(0.5)
		except Exception as e: lgr.info(f'Error on Sent Messages: {e}')

#@_faust.agent(delivery_status_topic, concurrency=1)
#async def delivery_status(messages):
#	#async for message in messages.take(1000, within=5):
#	async for message in messages:
#		try:
#			s = time.perf_counter()
#			elapsed = lambda: time.perf_counter() - s
#			lgr.info(f'RECEIVED Delivery Status {message}')
#			#timestamp = dateutil.parser.parse(message['timestamp'])
#			#query = """UPDATE notify.send_notification SET  state=?, response=?, date_modified=? where product_id=? and outbound_id=?;"""
#			#prepared_query = await session.prepare_future(query)
#			#bound = prepared_query.bind((message['response_state'], message['response_code'], timestamp,  int(message['product_id']), int(message['outbound_id']),))
#			#lgr.info(f'Delivery StatusQuery {bound}')
#			#prepared_query = await session.prepare_future(query)
#			#lgr.info(f'Delivery Status Query {prepared_query}')
#			#result = await session.execute_future(bound)
#			#lgr.info(f'Delivery Status Result {result}')
#			lgr.info(f'{elapsed()} Delivery Status Updated')
#			#await asyncio.sleep(0.5)
#		except Exception as e: lgr.info(f'Error on Delivery Status: {e}')



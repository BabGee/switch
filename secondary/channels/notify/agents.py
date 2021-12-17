import faust
from faust.types import StreamT
#from primary.core.async.faust import app
from switch.faust_app import app as _faust
import requests, json, ast
from aiocassandra import aiosession
import dateutil.parser

from django.db import transaction
from .models import *
from django.db.models import Q,F
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from functools import reduce
from switch.kafka_app import app as kafka_producer
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

add_recipient_topic = _faust.topic('switch.secondary.channels.notify.add_recipient')
sent_messages_topic = _faust.topic('switch.secondary.channels.notify.sent_messages')
delivery_status_topic = _faust.topic('switch.secondary.channels.notify.delivery_status')

#Session required within task 
from cassandra.cqlengine.connection import session
#Cassandra Async Patching
aiosession(session)

@_faust.agent(add_recipient_topic, concurrency=16)
async def add_recipient(messages):
	async for message in messages:
		try:
			s = time.perf_counter()
			elapsed = lambda: time.perf_counter() - s
			lgr.info(f'RECEIVED Recipient {message}')

			#timestamp = dateutil.parser.parse(message['timestamp'])
			#date_created = timestamp.date()
			#query = """INSERT INTO switch.notify_recipient (product_id, outbound_id, batch_id, 
			#	channel, code, date_created, date_modified, message, mno, recipient, response, state) 
			#	VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
			#prepared_query = await session.prepare_future(query)
			#bound = prepared_query.bind(dict(product_id=int(message['product_id']), outbound_id=int(message['outbound_id']), 
			#	batch_id=message['batch_id'], channel=message['channel'], code=message['code'], date_created=date_created, 
			#	date_modified=timestamp, message=message['message'], mno=message.get('mno'), 
			#	recipient=message['recipient'], response=message['response_code'], state=message['response_state']))
			#lgr.info(f'Sent Message Query {bound}')
			#result = await session.execute_future(bound)
			lgr.info(f'Add Recipient Result {result}')
			lgr.info(f'{elapsed()} Add Recipient Task Completed')
			#await asyncio.sleep(0.5)
		except Exception as e: lgr.info(f'Error on Add Recipient: {e}')


@_faust.agent(sent_messages_topic, concurrency=16)
async def sent_messages(messages):

	#async for message in messages.take(1000, within=1):
	async for message in messages:
		try:
			s = time.perf_counter()
			elapsed = lambda: time.perf_counter() - s
			lgr.info(f'RECEIVED Sent Message {message}')

			timestamp = dateutil.parser.parse(message['timestamp'])
			#date_created = timestamp.date()
			#query = """INSERT INTO switch.notify_outbound (product_id, outbound_id, batch_id, 
			#	channel, code, date_created, date_modified, message, mno, recipient, response, state) 
			#	VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
			#prepared_query = await session.prepare_future(query)
			#bound = prepared_query.bind(dict(product_id=int(message['product_id']), outbound_id=int(message['outbound_id']), 
			#	batch_id=message['batch_id'], channel=message['channel'], code=message['code'], date_created=date_created, 
			#	date_modified=timestamp, message=message['message'], mno=message.get('mno'), 
			#	recipient=message['recipient'], response=message['response_code'], state=message['response_state']))
			#lgr.info(f'Sent Message Query {bound}')
			#result = await session.execute_future(bound)

			def outbound_sent_insert(message):
			    outbound_sent = OutboundSent()
			    outbound_sent.timestamp = timestamp
			    outbound_sent.batch_id = message['batch_id']

			    #outbound_sent.outbound_id = message['outbound_id']
			    outbound = Outbound.objects.filter(id=message['outbound_id'])
			    outbound_sent.outbound = outbound.last() if len(outbound) else None

			    outbound_sent.recipient = message['recipient']
			    outbound_sent.state = OutBoundState.objects.get(name=message['response_state'])
			    outbound_sent.response = message['response_code']
			    outbound_sent.product_id = message['product_id']
			    outbound_sent.message = message['message']

			    return outbound_sent.save()

			result = await sync_to_async(outbound_sent_insert, thread_sensitive=True)(message)

			lgr.info(f'Sent Message Result {result}')
			lgr.info(f'{elapsed()} Sent Message Task Completed')
			#await asyncio.sleep(0.5)
		except Exception as e: lgr.info(f'Error on Sent Messages: {e}')

@_faust.agent(delivery_status_topic, concurrency=1)
async def delivery_status(messages):
	#async for message in messages.take(1000, within=5):
	async for message in messages:
		try:
			s = time.perf_counter()
			elapsed = lambda: time.perf_counter() - s
			lgr.info(f'RECEIVED Delivery Status {message}')
			timestamp = dateutil.parser.parse(message['timestamp'])
			#query = """UPDATE notify.send_notification SET  state=?, response=?, date_modified=? where product_id=? and outbound_id=?;"""
			#prepared_query = await session.prepare_future(query)
			#bound = prepared_query.bind((message['response_state'], message['response_code'], timestamp,  int(message['product_id']), int(message['outbound_id']),))
			#lgr.info(f'Delivery StatusQuery {bound}')
			#prepared_query = await session.prepare_future(query)
			#lgr.info(f'Delivery Status Query {prepared_query}')
			#result = await session.execute_future(bound)
			def outbound_sent_delivered_insert(message):
			    outbound_sent_delivered = OutboundSentDelivered()
			    outbound_sent_delivered.timestamp = timestamp
			    outbound_sent_delivered.batch_id = message['batch_id']

			    outbound_sent = OutboundSent.objects.filter(batch_id=message['batch_id'])
			    outbound_sent_delivered.outbound_sent = outbound_sent.last() if len(outbound_sent) else None

			    outbound_sent_delivered.recipient = message['recipient']
			    outbound_sent_delivered.state = OutBoundState.objects.get(name=message['response_state'])
			    outbound_sent_delivered.response = message['response_code']

			    return outbound_sent_delivered.save()

			result = await sync_to_async(outbound_sent_delivered_insert, thread_sensitive=True)(message)


			lgr.info(f'Delivery Status Result {result}')
			lgr.info(f'{elapsed()} Delivery Status Updated')
			#await asyncio.sleep(0.5)
		except Exception as e: lgr.info(f'Error on Delivery Status: {e}')



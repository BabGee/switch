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

thread_pool = ThreadPoolExecutor(max_workers=4)

@app.agent(sent_messages_topic, concurrency=1)
async def sent_messages(messages):
	async for message in messages.take(60, within=1):
		try:
			s = time.perf_counter()
			elapsed = lambda: time.perf_counter() - s
			lgr.info(f'RECEIVED Sent Messages {len(message)}')
			lgr.info(f'Sent Messages {message}')
			lgr.info(f'{elapsed()} Sent Message Task Completed')
			await asyncio.sleep(0.5)
		except Exception as e: lgr.info(f'Error on Sent Messages: {e}')

#@app.agent(delivery_status_topic, concurrency=1)
#async def delivery_status(messages):
#	async for message in messages.take(60, within=5):
#		try:
#			s = time.perf_counter()
#			elapsed = lambda: time.perf_counter() - s
#
#			lgr.info(f'RECEIVED Delivery Status {len(message)}')
#			lgr.info(f'{elapsed()} Delivery Status Updated')
#			await asyncio.sleep(0.5)
#		except Exception as e: lgr.info(f'Error on Delivery Status: {e}')



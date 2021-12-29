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
from mode import Service

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

service_topic = _faust.topic('switch.primary.core.upc.api.service')

#@_faust.agent(service_topic)
#async def service(messages):
#    async for message in messages:
#        try:
#            s = time.perf_counter()
#            elapsed = lambda: time.perf_counter() - s
#
#            lgr.info(f'RECEIVED Service Request {message}')
#            lgr.info(f'{elapsed()} Service Call Task Completed')
#        except Exception as e: lgr.info(f'Error on Service Call: {e}')


@_faust.agent(service_topic)
async def service(stream):
    async for event in stream.events():
        try:
            s = time.perf_counter()
            elapsed = lambda: time.perf_counter() - s
            lgr.info(f'RECEIVED Service Call {event}')
            key = event.key
            value = event.value
            offset = event.message.offset
            headers = event.headers
            lgr.info(f'Key: {key} | Value: {value} | Offset {offset} | Headers: {headers}')
            lgr.info(f'{elapsed()} Service Call Task Completed')
        except Exception as e: lgr.info(f'Error on Service Call: {e}')


#@_faust.agent(service_call_topic, concurrency=16)
#async def service_call(messages):
#	async for message in messages:
#		try:
#			s = time.perf_counter()
#			elapsed = lambda: time.perf_counter() - s
#			lgr.info(f'RECEIVED Service Call {message}')
#                        params = dict()
#                        gateway_profile 
#                        service = message['SERVICE']
#        		payload = await sync_to_async(ServiceCall().api_service_call, 
#                                                                thread_sensitive=True)(service, gateway_profile, params)
#
#			lgr.info(f'Service Call Result {payload}')
#			lgr.info(f'{elapsed()} Service Call Task Completed')
#			#await asyncio.sleep(0.5)
#		except Exception as e: lgr.info(f'Error on Service Call: {e}')



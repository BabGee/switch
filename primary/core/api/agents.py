import faust
from faust.types import StreamT
#from primary.core.async.faust import app
from switch.faust import app
import requests, json
from .views import Interface
from .models import *
from django.test import RequestFactory

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
lgr.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s-%(name)s %(funcName)s %(process)d %(thread)d-(%(threadName)-2s) %(levelname)s-%(message)s')
ch.setFormatter(formatter)

lgr.addHandler(ch)

HTTPConnection.debuglevel = 1

s = time.perf_counter()


class Greeting(faust.Record):
    from_name: str
    to_name: str
    count: float
    records: int


topic = app.topic('switch-hello-topic', value_type=Greeting)

@app.agent(topic)
async def hello(greetings):
	async for greeting in greetings:
		lgr.info(f'Hello from {greeting.from_name} to {greeting.to_name} | Count {greeting.count} | Records {greeting.records}')

#@app.task
#@app.timer(interval=0.25)
@app.timer(interval=10)
async def example_sender_task(app):
    count = time.perf_counter() - s
    elapsed = "{0:.2f}".format(count)
    records = random.randint(1,1000) 
    await hello.send(
        value=Greeting(from_name='Switch API Task', to_name='you', count=float(elapsed), records=records),
    )
    count+=1


#request_factory = RequestFactory(**{"SERVER_NAME": "localhost", "wsgi.url_scheme":"https"}).
request_factory = RequestFactory(**{"SERVER_NAME": "localhost"})


class _Interface(faust.Record):
    payload: dict 
    service_name: str


class TransformedInterface(faust.Record):
    request: dict 
    service_name: str
    response: dict

api_topic = app.topic('primary.core.upc.api.interface', value_type=_Interface)

transformed_api_topic = app.topic('primary.core.upc.api.transformedinterface', value_type=TransformedInterface)


@app.agent(api_topic)
async def _interface(_requests):
	async for _request in _requests:
		request = await sync_to_async(request_factory.post, thread_sensitive=False)(f'/api/{_request.service_name}/', json.dumps(_request.payload), content_type='application/json')
		lgr.info('Response: %s' % request)
		response = await sync_to_async(Interface().interface, thread_sensitive=False)(request, _request.service_name)
		lgr.info('Response: %s' % response)
		transformed = TransformedInterface(
					    request=_request.payload,
					    service_name=_request.service_name,
					    response=response.content
					    #response=json.loads(response.content)
					)

		await transformed_api_topic.send(value=transformed)   
		lgr.info(f'Interface Request: {_request.service_name}')



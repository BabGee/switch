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
		request = await sync_to_async(request_factory.post)(f'/api/{_request.service_name}/', json.dumps(_request.payload), content_type='application/json')
		response = await sync_to_async(Interface().interface)(request, _request.service_name)
		transformed = TransformedInterface(
					    request=_request.payload,
					    service_name=_request.service_name,
					    response=response.content
					    #response=json.loads(response.content)
					)

		await transformed_api_topic.send(value=transformed)   
		#lgr.info(f'Interface Request: {_request.service_name}')



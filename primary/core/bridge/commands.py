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

#thread_pool = ThreadPoolExecutor(max_workers=16) #Heavy on database
thread_pool = ThreadPoolExecutor(max_workers=16)



@_faust.command()
async def session_subscription_whatsapp_reminder():
	"""This docstring is used as the command help in --help."""
	lgr.info('Session Subscription.........')
	while 1:
		try:
			print('Session Subscription Running')
			tasks = list()

			#Query for Session Subscription after the 22nd hour
			#Insert into Background Service Subscription Check every 30 minutes

			#Run Tasks
			if tasks:
				response = await asyncio.gather(*tasks)
				#Control Speeds

			await asyncio.sleep(1.0)
		except Exception as e: 
			lgr.error(f'Session Subscription Error: {e}')
			break


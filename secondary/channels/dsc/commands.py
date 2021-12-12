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

@_faust.command()
async def dsc_file_upload():
	"""This docstring is used as the command help in --help."""
	lgr.info('File Upload.........')
	def upload_query(status):
		return FileUploadActivity.objects.select_for_update(of=('self',)).filter(Q(status__name=status),
							~Q(file_upload__activity_service=None))
	while 1:
		try:
			lgr.info('File Upload Running')
			s = time.perf_counter()
			elapsed = lambda: time.perf_counter() - s
			tasks = list()
			with transaction.atomic():
				lgr.info(f'1:File Upload-Elapsed {elapsed()}')
				orig_file_upload = await sync_to_async(upload_query, thread_sensitive=True)(status='CREATED')
				lgr.info(f'{elapsed()}-Orig File Upload: {orig_file_upload}')
				for f in orig_file_upload:
				    lgr.info(f'File Upload: {f}')
				    fu = sync_to_async(BridgeWrappers().background_service_call, thread_sensitive=True)(f.file_upload.activity_service, f.gateway_profile, f.details)

				    tasks.append(fu)
				#Mark Activities as processed
				orig_file_upload.update(status=FileUploadActivityStatus.objects.get(name='PROCESSED'))
			#End Atomic Transaction
			lgr.info(f'2:File Upload-Elapsed {elapsed()}')
			if tasks: response = await asyncio.gather(*tasks)
			lgr.info(f'3:File Upload-Elapsed {elapsed()}')
			await asyncio.sleep(1.0)
		except Exception as e: 
			lgr.error(f'File Upload Error: {e}')
			break


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

#thread_pool = ThreadPoolExecutor(max_workers=16) #Heavy on database
thread_pool = ThreadPoolExecutor(max_workers=16)

def _send_outbound_messages(is_bulk=True, limit_batch=100):
	try:

		s = time.perf_counter()
		elapsed = lambda: time.perf_counter() - s
		with transaction.atomic():
			#.order_by('contact__product__priority').select_related('contact','template','state').all
			#|Q(state__name="PROCESSING",date_modified__lte=timezone.now()-timezone.timedelta(minutes=20),date_created__gte=timezone.now()-timezone.timedelta(minutes=60))\
			orig_outbound = Outbound.objects.select_for_update(of=('self',)).filter(Q(contact__subscribed=True),Q(contact__product__notification__code__channel__name='SMS'),~Q(recipient=None),
					Q(contact__status__name='ACTIVE',contact__product__is_bulk=is_bulk),
					Q(Q(contact__product__trading_box=None)|Q(contact__product__trading_box__open_time__lte=timezone.localtime().time(),
					contact__product__trading_box__close_time__gte=timezone.localtime().time())),
					Q(scheduled_send__lte=timezone.now(),state__name='CREATED',date_created__gte=timezone.now()-timezone.timedelta(hours=24))\
					|Q(state__name="FAILED",date_modified__lte=timezone.now()-timezone.timedelta(minutes=20),date_created__gte=timezone.now()-timezone.timedelta(minutes=60)))\
					.select_related('contact','template','state')

			#lgr.info('Orig Outbound: %s' % orig_outbound)

			outbound = orig_outbound[:limit_batch].values_list('id','recipient','contact__product__id','contact__product__notification__endpoint__batch','ext_outbound_id',
                                                'contact__product__notification__ext_service_id','contact__product__notification__code__code','message','contact__product__notification__endpoint__account_id',
                                                'contact__product__notification__endpoint__password','contact__product__notification__endpoint__username','contact__product__notification__endpoint__api_key',
                                                'contact__subscription_details','contact__linkid','contact__product__notification__endpoint__url','contact__product__notification__endpoint__request',
						'contact__product__notification__code__channel__name')

			lgr.info(f'1:Elapsed {elapsed()}')
			#lgr.info('Outbound: %s' % outbound)
			if len(outbound):
				messages=np.asarray(outbound)
				lgr.info(f'2:Elapsed {elapsed()}')
				#lgr.info('Messages: %s' % messages)

				##Update State
				processing = orig_outbound.filter(id__in=messages[:,0].tolist()).update(state=OutBoundState.objects.get(name='PROCESSING'), date_modified=timezone.now(), sends=F('sends')+1)

				df = pd.DataFrame({'outbound_id':messages[:,0], 'recipient':messages[:,1], 'product_id':messages[:,2], 'batch':messages[:,3], 'ext_service_id':messages[:,5],'code':messages[:,6],\
					'message':messages[:,7],'endpoint_account_id':messages[:,8],'endpoint_password':messages[:,9],'endpoint_username':messages[:,10],\
					'endpoint_api_key':messages[:,11],'linkid':messages[:,13],'endpoint_url':messages[:,14], 'channel':messages[:,16]})

				lgr.info(f'3:Elapsed {elapsed()}')
				#lgr.info('DF: %s' % df)
				df['batch'] = pd.to_numeric(df['batch'])
				df = df.dropna(axis='columns',how='all')

				#lgr.info(f'DF 0 {df}')

				#if 'endpoint_request' in df.columns: 
				#	#df['endpoint_request'] = df['endpoint_request'].to_json()
				#	df['endpoint_request'] = pd.json_normalize(df['endpoint_request'])
				#	##df['endpoint_request'] = df['endpoint_request'].astype(str)
				#	##if not df['endpoint_request'].empty:
				#	#df['endpoint_request']= df['endpoint_request'].fillna({i: {} for i in df.index})
				#	##df['endpoint_request'] = df['endpoint_request'].apply(ast.literal_eval)
				#	#lgr.info(f'DF 1 {df}')
				#	#df = df.join(pd.json_normalize(df['endpoint_request']))
				#	#lgr.info(f'DF 2 {df}')
				#	#df.drop(columns=['endpoint_request'], inplace=True)

				#lgr.info(f'DF 3 {df}')
				cols = df.columns.tolist()
				#df.set_index(cols, inplace=True)
				#df = df.sort_index()
				cols.remove('outbound_id')
				cols.remove('recipient')
				grouped_df = df.groupby(cols)
				#lgr.info('Grouped DF: %s' % grouped_df)


				tasks = []
				for name,group_df in grouped_df:
					batch_size = group_df['batch'].unique()[0]
					outbound_id_list = group_df['outbound_id'].tolist()
					recipient_list = group_df['recipient'].tolist()
					recipients = tuple(zip(outbound_id_list, recipient_list))
					payload = dict()    
					for c in cols: payload[c] = str(group_df[c].unique()[0])
					#lgr.info('MULTI: %s \n %s' % (group_df.shape,group_df.head()))
					if batch_size>1 and len(group_df.shape)>1 and group_df.shape[0]>1:
						objs = recipients
						lgr.info(f'Got Here (multi): {len(objs)}')
						start = 0
						while True:
							batch = list(islice(objs, start, start+batch_size))
							start+=batch_size
							if not batch: break
							payload['recipients'] = batch
							#lgr.info(f'{elapsed()} Producer Payload: {payload}')
							kafka_producer.publish_message(
									payload['endpoint_url'], 
									None, json.dumps(payload) 
									)

					elif len(group_df.shape)>1 :
						lgr.info(f'Got Here (list of singles): {len(recipients)}')
						for d in recipients:
							payload['recipients'] = [d]       
							#lgr.info(f'{elapsed()} Producer Payload: {payload}')
							kafka_producer.publish_message(
									payload['endpoint_url'], 
									None, json.dumps(payload) 
									)
					else:
						lgr.info(f'Got Here (single): {recipients}')
						payload['recipients'] = recipients
						#lgr.info(f'{elapsed()} Producer Payload: {payload}')
						kafka_producer.publish_message(
								payload['endpoint_url'], 
								None, json.dumps(payload) 
								)
					#Control Speeds

					lgr.info(f'4:Elapsed {elapsed()} Producer Sent')
					lgr.info(f'Sent Message to topic {payload["endpoint_url"]}')

				lgr.info(f'5:Elapsed {elapsed()} Sent Outbound Message')

	except Exception as e: lgr.error(f'Send Outbound Messages Error: {e}')



@app.command()
async def notify_notifications():
	"""This docstring is used as the command help in --help."""
	lgr.info('NOTIFICATION SERVICE STARTING.........')
	while 1:
		try:
			print('NOTIFICATION SERVICE RUNNING')
			tasks = list()
			#Transactional Notification
			notification = app.loop.run_in_executor(thread_pool, _send_outbound_messages, *[False, 240])
			tasks.append(notification)
			#Bulk Notification
			bulk_notification = app.loop.run_in_executor(thread_pool, _send_outbound_messages, *[True, 960])
			tasks.append(bulk_notification)
			#Run Tasks
			response = await asyncio.gather(*tasks)
			#Control Speeds
			await asyncio.sleep(1.0)
		except Exception as e: 
			lgr.error(f'NOTIFICATION SERVICE ERROR: {e}')
			break

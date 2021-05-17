import faust
from faust.types import StreamT
#from primary.core.async.faust import app
from switch.faust import app
import requests, json, ast


from django.db import transaction
from .models import *
from django.db.models import Q,F

from itertools import islice
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

sent_message_log_topic = app.topic('switch.secondary.channels.notify.sent_messages_log')
delivery_status_log_topic = app.topic('switch.secondary.channels.notify.delivery_status_log')

@app.agent(sent_message_log_topic)
async def sent_messages(messages):
	try:
		async for message in messages.take(300, within=10):
			s = time.perf_counter()
			
			elapsed = lambda: time.perf_counter() - s

			lgr.info(f'RECEIVED Sent Notification {len(message)}: {message}')
			message = np.asarray(message)
			message_id = message[:,0]
			message_status = message[:,1]
			message_response = message[:,2]

			def update_sent_outbound(outbound_id, outbound_state, response):
				outbound = Outbound.objects.get(id=outbound_id)
				outbound.state = OutBoundState.objects.get(name=outbound_state)
				outbound.response = response
				return outbound

			outbound_list = np.vectorize(update_sent_outbound)(outbound_id=message_id, outbound_state=message_status, response=message_response).tolist()
			Outbound.objects.bulk_update(outbound_list, ['state','response'])
			lgr.info(f'{elapsed()} Sent Messages Updated')

	except Exception as e: lgr.info(f'Error on Sent Notification: {e}')

@app.agent(delivery_status_log_topic)
async def delivery_status(messages):
	try:
		async for message in messages.take(300, within=10):
			s = time.perf_counter()

			elapsed = lambda: time.perf_counter() - s

			lgr.info(f'RECEIVED Delivery Status {len(message)}: {message}')

			message = np.asarray(message)
			message_id = message[:,0]
			message_status = message[:,1]
			message_response = message[:,2]

			def update_sent_outbound(outbound_id, outbound_state, response):
				outbound = Outbound.objects.get(id=outbound_id)
				outbound.state = OutBoundState.objects.get(name=outbound_state)
				outbound.response = response
				return outbound

			outbound_list = np.vectorize(update_sent_outbound)(outbound_id=message_id, outbound_state=message_status, response=message_response).tolist()
			Outbound.objects.bulk_update(outbound_list, ['state','response'])
			lgr.info(f'{elapsed()} Delivery Status Updated')

	except Exception as e: lgr.info(f'Error on Delivery Status: {e}')

async def send_outbound_message(messages):
	try:
		s = time.perf_counter()

		elapsed = lambda: time.perf_counter() - s
	
		df = pd.DataFrame({'outbound_id':messages[:,0], 'recipient':messages[:,1], 'product_id':messages[:,2], 'batch':messages[:,3],'ext_outbound_id':messages[:,4],'ext_service_id':messages[:,5],'code':messages[:,6],\
			'message':messages[:,7],'endpoint_account_id':messages[:,8],'endpoint_password':messages[:,9],'endpoint_username':messages[:,10],\
			'endpoint_api_key':messages[:,11],'subscription_details':messages[:,12],'linkid':messages[:,13],'endpoint_url':messages[:,14], 'endpoint_request':messages[:,15], 'channel':messages[:,16]})

		lgr.info(f'3:Elapsed {elapsed()}')
		lgr.info('DF: %s' % df)
		df['batch'] = pd.to_numeric(df['batch'])

		#if 'endpoint_request' in df.columns:
		#df['endpoint_request'] = df['endpoint_request'].to_json(orient="records")

		df['endpoint_request']= df['endpoint_request'].fillna({i: {} for i in df.index})
		df['endpoint_request'] = df['endpoint_request'].apply(ast.literal_eval)
		df = df.join(pd.json_normalize(df['endpoint_request']))
		df.drop(columns=['endpoint_request'], inplace=True)

		df = df.dropna(axis='columns',how='all')
		cols = df.columns.tolist()
		#df.set_index(cols, inplace=True)
		#df = df.sort_index()
		cols.remove('outbound_id')
		cols.remove('recipient')
		grouped_df = df.groupby(cols)
		lgr.info('Grouped DF: %s' % grouped_df)


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
				lgr.info(f'Got Here (multi): {objs}')
				start = 0
				while True:
					batch = list(islice(objs, start, start+batch_size))
					start+=batch_size
					if not batch: break
					payload['recipients'] = batch
					lgr.info(payload)
					await app.topic(payload['endpoint_url']).send(value=payload)
			elif len(group_df.shape)>1 :
				lgr.info(f'Got Here (list of singles): {recipients}')
				for d in recipients:
					payload['recipients'] = [d]       
					lgr.info(payload)
					await app.topic(payload['endpoint_url']).send(value=payload)
			else:
				lgr.info(f'Got Here (single): {recipients}')
				payload['recipients'] = recipients
				lgr.info(payload)
				await app.topic(payload['endpoint_url']).send(value=payload)

			#Control Speeds
			#await asyncio.sleep(0.10)
			lgr.info(f'4:Elapsed {elapsed()}')
			lgr.info(f'Sent Message to topic {payload["endpoint_url"]}')

		lgr.info(f'4.1:Elapsed {elapsed()}')
	except Exception as e: lgr.error(f'Send Outbound Message Error: {e}')


async def send_outbound_messages(is_bulk=True, limit_batch=100):
	try:

		s = time.perf_counter()
		elapsed = lambda: time.perf_counter() - s
		with transaction.atomic():
			#.order_by('contact__product__priority').select_related('contact','template','state').all
			def outbound_query():        
				return Outbound.objects.select_for_update(of=('self',)).filter(Q(contact__subscribed=True),Q(contact__product__notification__code__channel__name='WHATSAPP API'),~Q(recipient=None),
					Q(contact__status__name='ACTIVE',contact__product__is_bulk=is_bulk),
					Q(Q(contact__product__trading_box=None)|Q(contact__product__trading_box__open_time__lte=timezone.localtime().time(),
					contact__product__trading_box__close_time__gte=timezone.localtime().time())),
					Q(scheduled_send__lte=timezone.now(),state__name='CREATED',date_created__gte=timezone.now()-timezone.timedelta(hours=24))\
					|Q(state__name="PROCESSING",date_modified__lte=timezone.now()-timezone.timedelta(minutes=20),date_created__gte=timezone.now()-timezone.timedelta(minutes=60))\
					|Q(state__name="FAILED",date_modified__lte=timezone.now()-timezone.timedelta(minutes=20),date_created__gte=timezone.now()-timezone.timedelta(minutes=60)))\
					.select_related('contact','template','state').all

			#orig_outbound = await outbound_query()
			orig_outbound = await sync_to_async(outbound_query, thread_sensitive=True)()

			lgr.info('Orig Outbound: %s' % orig_outbound)

			outbound = orig_outbound()[:limit_batch].values_list('id','recipient','contact__product__id','contact__product__notification__endpoint__batch','ext_outbound_id',
                                                'contact__product__notification__ext_service_id','contact__product__notification__code__code','message','contact__product__notification__endpoint__account_id',
                                                'contact__product__notification__endpoint__password','contact__product__notification__endpoint__username','contact__product__notification__endpoint__api_key',
                                                'contact__subscription_details','contact__linkid','contact__product__notification__endpoint__url','contact__product__notification__endpoint__request',
						'contact__product__notification__code__channel__name')

			lgr.info(f'1:Elapsed {elapsed()}')
			lgr.info('Outbound: %s' % outbound)
			if len(outbound):
				messages=np.asarray(outbound)
				lgr.info(f'2:Elapsed {elapsed()}')
				lgr.info('Messages: %s' % messages)

				##Update State
				processing = orig_outbound().filter(id__in=messages[:,0].tolist()).update(state=OutBoundState.objects.get(name='PROCESSING'), date_modified=timezone.now(), sends=F('sends')+1)

				response = await send_outbound_message(messages)

			lgr.info(f'1.1:Elapsed {elapsed()}')
	except Exception as e: lgr.error(f'Send Outbound Messages Error: {e}')


@app.timer(interval=5)
async def _nbulk_send_outbound_messages(app):
	try:
		await send_outbound_messages(is_bulk=False, limit_batch=60)
	except Exception as e: lgr.error(f'Non-Bulk Send Outbound Messages Error: {e}')

@app.timer(interval=5)
async def _bulk_send_outbound_messages(app):
	try:
		await send_outbound_messages(is_bulk=True, limit_batch=240)
	except Exception as e: lgr.error(f'Bulk Send Outbound Messages Error: {e}')

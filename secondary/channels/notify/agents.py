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

@app.agent(sent_messages_topic)
async def sent_messages(messages):
	async for message in messages:
		try:
			s = time.perf_counter()
			elapsed = lambda: time.perf_counter() - s
			async def _record(message):
				lgr.info(f'RECEIVED Sent Messages {message}')
				outbound = Outbound.objects.get(id=message['outbound_id'])
				outbound.state = OutBoundState.objects.get(name=message['response_state'])
				outbound.response = message['response_code']
				outbound.batch_id = message['batch_id']
				outbound.save()
				lgr.info(f'{elapsed()} Sent Messages Updated')
			await _record(message)
		except Exception as e: lgr.info(f'Error on Sent Messages: {e}')
	#async for message in messages.take(15, within=1):
	#	try:
	#		s = time.perf_counter()
	#		
	#		elapsed = lambda: time.perf_counter() - s

	#		lgr.info(f'RECEIVED Sent Messages {len(message)}: {message}')
	#		df = pd.DataFrame(message)

	#		batch_id = df['batch_id'].values
	#		outbound_id = df['outbound_id'].values
	#		recipient = df['recipient'].values
	#		response_state = df['response_state'].values
	#		response_code = df['response_code'].values

	#		def update_sent_outbound(outbound_id, outbound_state, response, batch_id):
	#			outbound = Outbound.objects.get(id=outbound_id)
	#			outbound.state = OutBoundState.objects.get(name=outbound_state)
	#			outbound.response = response
	#			outbound.batch_id = batch_id
	#			return outbound

	#		outbound_list = await sync_to_async(np.vectorize(update_sent_outbound))(outbound_id=outbound_id, outbound_state=response_state, response=response_code, batch_id=batch_id)
	#		await sync_to_async(Outbound.objects.bulk_update, thread_sensitive=True)(outbound_list.tolist(), ['state','response','batch_id'])
	#		lgr.info(f'{elapsed()} Sent Messages Updated')

	#	except Exception as e: lgr.info(f'Error on Sent Messages: {e}')

@app.agent(delivery_status_topic)
async def delivery_status(messages):
	async for message in messages:
		try:
			s = time.perf_counter()
			elapsed = lambda: time.perf_counter() - s
			async def _record(message):
				lgr.info(f'RECEIVED Delivery Status {message}')
				outbound = Outbound.objects.filter(batch_id=message['batch_id']).\
								update(state=OutBoundState.objects.get(name=message['response_state']),
								response=message['response_code'])
				lgr.info(f'{elapsed()} Delivery Status Updated')

			await _record(message)
		except Exception as e: lgr.info(f'Error on Delivery Status: {e}')

	#async for message in messages.take(150, within=5):
	#	try:
	#		s = time.perf_counter()
	#		
	#		elapsed = lambda: time.perf_counter() - s

	#		lgr.info(f'RECEIVED Delivery Status {len(message)}: {message}')
	#		df = pd.DataFrame(message)

	#		batch_id = df['batch_id'].values
	#		recipient = df['recipient'].values
	#		response_state = df['response_state'].values
	#		response_code = df['response_code'].values

	#		def update_delivery_outbound(batch_id, outbound_state, response):
	#			outbound = None
	#			try:
	#				outbound = Outbound.objects.get(batch_id=batch_id)
	#				outbound.state=OutBoundState.objects.get(name=outbound_state)
	#				outbound.response=response
	#				return outbound
	#			except MultipleObjectsReturned:
	#				outbound_list = Outbound.objects.filter(batch_id=batch_id)
	#				lgr.info(f'{elapsed()} Delivery Status Outbound List {outbound_list}')
	#				result = outbound_list.update(state=OutBoundState.objects.get(name=outbound_state), 
	#								response=response)
	#				lgr.info(f'{elapsed()} Delivery Status Outbound {result}')
	#				return None
	#			except ObjectDoesNotExist:
	#				return None


	#		outbound_list = await sync_to_async(np.vectorize(update_delivery_outbound))(batch_id=batch_id, outbound_state=response_state, response=response_code)
	#		outbound_list = list(filter(None,outbound_list))
	#		if outbound_list: await sync_to_async(Outbound.objects.bulk_update, thread_sensitive=True)(outbound_list, ['state','response'])

	#		lgr.info(f'{elapsed()} Delivery Status Updated {outbound_list}')

	#	except Exception as e: lgr.info(f'Error on Delivery Status: {e}')


#@app.agent(join_sent_messages_topic)
#async def join_sent_messages(messages):
#	async for message in messages.take(300, within=1):
#		try:
#			s = time.perf_counter()
#			
#			elapsed = lambda: time.perf_counter() - s
#
#			lgr.info(f'Join Sent Message: {message}')
#			async def update_sent_status(data):
#				try:
#					df = pd.DataFrame(data)
#					for response_state in df['sent_response_state'].unique():
#						lgr.info(f'{elapsed()} Response State {response_state}')
#						response_state_df = df[df['sent_response_state']==response_state]
#						q_list = map(lambda n: Q(id=n[1]['outbound_id']), response_state_df.iterrows())
#						q_list = reduce(lambda a, b: a | b, q_list) 
#						state = await sync_to_async(OutBoundState.objects.get)(name=response_state)
#						lgr.info(f'{elapsed()} State Outbound Join Sent {state}')
#						#outbound = await sync_to_async(Outbound.objects.filter)(~Q(state=state), q_list)
#						outbound = await sync_to_async(Outbound.objects.filter)(q_list)
#						lgr.info(f'{elapsed()} Filter Outbound Join Sent {outbound}')
#						lgr.info(f'{elapsed()} Outbound: {outbound.query.__str__()}')
#						outbound = await sync_to_async(outbound.update)(state=state)
#						lgr.info(f'{elapsed()} Updated Outbound Join Sent {outbound}')
#				except Exception as e: lgr.info(f' Error on Update Sent Status {e}')
#
#			response = await update_sent_status(message)
#			lgr.info(f'{elapsed()} Update Join Sent Messages')
#		except Exception as e: lgr.info(f'Error on Join Sent Notification: {e}')

#async def sent_messages(messages):
#	async for message in messages.take(300, within=1):
#		try:
#			s = time.perf_counter()
#			
#			elapsed = lambda: time.perf_counter() - s
#
#			lgr.info(f'RECEIVED Sent Notification {len(message)}: {message}')
#			message = np.asarray(message)
#			message_id = message[:,0]
#			message_status = message[:,1]
#			message_response = message[:,2]
#
#			def update_sent_outbound(outbound_id, outbound_state, response):
#				outbound = Outbound.objects.get(id=outbound_id)
#				outbound.state = OutBoundState.objects.get(name=outbound_state)
#				outbound.response = response
#				return outbound
#
#			outbound_list = await sync_to_async(np.vectorize(update_sent_outbound))(outbound_id=message_id, outbound_state=message_status, response=message_response)
#			await sync_to_async(Outbound.objects.bulk_update, thread_sensitive=True)(outbound_list.tolist(), ['state','response'])
#			lgr.info(f'{elapsed()} Sent Messages Updated')
#
#		except Exception as e: lgr.info(f'Error on Sent Notification: {e}')
#
#async def delivery_status(messages):
#	async for message in messages.take(300, within=5):
#		try:
#			s = time.perf_counter()
#			elapsed = lambda: time.perf_counter() - s
#
#			lgr.info(f'RECEIVED Delivery Status {len(message)}: {message}')
#			message = np.asarray(message)
#			message_id = message[:,0]
#			message_status = message[:,1]
#			message_response = message[:,2]
#
#			def update_sent_outbound(outbound_id, outbound_state, response):
#				outbound = Outbound.objects.get(id=outbound_id)
#				outbound.state = OutBoundState.objects.get(name=outbound_state)
#				outbound.response = response
#				return outbound
#
#			outbound_list = await sync_to_async(np.vectorize(update_sent_outbound))(outbound_id=message_id, outbound_state=message_status, response=message_response)
#			await sync_to_async(Outbound.objects.bulk_update, thread_sensitive=True)(outbound_list.tolist(), ['state','response'])
#			lgr.info(f'{elapsed()} Delivery Status Updated')
#		except Exception as e: lgr.info(f'Error on Delivery Status: {e}')

async def send_outbound_message(messages):
	try:
		s = time.perf_counter()

		elapsed = lambda: time.perf_counter() - s
	
		df = pd.DataFrame({'outbound_id':messages[:,0], 'recipient':messages[:,1], 'product_id':messages[:,2], 'batch':messages[:,3], 'ext_service_id':messages[:,5],'code':messages[:,6],\
			'message':messages[:,7],'endpoint_account_id':messages[:,8],'endpoint_password':messages[:,9],'endpoint_username':messages[:,10],\
			'endpoint_api_key':messages[:,11],'linkid':messages[:,13],'endpoint_url':messages[:,14], 'channel':messages[:,16]})

		lgr.info(f'3:Elapsed {elapsed()}')
		lgr.info('DF: %s' % df)
		df['batch'] = pd.to_numeric(df['batch'])
		df = df.dropna(axis='columns',how='all')

		lgr.info(f'DF 0 {df}')

		##if not df['endpoint_request'].empty:
		##df['endpoint_request'] = df['endpoint_request'].to_json(orient="records")
		#df['endpoint_request']= df['endpoint_request'].fillna({i: {} for i in df.index})
		##df['endpoint_request'] = df['endpoint_request'].apply(ast.literal_eval)
		#lgr.info(f'DF 1 {df}')
		#df = df.join(pd.json_normalize(df['endpoint_request']))
		#lgr.info(f'DF 2 {df}')
		#df.drop(columns=['endpoint_request'], inplace=True)

		lgr.info(f'DF 3 {df}')
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
					topic = app.topic(payload['endpoint_url'])
					lgr.info(f'Topic: {topic}')
					tasks.append(topic.send(value=payload))
			elif len(group_df.shape)>1 :
				lgr.info(f'Got Here (list of singles): {recipients}')
				for d in recipients:
					payload['recipients'] = [d]       
					lgr.info(payload)
					topic = app.topic(payload['endpoint_url'])
					lgr.info(f'Topic: {topic}')
					tasks.append(topic.send(value=payload))
			else:
				lgr.info(f'Got Here (single): {recipients}')
				payload['recipients'] = recipients
				lgr.info(payload)
				topic = app.topic(payload['endpoint_url'])
				lgr.info(f'Topic: {topic}')
				tasks.append(topic.send(value=payload))

			#Control Speeds
			#await asyncio.sleep(0.10)
			lgr.info(f'4:Elapsed {elapsed()}')
			lgr.info(f'Sent Message to topic {payload["endpoint_url"]}')

		lgr.info(f'4.1:Elapsed {elapsed()}')
		response = await asyncio.gather(*tasks)
		lgr.info(f'5:Elapsed {elapsed()} Sent Outbound Message {response}')
	except Exception as e: lgr.error(f'Send Outbound Message Error: {e}')


async def send_outbound_messages(is_bulk=True, limit_batch=100):
	try:

		s = time.perf_counter()
		elapsed = lambda: time.perf_counter() - s
		with transaction.atomic():
			#.order_by('contact__product__priority').select_related('contact','template','state').all
			#|Q(state__name="PROCESSING",date_modified__lte=timezone.now()-timezone.timedelta(minutes=20),date_created__gte=timezone.now()-timezone.timedelta(minutes=60))\
			def outbound_query():        
				return Outbound.objects.select_for_update(of=('self',)).filter(Q(contact__subscribed=True),Q(contact__product__notification__code__channel__name='SMS'),~Q(recipient=None),
					Q(contact__status__name='ACTIVE',contact__product__is_bulk=is_bulk),
					Q(Q(contact__product__trading_box=None)|Q(contact__product__trading_box__open_time__lte=timezone.localtime().time(),
					contact__product__trading_box__close_time__gte=timezone.localtime().time())),
					Q(scheduled_send__lte=timezone.now(),state__name='CREATED',date_created__gte=timezone.now()-timezone.timedelta(hours=24))\
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


@app.timer(interval=1)
async def _nbulk_send_outbound_messages(app):
	try:
		await send_outbound_messages(is_bulk=False, limit_batch=60)
	except Exception as e: lgr.error(f'Non-Bulk Send Outbound Messages Error: {e}')

@app.timer(interval=1)
async def _bulk_send_outbound_messages(app):
	try:
		await send_outbound_messages(is_bulk=True, limit_batch=240)
	except Exception as e: lgr.error(f'Bulk Send Outbound Messages Error: {e}')



#from mode import Service
#
#@app.service
#class NotificationService(Service):
#	async def on_start(self):
#		print('NOTIFICATION SERVICEIS STARTING')
#
#	async def on_stop(self):
#		print('NOTIFICATION SERVICE IS STOPPING')
#
#	@Service.task
#	async def _notification(self):
#		while not self.should_stop:
#			print('NOTIFICATION SERVICE RUNNING')
#			try:
#				await send_outbound_messages(is_bulk=False, limit_batch=60)
#				#await self.sleep(2.0)
#			except Exception as e: lgr.error(f'Non-Bulk Send Outbound Messages Error: {e}')
#
#	@Service.task
#	async def _bulk_notification(self):
#		while not self.should_stop:
#			print('BULK NOTIFICATION SERVICE RUNNING')
#			try:
#				await send_outbound_messages(is_bulk=True, limit_batch=240)
#				#await self.sleep(2.0)
#			except Exception as e: lgr.error(f'Bulk Send Outbound Messages Error: {e}')




import faust
from faust.types import StreamT
#from primary.core.async.faust import app
from switch.faust import app
import requests, json


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

s = time.perf_counter()


'''
class OutBoundMessage(faust.Record):
    from_name: str
    to_name: str
    count: float
    records: int
{'product': '433', 'batch': '10', 'kmp_service_id': 'TEST', 'kmp_code': 'TEST', 'kmp_message': 'Test', 'kmp_spid': 'TEST', 'kmp_password': 'TEST', 'node_account_id': 'TEST', 'node_password': 'TEST', 'node_username': 'TEST', 'contact_info': '', 'node_url': 'integrator.apps.test.notification', 'kmp_recipients': ['254725765441', '254717103598']} 

{'product_id': '433', 'batch': '10', 'ext_service_id': 'TEST', 'code': 'TEST', 'message': 'Test', 'account_id': 'TEST', 'endpoint_password': 'TEST', 'endpoint_username': 'TEST', 'subscription_details': '', 'endpoint_url': 'integrator.apps.test.notification', 'recipients': [(61690123, '254725765441'), (61690124, '254725765441'), (61690125, '254725765441'), (61144994, '254717103598'), (61144995, '254717103598'), (61144996, '254717103598')]}

{'product_id': '433', 'batch': '10', 'ext_service_id': 'TEST', 'code': 'TEST', 'message': 'Test', 'account_id': 'TEST', 'endpoint_password': 'TEST', 'endpoint_username': 'TEST', 'subscription_details': '', 'endpoint_url': 'integrator.apps.test.notification', 'channel': 'WHATSAPP API', 'recipients': [(61690123, '254725765441'), (61690124, '254725765441'), (61690125, '254725765441'), (61144994, '254717103598'), (61144995, '254717103598'), (61144996, '254717103598')]}

topic = app.topic('switch.channels.notify.whatsapp_message', value_type=Greeting)
'''

async def send_outbound_message(messages):
	try:

		'''
		'id','recipient','contact__product__id','contact__product__notification__endpoint__batch','ext_outbound_id',\
		'contact__product__notification__ext_service_id','contact__product__notification__code__code','message','contact__product__notification__endpoint__account_id',\
		'contact__product__notification__endpoint__password','contact__product__notification__endpoint__username','contact__product__notification__endpoint__api_key',\
		'contact__subscription_details','contact__linkid','contact__product__notification__endpoint__url'
		'''
		count = time.perf_counter() - s
		elapsed = "{0:.2f}".format(count)
		'''
		df = pd.DataFrame({'kmp_recipients':messages[:,1], 'product':messages[:,2], 'batch':messages[:,3],'kmp_correlator':messages[:,4],'kmp_service_id':messages[:,5],'kmp_code':messages[:,6],\
			'kmp_message':messages[:,7],'kmp_spid':messages[:,8],'kmp_password':messages[:,9],'node_account_id':messages[:,8],'node_password':messages[:,9],'node_username':messages[:,10],\
			'node_api_key':messages[:,11],'contact_info':messages[:,12],'linkid':messages[:,13],'node_url':messages[:,14]})
		'''
	
		df = pd.DataFrame({'outbound_id':messages[:,0], 'recipient':messages[:,1], 'product_id':messages[:,2], 'batch':messages[:,3],'ext_outbound_id':messages[:,4],'ext_service_id':messages[:,5],'code':messages[:,6],\
			'message':messages[:,7],'endpoint_account_id':messages[:,8],'endpoint_password':messages[:,9],'endpoint_username':messages[:,10],\
			'endpoint_api_key':messages[:,11],'subscription_details':messages[:,12],'linkid':messages[:,13],'endpoint_url':messages[:,14], 'channel':messages[:,15]})

		#lgr.info(f'3:Elapsed {elapsed}')
		#lgr.info('DF: %s' % df)
		df['batch'] = pd.to_numeric(df['batch'])
		df = df.dropna(axis='columns',how='all')
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
			#lgr.info(f'4:Elapsed {elapsed}')
			lgr.info(f'Sent Message to topic {payload["endpoint_url"]}')
	except Exception as e: lgr.error(f'Send Outbound Message Error: {e}')

is_bulk = False
limit_batch = 100


@app.timer(interval=10)
async def send_outbound_messages(app):
	try:
		lgr.info(f'{app}')

		count = time.perf_counter() - s
		elapsed = "{0:.2f}".format(count)
		lgr.info(f'0:Elapsed {elapsed}')
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

			outbound = orig_outbound()[:limit_batch].values_list('id','recipient','contact__product__id','contact__product__notification__endpoint__batch','ext_outbound_id',\
                                                'contact__product__notification__ext_service_id','contact__product__notification__code__code','message','contact__product__notification__endpoint__account_id',\
                                                'contact__product__notification__endpoint__password','contact__product__notification__endpoint__username','contact__product__notification__endpoint__api_key',\
                                                'contact__subscription_details','contact__linkid','contact__product__notification__endpoint__url','contact__product__notification__code__channel__name')

			#lgr.info(f'1:Elapsed {elapsed}')
			#lgr.info('Outbound: %s' % outbound)
			if len(outbound):
				messages=np.asarray(outbound)
				#lgr.info(f'2:Elapsed {elapsed}')
				#lgr.info('Messages: %s' % messages)

				##Update State
				#processing = orig_outbound().filter(id__in=messages[:,0].tolist()).update(state=OutBoundState.objects.get(name='PROCESSING'), date_modified=timezone.now(), sends=F('sends')+1)

				response = await send_outbound_message(messages)

	except Exception as e: lgr.error(f'Send Outbound Messages Error: {e}')



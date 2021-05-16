import faust
from faust.types import StreamT
#from primary.core.async.faust import app
from switch.faust import app
import requests, json


from django.db import transaction
from .models import *
from django.db.models import Q,F

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
        value=Greeting(from_name='Switch Notify Task', to_name='you', count=float(elapsed), records=records),
    )
    count+=1


is_bulk = False
limit_batch = 100

#@app.task
@app.timer(interval=10)
#@transaction.atomic
async def _send_outbound_sms_messages_list(app):
	try:
		lgr.info(f'{app}')

		count = time.perf_counter() - s
		elapsed = "{0:.2f}".format(count)
		lgr.info(f'0:Elapsed {elapsed}')
		with transaction.atomic():
			'''
			def outbound_query():        
				return Outbound.objects.select_for_update(of=('self',)).filter(Q(contact__subscribed=True),Q(contact__product__notification__code__channel__name='WHATSAPP API'),\
                                                Q(Q(contact__product__trading_box=None)|Q(contact__product__trading_box__open_time__lte=timezone.localtime().time(),contact__product__trading_box__close_time__gte=timezone.localtime().time())),\
                                                ~Q(recipient=None),~Q(recipient=''),~Q(contact__product__notification__endpoint__url=None),~Q(contact__product__notification__endpoint__url=''),\
                                                Q(scheduled_send__lte=timezone.now(),state__name='CREATED',date_created__gte=timezone.now()-timezone.timedelta(hours=24))\
                                                |Q(state__name="PROCESSING",date_modified__lte=timezone.now()-timezone.timedelta(minutes=20),date_created__gte=timezone.now()-timezone.timedelta(minutes=60))\
                                                |Q(state__name="FAILED",date_modified__lte=timezone.now()-timezone.timedelta(minutes=20),date_created__gte=timezone.now()-timezone.timedelta(minutes=60)),\
                                                Q(contact__status__name='ACTIVE',contact__product__is_bulk=is_bulk)).order_by('contact__product__priority').select_related('contact').all

			#orig_outbound = await outbound_query()
			orig_outbound = await sync_to_async(outbound_query, thread_sensitive=True)()
			'''

			def outbound_query():        
				return Outbound.objects.select_for_update(of=('self',)).filter(Q(contact__subscribed=True),Q(contact__product__notification__code__channel__name='WHATSAPP API'),\
                                                Q(Q(contact__product__trading_box=None)|Q(contact__product__trading_box__open_time__lte=timezone.localtime().time(),contact__product__trading_box__close_time__gte=timezone.localtime().time())),\
                                                ~Q(recipient=None),~Q(recipient=''),~Q(contact__product__notification__endpoint__url=None),~Q(contact__product__notification__endpoint__url=''),\
                                                Q(scheduled_send__lte=timezone.now(),state__name='CREATED',date_created__gte=timezone.now()-timezone.timedelta(hours=24))\
                                                |Q(state__name="PROCESSING",date_modified__lte=timezone.now()-timezone.timedelta(minutes=20),date_created__gte=timezone.now()-timezone.timedelta(minutes=60))\
                                                |Q(state__name="FAILED",date_modified__lte=timezone.now()-timezone.timedelta(minutes=20),date_created__gte=timezone.now()-timezone.timedelta(minutes=60)),\
                                                Q(contact__status__name='ACTIVE',contact__product__is_bulk=is_bulk)).order_by('contact__product__priority').select_related('contact','state','template',
						'contact__product','contact__subscription','contact__product__notification''contact__product__notification__endpoint','contact__product__notification__code').all

			#orig_outbound = await outbound_query()
			orig_outbound = await sync_to_async(outbound_query, thread_sensitive=True)()

			lgr.info('Orig Outbound: %s' % orig_outbound)

			outbound = orig_outbound()[:limit_batch].values_list('id','recipient','contact__product__id','contact__product__notification__endpoint__batch','ext_outbound_id',\
                                                'contact__product__notification__ext_service_id','contact__product__notification__code__code','message','contact__product__notification__endpoint__account_id',\
                                                'contact__product__notification__endpoint__password','contact__product__notification__endpoint__username','contact__product__notification__endpoint__api_key',\
                                                'contact__subscription_details','contact__linkid','contact__product__notification__endpoint__url')

			lgr.info(f'1:Elapsed {elapsed}')
			lgr.info('Outbound: %s' % outbound)
			'''
                if len(outbound):
                    messages=np.asarray(outbound)

                    lgr.info(f'2:Elapsed {elapsed}')
                    lgr.info('Messages: %s' % messages)


                    ##Update State
                    #processing = orig_outbound().filter(id__in=messages[:,0].tolist()).update(state=OutBoundState.objects.get(name='PROCESSING'), date_modified=timezone.now(), sends=F('sends')+1)

                    df = pd.DataFrame({'kmp_recipients':messages[:,1], 'product':messages[:,2], 'batch':messages[:,3],'kmp_correlator':messages[:,4],'kmp_service_id':messages[:,5],'kmp_code':messages[:,6],\
                                'kmp_message':messages[:,7],'kmp_spid':messages[:,8],'kmp_password':messages[:,9],'node_account_id':messages[:,8],'node_password':messages[:,9],'node_username':messages[:,10],\
                                'node_api_key':messages[:,11],'contact_info':messages[:,12],'linkid':messages[:,13],'node_url':messages[:,14]})

                    lgr.info(f'3:Elapsed {elapsed}')
                    lgr.info('DF: %s' % df)
                    df['batch'] = pd.to_numeric(df['batch'])
                    df = df.dropna(axis='columns',how='all')
                    cols = df.columns.tolist()
                    #df.set_index(cols, inplace=True)
                    #df = df.sort_index()
                    cols.remove('kmp_recipients')
                    grouped_df = df.groupby(cols)
                    lgr.info('Grouped DF: %s' % grouped_df)

                    tasks = []
                    for name,group_df in grouped_df:
                            batch_size = group_df['batch'].unique()[0]
                            kmp_recipients = group_df['kmp_recipients'].unique().tolist()
                            payload = dict()    
                            for c in cols: payload[c] = str(group_df[c].unique()[0])
                            lgr.info('MULTI: %s \n %s' % (group_df.shape,group_df.head()))
                            if batch_size>1 and len(group_df.shape)>1 and group_df.shape[0]>1:
                                    objs = kmp_recipients
                                    lgr.info('Got Here (multi): %s' % objs)
                                    start = 0
                                    while True:
                                            batch = list(islice(objs, start, start+batch_size))
                                            start+=batch_size
                                            if not batch: break
                                            payload['kmp_recipients'] = batch
                                            lgr.info(payload)
                                            #if is_bulk: tasks.append(bulk_send_outbound_batch_list.s(payload))
                                            #else: tasks.append(send_outbound_batch_list.s(payload))
                            elif len(group_df.shape)>1 :
                                    lgr.info('Got Here (list of singles): %s' % kmp_recipients)
                                    for d in kmp_recipients:
                                            payload['kmp_recipients'] = [d]       
                                            lgr.info(payload)
                                            #if is_bulk: tasks.append(bulk_send_outbound_list.s(payload))
                                            #else: tasks.append(send_outbound_list.s(payload))
                            else:
                                    lgr.info('Got Here (single): %s' % kmp_recipients)
                                    payload['kmp_recipients'] = kmp_recipients
                                    lgr.info(payload)
                                    #if is_bulk: tasks.append(bulk_send_outbound_list.s(payload))
                                    #else: tasks.append(send_outbound_list.s(payload))

                    lgr.info('Tasks: %s' % tasks)

			'''
			#Control Speeds
			#await asyncio.sleep(0.10)

			'''

                        tasks = []
                        for name,group_df in grouped_df:
                                batch_size = group_df['batch'].unique()[0]
                                kmp_recipients = group_df['kmp_recipients'].unique().tolist()
                                payload = dict()    
                                for c in cols: payload[c] = str(group_df[c].unique()[0])
                                #lgr.info('MULTI: %s \n %s' % (group_df.shape,group_df.head()))
                                if batch_size>1 and len(group_df.shape)>1 and group_df.shape[0]>1:
                                        objs = kmp_recipients
                                        lgr.info('Got Here (multi): %s' % objs)
                                        start = 0
                                        while True:
                                                batch = list(islice(objs, start, start+batch_size))
                                                start+=batch_size
                                                if not batch: break
                                                payload['kmp_recipients'] = batch
                                                lgr.info(payload)
                                                if is_bulk: tasks.append(bulk_send_outbound_batch_list.s(payload))
                                                else: tasks.append(send_outbound_batch_list.s(payload))
                                elif len(group_df.shape)>1 :
                                        lgr.info('Got Here (list of singles): %s' % kmp_recipients)
                                        for d in kmp_recipients:
                                                payload['kmp_recipients'] = [d]       
                                                lgr.info(payload)
                                                if is_bulk: tasks.append(bulk_send_outbound_list.s(payload))
                                                else: tasks.append(send_outbound_list.s(payload))
                                else:
                                        lgr.info('Got Here (single): %s' % kmp_recipients)
                                        payload['kmp_recipients'] = kmp_recipients
                                        lgr.info(payload)
                                        if is_bulk: tasks.append(bulk_send_outbound_list.s(payload))
                                        else: tasks.append(send_outbound_list.s(payload))

                        lgr.info('Got Here 10: %s' % tasks)

                        chunks, chunk_size = len(tasks), 100
                        sms_tasks= [ group(*tasks[i:i+chunk_size])() for i in range(0, chunks, chunk_size) ]
			'''

	except Exception as e: lgr.error(f'Send Outbound Message Error: {e}')



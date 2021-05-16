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
from itertools import islice

lgr = logging.getLogger(__name__)
lgr.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s-%(name)s %(funcName)s %(process)d %(thread)d-(%(threadName)-2s) %(levelname)s-%(message)s')
ch.setFormatter(formatter)

lgr.addHandler(ch)

HTTPConnection.debuglevel = 1


s = time.perf_counter()


async def send_outbound_message(messages):
	try:


		count = time.perf_counter() - s
		elapsed = "{0:.2f}".format(count)
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











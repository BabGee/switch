import faust
from faust.types import StreamT
#from primary.core.async.faust import app
from switch.faust_app import app as _faust
import requests, json, ast
from aiocassandra import aiosession
import dateutil.parser

from django.db import transaction
from .models import *
from django.db.models import Q,F
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from functools import reduce
from mode import Service
from concurrent.futures import ThreadPoolExecutor

from primary.core.api.views import ServiceCall
from secondary.channels.vcs.models import *

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

service_topic = _faust.topic('switch.primary.core.upc.api.service')

thread_pool = ThreadPoolExecutor(max_workers=4)


def api_service_call(payload):
        service_name = payload.get('SERVICE')
        if 'session_id' not in payload.keys() and 'credentials' not in payload.keys():
                #To use this access, one would require the System@User API_KEY
                #This access can create any user's session thus get any users API_KEY
                lgr.info('# A system User Login')
                gateway_profile_list = GatewayProfile.objects.using('read').filter(Q(Q(allowed_host__host=str(payload['gateway_host'])),Q(allowed_host__status__name='ENABLED'))\
                                        |Q(Q(gateway__default_host__host=str(payload['gateway_host'])),Q(gateway__default_host__status__name='ENABLED')),\
                                        Q(user__username='System@User'),Q(status__name__in=['ACTIVATED','ONE TIME PIN','FIRST ACCESS'])).select_related()

        #Integration would need an API Key for the specific user.
        #Integration would require the user credentials on call so as to select user for API KEY check
        #If unable to locate record status is received on app, redirect to logout or call logout function
        elif 'session_id' not in payload.keys() and 'credentials' in payload.keys():
                #This allows any user with credentials to access services enabled within their access level
                #System services are excluded. (System services are the most sensitive)
                lgr.info('# A Credentials User Login')
                credentials = payload['credentials']
                gateway_profile_list = GatewayProfile.objects.using('read').filter(Q(allowed_host__host=payload['gateway_host'],\
                                        allowed_host__status__name='ENABLED')|Q(gateway__default_host__host=payload['gateway_host'],\
                                        gateway__default_host__status__name='ENABLED'),\
                                        Q(Q(user__username=credentials['username'])|Q(user__email=credentials['username'])),\
                                        Q(status__name__in=['ACTIVATED','ONE TIME PIN','FIRST ACCESS'])).select_related()#Cant Filter as password check continues

                if gateway_profile_list.exists():
                        gp = None
                        for g in gateway_profile_list:
                                if g.user.check_password(credentials['password']):
                                        gp = g
                                        break
                        if gp !=  None:
                                lgr.info('This User Active')
                                gateway_profile_list = gateway_profile_list.filter(id=gp.id).select_related()
                        else:
                                gateway_profile_list = GatewayProfile.objects.using('read').none()
                else:
                        gateway_profile_list = GatewayProfile.objects.using('read').none()

        elif 'session_id' in payload.keys():
                #This user can access services within its access level
                lgr.info('Session ID available')
                try:
                        lgr.info('SessionID: %s' % payload['session_id'])
                        session_id = base64.urlsafe_b64decode(str(payload['session_id']).encode()).decode('utf-8')
                        session = Session.objects.using('read').filter(Q(session_id=session_id),\
                                Q(channel__id=payload['chid']),\
                                Q(gateway_profile__allowed_host__host=payload['gateway_host'],\
                                gateway_profile__allowed_host__status__name='ENABLED')|\
                                Q(gateway_profile__gateway__default_host__host=payload['gateway_host'],\
                                gateway_profile__gateway__default_host__status__name='ENABLED'),\
                                Q(gateway_profile__status__name__in=['ACTIVATED','ONE TIME PIN','FIRST ACCESS'])).select_related()

                        if session.exists():
                                lgr.info('Session Exists')
                                
                                user_session_list = Session.objects.filter(id=session.last().id, status__name='CREATED')
                                if user_session_list.exists():
                                        user_session = user_session_list.last()
                                        lgr.info('User Session: %s' % user_session)
                                        session_expiry = user_session.gateway_profile.role.session_expiry if user_session.gateway_profile.role and \
                                                        user_session.gateway_profile.role.session_expiry else \
                                                        user_session.gateway_profile.gateway.session_expiry
                                        lgr.info('Session Expiry: %s' % session_expiry)
                                        #if True:#Check date_created/modified for expiry time
                                        if session_expiry: lgr.info('Last Access: %s | Expiration time: %s' % (user_session.last_access, user_session.last_access + timezone.timedelta(minutes=session_expiry)))
                                        if session_expiry and timezone.now() > user_session.last_access + timezone.timedelta(minutes=session_expiry):
                                                lgr.info('Expiring Session')
                                                session_active = False
                                                user_session.status = SessionStatus.objects.get(name='EXPIRED')
                                                user_session.save()
                                        else:
                                                user_session.last_access = timezone.now()
                                                user_session.save()

                                        if (session_expiry == None) or (session_expiry and session_active):
                                                try: gateway_profile_list = GatewayProfile.objects.using('read').filter(id=user_session.gateway_profile.id).select_related()
                                                except: pass
                                else:
                                        lgr.info('Expired Session')
                                        session_active = False
                        else:
                                lgr.info('Non-existent Session')
                                session_active = False

                except Exception as e:
                        lgr.info('Error: %s' % e)
                #session should be encrypted and salted in base64
                #Session should last around 24 - 48 hours before pasword is prompted once again for access
                #Get Session from VCS and capture user #Pass the captured user for transaction
                #IF A WRONG SESSION IS PASSED, CLOSE PREVIOUS SESSION
                #iF SESSION TIME MORE THAN N-HOURS Request Credentials from USER
                #Country of Session must remain Consistent
        else:
                lgr.info('None of the Above')

        if gateway_profile_list.exists():
                lgr.info('Got Gateway Profile')
                gateway_profile = gateway_profile_list.first()
                service = Service.objects.using('read').filter(Q(name=service_name),Q(Q(access_level=gateway_profile.access_level)|Q(access_level=None))).select_related() 
                #lgr.info('Got Service: %s (%s)' % (service, service_name))
                if service.exists():
                        #payload = await sync_to_async(ServiceCall().api_service_call, thread_sensitive=True)(service.first(), gateway_profile, payload)
                        #payload = await _faust.loop.run_in_executor(thread_pool, ServiceCall().api_service_call, *[service.first(), gateway_profile, payload])
                        payload = ServiceCall().api_service_call(service.first(), gateway_profile, payload)
                        lgr.info(f'Service Call Result {payload}')
                else:

                        lgr.info(f'Service Does not Exist')
        else:
                lgr.info(f'Gateway Profile Does not Exist')

        return payload


@_faust.agent(service_topic)
async def service(messages):
    async for message in messages:
        try:
            s = time.perf_counter()
            elapsed = lambda: time.perf_counter() - s

            lgr.info(f'RECEIVED Service Request {message}')
            payload = message.copy()

            payload = await _faust.loop.run_in_executor(thread_pool, api_service_call, *[payload])

            lgr.info(f'{elapsed()} Service Call Task Completed')

            await asyncio.sleep(0.1)
        except Exception as e: lgr.info(f'Error on Service Call: {e}')


#@_faust.agent(service_topic, concurrency=4)
#async def service(stream):
#    async for event in stream.events():
#        try:
#            s = time.perf_counter()
#            elapsed = lambda: time.perf_counter() - s
#            lgr.info(f'{elapsed()}RECEIVED Service Call {event}')
#            key = event.key
#            value = event.value
#            offset = event.message.offset
#            headers = event.headers
#
#            lgr.info(f'{elapsed()} Key: {key} | Value: {value} | Offset {offset} | Headers: {headers}')
#            ####################
#            payload = value.copy()
#
#            payload = await _faust.loop.run_in_executor(thread_pool, api_service_call, *[payload])
#
#            ###################
#
#            lgr.info(f'{elapsed()} Service Call Task Completed')
#            await asyncio.sleep(0.5)
#
#        except Exception as e: lgr.info(f'Error on Service Call: {e}')
#

#@_faust.agent(service_call_topic, concurrency=16)
#async def service_call(messages):
#	async for message in messages:
#		try:
#			s = time.perf_counter()
#			elapsed = lambda: time.perf_counter() - s
#			lgr.info(f'RECEIVED Service Call {message}')
#                        params = dict()
#                        gateway_profile 
#                        service = message['SERVICE']
#        		payload = await sync_to_async(ServiceCall().api_service_call, 
#                                                                thread_sensitive=True)(service, gateway_profile, params)
#
#			lgr.info(f'Service Call Result {payload}')
#			lgr.info(f'{elapsed()} Service Call Task Completed')
#			#await asyncio.sleep(0.5)
#		except Exception as e: lgr.info(f'Error on Service Call: {e}')



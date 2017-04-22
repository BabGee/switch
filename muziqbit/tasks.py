from __future__ import absolute_import
from celery import shared_task
from celery.contrib.methods import task_method
from celery.contrib.methods import task
from switch.celery import app
from celery.utils.log import get_task_logger

from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import utc
from django.contrib.gis.geos import Point
from django.db import IntegrityError
import pytz, time, json
from django.utils.timezone import localtime
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
import base64, re
from django.core.files import File
from django.db.models import Count

from muziqbit.models import *
from django.db.models import Q
import operator

import logging
lgr = logging.getLogger('muziqbit')


class Wrappers:
	@app.task(filter=task_method, ignore_result=True)
	def log_download(self, payload, node_info):
		lgr = get_task_logger(__name__)
		try:
			music = Music.objects.get(id=payload['music_id'])
			download_type = DownloadType.objects.filter(service__name=payload['SERVICE'])
			if 'session_gateway_profile_id' in payload.keys():
				gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
			else:
				gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			download = Download(music=music,download_type=download_type[0],gateway_profile=gateway_profile)

			if 'bridge__transaction_id' in payload.keys():
				download.transaction_reference = payload['bridge__transaction_id']

			download.save()
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Fetching Song Details: %s" % e)
		return payload


class System(Wrappers):
	def song_item_details(self, payload, node_info):
		try:

			song = payload['song']
			#get artiste name
			artiste_list = re.findall("\((.*?)\)", song)
			artiste = ''
			if len(artiste_list)>0:
				artiste = artiste_list[len(artiste_list)-1]
				song = song.replace('('+artiste+')','')

			music = Music.objects.filter(product_item__name=song,artiste=artiste,product_item__institution__id=payload['institution_id'],\
					product_item__status__name='ACTIVE').order_by('-release_date')

			if len(music)>0:
				payload['media_path'] = music[0].file_path.name
				payload['media_convert'] = 'mp4|mp3'
				#payload['song'] = item.product_item.name
				payload['ARTISTE'] = music[0].artiste
				payload['ALBUM'] = music[0].album
				payload['product_item_id'] = music[0].product_item.id
                                payload['institution_till_id'] = music[0].product_item.institution_till.all()[0].id
                                payload['currency'] = music[0].product_item.currency.code
                                payload['amount'] = music[0].product_item.unit_cost
				#payload['product_type_id'] = music[0].product_item.product_type.id
				payload['music_id'] = music[0].id
				self.log_download.delay(payload,{}) # Log Download
				payload['response']= 'Song Details Acquired'
				payload['response_status']= '00'
			else:
				payload['response_status'] = '25'
				payload['response'] = 'Song not Found'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Fetching Song Details: %s" % e)
		return payload


	def music_details(self, payload, node_info):
		try:
			music = Music.objects.get(id=payload['music_id'])
			payload['product_item_id'] = music.product_item.id
			payload['music_name'] = music.product_item.name
			payload['artiste'] = music.artiste
			payload['album'] = music.album
			payload['response']= 'Music Details Acquired'
			payload['response_status']= '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Music Details: %s" % e)
		return payload

	def ussd_song_details(self, payload, node_info):
		try:
			lgr.info("Get Song Details Payload: %s" % payload)

			music = Music.objects.filter(Q(product_item__name=payload['Music']),Q(product_item__product_type__name='Music'),\
						 Q(product_item__institution__id=payload['institution_id']),\
						 product_item__status__name='ACTIVE').order_by('-release_date')

			item = None
			if len(music)>0:
				item = music[0]
				payload['media_path'] = item.file_path.name
				payload['media_convert'] = 'mp4|mp3'
				#Song not captured, so constructed
				payload['song'] = '%s(%s)' % (item.product_item.name,item.artiste)
				payload['ARTISTE'] = item.artiste
				payload['ALBUM'] = item.album
				payload['product_type_id'] = item.product_item.product_type.id
				payload['music_id'] = item.id
				self.log_download.delay(payload,{}) # Log Download
				payload['response']= 'Song Details Acquired'
				payload['response_status']= '00'
			else:
				payload['response_status'] = '25'
				payload['response'] = 'Song not Found'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Fetching Song Details: %s" % e)
		return payload


	def ussd_searched_song_details(self, payload, node_info):
		try:
			lgr.info("Get Song Details Payload: %s" % payload)

			query0 = reduce(operator.or_, ( Q(product_item__name__icontains=s.strip()) for s in payload['Search'].split(" ") ))
			query1 = reduce(operator.or_, ( Q(artiste__icontains=s.strip()) for s in payload['Search'].split(" ") ))
			query2 = reduce(operator.and_, ( Q(product_item__name__icontains=s.strip()) for s in payload['Search'].split(" ") ))
			query3 = reduce(operator.and_, ( Q(artiste__icontains=s.strip()) for s in payload['Search'].split(" ") ))

			#music = Music.objects.filter(Q(query0, query1) |Q(artiste__icontains=payload['Search'])|Q(product_item__name__icontains=payload['Search']) | query2 |query3,\
			#		 Q(product_item__institution__id=code[0].institution.id) )[:10]

			music = Music.objects.filter(query0|query1,Q(product_item__institution__id=payload['institution_id']),\
						 product_item__status__name='ACTIVE').order_by('-release_date')

			if len(music)>1:
				music0 = music.filter(query0|query1)
				if len(music0)>1:
					music1 = music0.filter(Q(product_item__name__icontains=payload['Search']) |Q(artiste__icontains=payload['Search']))
					if len(music1) > 1:
						music = music1
					else:
						music2 = music0.filter(query0,query1)
						if len(music2) > 1:
							music = music2
						else:
							music = music0

			music = music[:10]

			item = None
			for i in music:
				song = '%s(%s)' % (i.product_item.name,i.artiste)
				if song == payload['song']:
					item = i
				else:
					continue
			lgr.info('Item: %s' % item)
			if item is not None:
				payload['media_path'] = item.file_path.name
				payload['media_convert'] = 'mp4|mp3'
				#payload['song'] = item.product_item.name
				payload['ARTISTE'] = item.artiste
				payload['ALBUM'] = item.album
				payload['product_type_id'] = item.product_item.product_type.id
				payload['music_id'] = item.id
				self.log_download.delay(payload,{}) # Log Download
				payload['response']= 'Song Details Acquired'
				payload['response_status']= '00'
			else:
				payload['response_status'] = '25'
				payload['response'] = 'Song not Found'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Fetching Song Details: %s" % e)
		return payload


class Payments(System):
	pass

class Trade(System):
	pass


lgr = get_task_logger(__name__)
#Celery Tasks Here

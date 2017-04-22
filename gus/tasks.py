from __future__ import absolute_import
from celery import shared_task
from celery.contrib.methods import task_method
from celery.contrib.methods import task
from switch.celery import app
from celery.utils.log import get_task_logger

from django.shortcuts import render
from django.contrib.auth.models import User
#from upc.backend.wrappers import *
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
import time, os, random, string, json
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from django.db import IntegrityError
from django.contrib.gis.geos import Point
from django.conf import settings
from django.core.files import File
from django.db.models import F
import base64, re, urllib

from gus.models import *

import logging
lgr = logging.getLogger('gus')


class Wrappers:
	def createBase(self):
		chars = string.ascii_letters + string.punctuation + string.digits
		rnd = random.SystemRandom()
		s = ''.join(rnd.choice(chars) for i in range(4))
		#base = base64.urlsafe_b64encode(s)
		base = s.encode('hex').lower()

		u = Shortener.objects.filter(base=base,visits__lt=F('url_type__max_visits'),\
			expiry__gte=timezone.now())
		if len(u)>0:
			return createUsername()
		else:
			return base

	@app.task(filter=task_method, ignore_result=True)
	def copyFile(self, file_path, shortener):
		lgr = get_task_logger(__name__)
		try:
			lgr.info('Starting Convert File')
			import shlex
			from subprocess import Popen, PIPE

			cmd = 'cp '+file_path['fpath']+' '+file_path['copy_fpath']

			process = Popen(shlex.split(cmd), stdout=PIPE)
			s=process.communicate()    # execute it, the output goes to the stdout
			lgr.info(s)
			exit_code = process.wait()    # when finished, get the exit code

			if exit_code == 0:
				lgr.info('Successful Copy')
				shortener.status = ShortenerStatus.objects.get(name='ACTIVE')
				shortener.save()
				return True
			else:
				lgr.info('Copy File Failed')
				return False
		except Exception, e:
			lgr.info("Error on copy file: %s" % e)
			return False


	@app.task(filter=task_method, ignore_result=True)
	def convertFile(self, file_path, shortener):
		lgr = get_task_logger(__name__)
		try:
			lgr.info('Starting Convert File')
			import shlex
			from subprocess import Popen, PIPE

			cmd = 'ffmpeg -i '+file_path['fpath']+'  -vn -strict -2 -f mp3 '+file_path['convert_fpath']
			#cmd = 'ffmpeg -i '+file_path['fpath']+'  -strict -2 -f mp3 '+file_path['convert_fpath']

			process = Popen(shlex.split(cmd), stdout=PIPE)
			s=process.communicate()    # execute it, the output goes to the stdout
			lgr.info(s)
			exit_code = process.wait()    # when finished, get the exit code

			if exit_code == 0:
				lgr.info('Successful Conversion')
				shortener.status = ShortenerStatus.objects.get(name='ACTIVE')
				shortener.save()
				return True
			else:
				lgr.info('Convert File Failed')
				return False
		except Exception, e:
			lgr.info("Error on convert file: %s" % e)
			return False


class System(Wrappers):
	def redirect_url(self, payload, node_info):
		try:
			lgr.info('Redirect URL Payload: %s' % payload)
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			unique_base = self.createBase() 

			url_type = URLType.objects.get(name='REDIRECT URL')
			status = ShortenerStatus.objects.get(name='ACTIVE')
			s = Shortener(base=unique_base,url=payload['original_url'],url_type=url_type,\
					expiry=timezone.now()+timezone.timedelta(hours=72),visits=0,\
					updated=False,name=payload['redirect_name'][:199],status=status)

			if 'session_gateway_profile_id' in payload.keys():
				session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
				s.gateway_profile = session_gateway_profile 
			else:
				s.gateway_profile = gateway_profile 

			s.save()

			payload['URL'] = 'https://gus.gs/%s' % unique_base

			payload['response'] = 'Processed'
			payload['response_status'] = '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on redirect url: %s" % e)
		return payload


	def hf_facebook_url(self, payload, node_info):
		try:
			names = ''
			if 'first_name' in payload.keys():
				names = '%s' % payload['first_name']

			redirect_uri = 'https://nikobizz.com/api/facebook/%s/' % names.strip() 
			payload['original_url'] = 'https://www.facebook.com/dialog/oauth?app_id=1961923274033108&redirect_uri=%s&scope=publish_actions' % urllib.quote_plus(redirect_uri)
			payload['redirect_name'] = 'Facebook'

			payload = self.redirect_url(payload, {})


		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on redirect url: %s" % e)
		return payload


	def download_url(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			media_root = settings.MEDIA_ROOT + '/' 
			media_temp = settings.MEDIA_ROOT + '/tmp_gus_media/'
			if 'media_path' in payload.keys() and payload['media_path'] not in [None,'']:
				extension = os.path.splitext(payload['media_path'])[1]
				if extension == '.mp4':
					file_path = {}
					file_path['fpath'] =  media_root + payload['media_path']
					convert_fname = os.path.splitext(payload['media_path'])[0]+'.mp3'
					file_path['convert_fpath'] = media_temp + convert_fname 


					#create gus record
					unique_base = self.createBase() 

					url_type = URLType.objects.get(name='DRM DOWNLOAD')
					status = ShortenerStatus.objects.get(name='INACTIVE')
					s = Shortener(base=unique_base,url=convert_fname,url_type=url_type,\
							expiry=timezone.now()+timezone.timedelta(hours=24),visits=0,\
							updated=False,name=payload['song'][:199],status=status)

					if 'session_gateway_profile_id' in payload.keys():
						session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
						s.gateway_profile = session_gateway_profile 
					else:
						s.gateway_profile = gateway_profile 

					s.save()


					payload['URL'] = 'https://gus.gs/%s' % unique_base


					#find if file exists if not, create
					if os.path.isfile(file_path['convert_fpath']):
						s.status = ShortenerStatus.objects.get(name='ACTIVE')
						s.save()
					else:
						#convert create
						self.convertFile.delay(file_path,s)
				else:
					file_path = {}
					file_path['fpath'] =  media_root + payload['media_path']
					file_path['copy_fpath'] = media_temp + payload['media_path']


					#create gus record
					unique_base = self.createBase() 

					url_type = URLType.objects.get(name='DRM DOWNLOAD')
					status = ShortenerStatus.objects.get(name='INACTIVE')
					s = Shortener(base=unique_base,url=payload['media_path'],url_type=url_type,\
							expiry=timezone.now()+timezone.timedelta(hours=24),visits=0,\
							updated=False,name=payload['song'][:199],status=status)

					if 'session_gateway_profile_id' in payload.keys():
						session_gateway_profile = GatewayProfile.objects.get(id=payload['session_gateway_profile_id'])
						s.gateway_profile = session_gateway_profile 
					else:
						s.gateway_profile = gateway_profile 

					s.save()


					payload['URL'] = 'https://gus.gs/%s' % unique_base


					#find if file exists if not, create
					if os.path.isfile(file_path['copy_fpath']):
						s.status = ShortenerStatus.objects.get(name='ACTIVE')
						s.save()
					else:
						#convert create
						self.copyFile.delay(file_path,s)


				payload['response'] = 'Processed'
				payload['response_status'] = '00'
			else:
				payload['response_status'] = '25'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on download url: %s" % e)
		return payload


class Payments(System):
	pass

class Trade(System):
	pass



lgr = get_task_logger(__name__)
#Celery Tasks Here

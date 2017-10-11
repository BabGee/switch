from __future__ import absolute_import
from celery import shared_task
#from celery.contrib.methods import task_method
from celery import task
from switch.celery import app
from celery.utils.log import get_task_logger

from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import utc
from django.contrib.gis.geos import Point
from django.db import IntegrityError
import time, json
from django.utils.timezone import localtime
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
import base64, re
from django.core.files import File


from .models import *
import logging
lgr = logging.getLogger('roadroute')


class System:
	def get_directions(self, payload, node_info):
		try:
			import urllib, urllib2
			from xml.etree import cElementTree, ElementTree
			import re

			#city = 'Nairobi'
			country = 'Kenya'
			#request = 'mpaka road to haille sellasie'
			#info_list= request.split(' to ')
			info_list = [str(payload['ORIGIN']),str(payload['DESTINATION'])]
			#lgr.info('Got Origin & Destination')
			origin, destination = '',''
			count = 0
			elements = []
			info = []
			for elm in info_list:
				if count > 0:
					info.append({'origin':info_list[count-1],'destination':info_list[count]})
				count+=1
			lgr.info('Appended to Info: %s' % info)

			ultimate_regexp = "(?i)<\/?\w+((\s+\w+(\s*=\s*(?:\".*?\"|'.*?'|[^'\">\s]+))?)+\s*|\s*)\/?>"
			directions = ''

			for i in info:
				orig = urllib.quote(i['origin']+','+country)
				dest  = urllib.quote(i['destination']+','+country)
				url = 'https://maps.googleapis.com/maps/api/directions/xml?origin='+orig+'&destination='+dest+''
				response = urllib2.urlopen(url)
				params = response.read()
				tree = ElementTree.fromstring( params )
				lgr.info('Fetch from directions API: %s' % tree)

				for elm in tree.findall('*//step//html_instructions'):
					s =elm.text
			                directions = '%s%s. ' % (directions,re.sub(ultimate_regexp,' ', s) )
                			directions = directions.replace( '&nbsp;', ' ' )
		                	directions = directions.replace( '&amp;', '&' )
			                directions = directions.replace('A 104','. ')
        	        		directions = directions.replace('  ',' ')
			                directions = directions.replace(' .','.')

			lgr.info('Got Directions: %s' % directions)

			payload['message'] = str(directions)
			payload['response'] = 'Directions Captured'
			payload['response_status']= '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error on Getting Directions: %s" % e)
		return payload

class Trade(System):
	pass



lgr = get_task_logger(__name__)
#Celery Tasks here

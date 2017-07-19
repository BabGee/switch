from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import utc
from django.contrib.gis.geos import Point
from django.db import IntegrityError
import pytz, time, json, pycurl
from django.utils.timezone import localtime
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
import base64, re
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db.models import Q
import operator
import urllib, urllib2
from django.db import transaction
from xml.sax.saxutils import escape, unescape
from django.utils.encoding import smart_str, smart_unicode

#from paygate.models import *
#from notify.models import *
from notify.models import Endpoint
from pos.models import *

import logging
lgr = logging.getLogger('crb')

from celery import shared_task
#from celery.contrib.methods import task_method
from celery import task
from switch.celery import app
from switch.celery import single_instance_task


class Wrappers:
    @app.task(ignore_result=True)
    def service_call(self, service, gateway_profile, payload):
        from celery.utils.log import get_task_logger
        lgr = get_task_logger(__name__)
        from api.views import ServiceCall
        try:
            payload = ServiceCall().api_service_call(service, gateway_profile, payload)
            lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info('Unable to make service call: %s' % e)
        return payload

    def validate_url(self, url):
        val = URLValidator()
        try:
            val(url)
            return True
        except ValidationError, e:
            lgr.info("URL Validation Error: %s" % e)
            return False

    def post_request(self, payload, node):
        try:
            if self.validate_url(node):
                jdata = json.dumps(payload)
                # response = urllib2.urlopen(node, jdata, timeout = timeout)
                # jdata = response.read()
                # payload = json.loads(jdata)
                c = pycurl.Curl()
                # Timeout after 10 seconds
                c.setopt(pycurl.CONNECTTIMEOUT, 30)
                c.setopt(pycurl.TIMEOUT, 30)
                c.setopt(pycurl.NOSIGNAL, 1)
                c.setopt(pycurl.URL, str(node))
                c.setopt(pycurl.POST, 1)
                header = ['Content-Type: application/json; charset=utf-8', 'Content-Length: ' + str(len(jdata))]
                c.setopt(pycurl.HTTPHEADER, header)
                c.setopt(pycurl.POSTFIELDS, str(jdata))
                import StringIO
                b = StringIO.StringIO()
                c.setopt(pycurl.WRITEFUNCTION, b.write)
                c.perform()
                response = b.getvalue()

                payload = json.loads(response)
        except Exception, e:
            lgr.info("Error Posting Request: %s" % e)
            payload['response_status'] = '96'

        return payload


class System(Wrappers):
	def verification_details(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			payload['response'] = 'MSISDN Found'
			payload['response_status'] = '00'

		except Exception, e:
			lgr.info('Error on verification details: %s' % e)
			payload['response'] = str(e)
			payload['response_status'] = '96'
		return payload




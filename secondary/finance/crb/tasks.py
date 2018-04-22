from __future__ import absolute_import
from celery import shared_task
#from celery.contrib.methods import task_method
from celery import task
from switch.celery import app
from celery.utils.log import get_task_logger
from switch.celery import single_instance_task


from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import utc
from django.contrib.gis.geos import Point
from django.db import IntegrityError
import pytz, time, json, pycurl
from django.utils.timezone import localtime
from datetime import datetime, timedelta
import time, os, random, string, json
from decimal import Decimal, ROUND_DOWN
import base64, re
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db.models import Q,F
import operator
import urllib, urllib2
from django.db import transaction
from xml.sax.saxutils import escape, unescape
from django.utils.encoding import smart_str, smart_unicode

from secondary.finance.crb.models import *

import logging
lgr = logging.getLogger('secondary.finance.crb')

class Wrappers:
    @app.task(ignore_result=True)
    def service_call(self, service, gateway_profile, payload):
        from celery.utils.log import get_task_logger
        lgr = get_task_logger(__name__)
        from primary.core.api.views import ServiceCall
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
	def reference_risk(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			reference_risk = ReferenceRisk.objects.filter(gateway=gateway_profile.gateway)

			if 'institution_id' in payload.keys():
				reference_risk = reference_risk.filter(Q(institution__id=payload['institution_id'])\
									|Q(institution=None))
			else:
				reference_risk = reference_risk.filter(institution=None)

			'''
			if reference_risk.exists():
				if  
				if 'credit_account_list' in payload.keys():

			'''
			payload['response'] = "Reference Risk Captured"
			payload['response_status'] = '00'
		except Exception, e:
			payload['response'] = str(e)
			payload['response_status'] = '96'
			lgr.info("Error on reference risk: %s" % e)
		return payload



	def verification_details(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			'''
			{"response_code": "200", 
			"response_reason": "Product request processed successfully", 
			"personal_profile": {"nationalID": "25967960", "surname": "ONGARO", "gender": "M", "otherNames": "SAMSON ARITA", "dateOfBirth": "1988-06-24 00:00:00", "maritalStatus": "None", "salutation": "None", "fullName": "ONGARO SAMSON ARITA", "crn": "24722331", "healthInsuranceNo": "None"}}

			{"score_output": {"probability": "9.14", "grade": "DD", "reasonCodeAARC4": "Many unpaid installments or no loans that have regular monthly installments", "reasonCodeAARC3": "Many loan applications in the recent past (for non mobile loans)", "reasonCodeAARC2": "High number of open, longterm loans where the balance does not have to be paid every month compared to other loans", "reasonCodeAARC1": "Borrowed a lot on loans other than secured loans, those with regular payments or those where balances do not have to be paid every month", "positiveScore": "666"}, "accountList": [{"accountStatus": "FULLY SETTLED"}, {"accountStatus": "ACTIVE"}, {"accountStatus": "CLOSED"}, {"accountStatus": "CLOSED"}, {"accountStatus": "CLOSED"}, {"accountStatus": "CLOSED"}, {"accountStatus": "CLOSED"}, {"accountStatus": "CLOSED"}, {"accountStatus": "ACTIVE"}, {"accountStatus": "CLOSED"}], "response_code": "200", "summary": {"paClosedAccounts": {"otherSectors": 8, "mySector": 0}, "npaClosedAccounts": {"otherSectors": 0, "mySector": 0}, "npaOpenAccounts": {"otherSectors": 0, "mySector": 0}, "npaAccounts": {"otherSectors": 0, "mySector": 0}, "paAccounts": {"otherSectors": 10, "mySector": 0}, "paOpenAccounts": {"otherSectors": 2, "mySector": 0}, "creditHistory": {"otherSectors": 24, "mySector": 0}},
"personal_profile": {"nationalID": "25967960", "surname": "ONGARO", "otherNames": "SAMSON ARITA", "salutation": "None", "fullName": "ONGARO SAMSON ARITA", "crn": "24722331"}, "request_no": "17788908", "response_reason": "Product request processed successfully"}
			'''

			details = payload['remit_response']
			details = json.loads(details)
			response_code = details['response_code']
			lgr.info('Response Code: %s' % response_code)
			if response_code == '200':
				profile = details['personal_profile']
				payload['full_names'] = '%s %s' % (profile['otherNames'],profile['surname'])
				payload['national_id'] = profile['nationalID']


				#Log Reference Details
				reference_data = {}
				reference_data['surname'] =profile['surname']
				reference_data['client_number'] =profile['crn']

				names = profile['otherNames'].split(' ')
				forename = ['forename_1','forename_2','forename_3']
				count = 0
				for n in names[:3]:
					reference_data[forename[count]] = n
					count+=1

				if 'dateOfBirth' in profile.keys() and profile['dateOfBirth'] not in ['',None,"None"]:
					#dob = str(profile['dateOfBirth']).split(' ')[0].split('-')
					#payload['dob']= '%s/%s/%s' % (dob[2],dob[1],dob[0])
					#dob = datetime.strptime(payload['dob'], '%d/%m/%Y').date()

					dob = str(profile['dateOfBirth']).split(' ')[0]
					dob = datetime.strptime(dob, '%Y-%m-%d').date()
					payload['dob'] = dob.isoformat()
					reference_data['date_of_birth'] = dob


				if 'salutation' in profile.keys() and profile['salutation'] not in ['',None,"None"]:
					reference_data['salutation'] = profile['salutation']
					payload['salutation'] = profile['salutation']

				if 'gender' in profile.keys() and profile['gender'].strip() not in ['',None,"None"]:
					reference_data['gender'] = Gender.objects.get(code__iexact=profile['gender'].strip())
					payload['gender'] = profile['gender'].strip()

				if 'maritalStatus' in profile.keys() and profile['maritalStatus'] not in ['',None,"None"]:
					reference_data['marital_status'] = profile['maritalStatus']

				#score details
				if 'score_output' in details.keys() and isinstance(details['score_output'], dict):
					score_output = details['score_output']

					grade = score_output['grade']
					payload['credit_grade'] = grade
					credit_grade =CreditGrade.objects.get(code=grade)
					reference_data['credit_grade'] = credit_grade

					probability = score_output['probability']

					is_int,is_float = False,False
					try: is_int=isinstance(int(probability), int) 
					except:pass
					try: is_float=isinstance(float(probability),float)
					except:pass
					if is_int or is_float:
						payload['credit_probability'] = probability
						reference_data['credit_probability'] = probability
					else:
						payload['credit_probability'] = Decimal(0)
						reference_data['credit_probability'] = Decimal(0)


					score = score_output['positiveScore']
					payload['credit_score'] = score
					reference_data['credit_score'] = score

				#accounts details
				if 'accountList'  in details.keys():
					payload['credit_account_list'] = details['accountList']
					accountList = json.dumps(details['accountList'])
					lgr.info('Account List: %s' % accountList)
					reference_data['credit_account_list'] = accountList

				if 'summary'  in details.keys():
					payload['credit_account_summary'] = details['summary']
					summary = json.dumps(details['summary'])
					lgr.info('Summary : %s' % summary)
					reference_data['credit_account_summary'] = summary
					lgr.info('Summary 2: %s' % summary)

				identity = IdentificationProfile.objects.filter(national_id=payload['national_id'])

				lgr.info('Reference Data: %s' % reference_data)
				if identity.exists():
					if hasattr(identity[0], 'reference'):
						reference = identity[0].reference
						for k,v in reference_data.items():
							setattr(reference, k, v)
						reference.save()
					else:
						reference_data['identification_profile'] = identity[0]
						reference = Reference(**reference_data)
						reference.save()

				else:
					identification_profile = IdentificationProfile(national_id=payload['national_id'])
					identification_profile.save()
						
					reference_data['identification_profile'] = identification_profile
					reference = Reference(**reference_data)
					reference.save()

				payload['trigger'] = 'verified%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				payload['response'] = 'Verification Details Captured'
				payload['response_status'] = '00'
			else:
				payload['response_message'] = details['response_reason']
				payload['trigger'] = 'not_verified%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
				payload['response'] = 'Invalid Verification Details'
				payload['response_status'] = '00'

		except Exception, e:
			lgr.info('Error on verification details: %s' % e)
			payload['response'] = str(e)
			payload['response_status'] = '96'
		return payload


class Trade(System):
	pass
class Payments(System):
	pass



@app.task(ignore_result=True)
def reference_activity_service_call(activity):
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)
	from primary.core.api.views import ServiceCall
	try:
		i = ReferenceActivity.objects.get(id=activity)

		payload = json.loads(i.reference_activity_type.details)
		try:payload.update(json.loads(i.request))
		except:pass
		payload['product_item_id'] = i.reference_activity_type.product_item.id
		payload['national_id'] = i.identification_profile.national_id
		payload['chid'] = i.channel.id
		payload['ip_address'] = '127.0.0.1'
		payload['gateway_host'] = '127.0.0.1'
		if i.institution:
			payload['institution_id'] = i.institution.id
		else:
			payload['institution_id'] = i.reference_activity_type.product_item.institution.id

		service = i.reference_activity_type.service
		gateway_profile = i.gateway_profile

		payload = dict(map(lambda (key, value):(string.lower(key),json.dumps(value) if isinstance(value, dict) else str(value)), payload.items()))
		payload = ServiceCall().api_service_call(service, gateway_profile, payload)

		lgr.info('\n\n\n\n\t########\tResponse: %s\n\n' % payload)

		i.transaction_reference = payload['bridge__transaction_id'] if 'bridge__transaction_id' in payload.keys() else None

		if 'response_status' in payload.keys():
			i.status = TransactionStatus.objects.get(name='PROCESSED')
			i.response_status = ResponseStatus.objects.get(response=payload['response_status'])
		else:
			i.status = TransactionStatus.objects.get(name='FAILED')
			i.response_status = ResponseStatus.objects.get(response='20')
		i.save()

	except Exception, e:
		payload['response_status'] = '96'
		lgr.info('Unable to make service call: %s' % e)
	return payload


@app.task(ignore_result=True) #Ignore results ensure that no results are saved. Saved results on daemons would cause deadlocks and fillup of disk
@transaction.atomic
@single_instance_task(60*10)
def process_reference_activity():
	from celery.utils.log import get_task_logger
	lgr = get_task_logger(__name__)

	orig_activity = ReferenceActivity.objects.select_for_update().filter(status__name='CREATED',response_status__response='DEFAULT', \
									date_modified__lte=timezone.now()-timezone.timedelta(seconds=2))

	activity = list(orig_activity.values_list('id',flat=True)[:250])

	processing = orig_activity.filter(id__in=activity).update(status=TransactionStatus.objects.get(name='PROCESSING'), date_modified=timezone.now())
	for ac in activity:
		reference_activity_service_call.delay(ac)


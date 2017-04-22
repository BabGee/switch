from __future__ import absolute_import
from celery import shared_task
from celery.contrib.methods import task_method
from celery.contrib.methods import task
from switch.celery import app
from celery.utils.log import get_task_logger

from django.shortcuts import render
from doc.models import *
from PIL import Image
#from SimpleCV import Image as SCVImage
import cStringIO
import base64
import numpy as np
import cv2
from django.core.files import File

import logging
lgr = logging.getLogger('doc')

class ImageProcessor:
	@app.task(filter=task_method)
	def saveDocumentImage(self, payload, user):
		lgr = get_task_logger(__name__)
		try:
			fromdir_name = '/home/system/tmp/uploads/'
			def dimage(user, filename):
				from_file = fromdir_name + str(filename)
				lgr.info('Filename: %s' % filename)

				status = DocumentActivityStatus.objects.get(name='CREATED')
				created_by = User.objects.get(id=payload['user_id'])
				document = Document.objects.get(id=payload['DOCUMENT'])
				doc = DocumentActivity(user=user, document=document, status=status, created_by=created_by)
				with open(from_file, 'r') as f:
					myfile = File(f)
					doc.photo.save(filename, myfile, save=False)
				doc.save()
				myfile.close()
				f.close()
			if 'FRONT IMAGE' in payload.keys() and payload['FRONT IMAGE'] <> '':
				dimage(user, payload['FRONT IMAGE'])
			if 'BACK IMAGE' in payload.keys() and payload['BACK IMAGE'] <> '':
				dimage(user, payload['BACK IMAGE'])
			if 'LEFT IMAGE' in payload.keys() and payload['LEFT IMAGE'] <> '':
				dimage(user, payload['LEFT IMAGE'])
			if 'RIGHT IMAGE' in payload.keys() and payload['RIGHT IMAGE'] <> '':
				dimage(user, payload['RIGHT IMAGE'])
			if 'TOP IMAGE' in payload.keys() and payload['TOP IMAGE'] <> '':
				dimage(user, payload['TOP IMAGE'])
			if 'BOTTOM IMAGE' in payload.keys() and payload['BOTTOM IMAGE'] <> '':
				dimage(user, payload['BOTTOM IMAGE'])

		except Exception, e:
			lgr.info('Error On Saving Default Image: %s' % e)

class System: 
        def process_document(self, payload, node_info):
                try:   
			username = None
			if 'msisdn' in payload.keys():
	 			msisdn = str(payload['msisdn'])
				msisdn = msisdn.strip()
				if len(msisdn) == 9:
					msisdn = '+254' + msisdn
				elif len(msisdn) == 10:
					msisdn = '+254' + msisdn[-9:]
				elif len(msisdn) == 12:
					msisdn = '+' + msisdn
				elif len(msisdn) == 13 and msisdn[:-12] == '+':
					msisdn = str(payload['msisdn'])
				else:
					msisdn = None
				lgr.info('\n\n\n\n\t#######Final MSISDN: %s\n\n\n\n' % msisdn)
				username = msisdn
			elif 'EMAIL' in payload.keys() and self.validateEmail(payload['EMAIL']):
				username = payload['EMAIL']

			user = User.objects.filter(username=username)
			lgr.info('\n\n\n\t#######User: %s\n\n\n\n' % user)
			if len(user) > 0:
				names = '%s %s' % (user[0].first_name, user[0].last_name)

				#Save Product Extra Images
				ImageProcessor().saveDocumentImage.delay(payload, user[0])

				payload['response'] = 'Document Processed'
				payload['response_status'] = '00'
			else:
				payload['response_status'] = '13' #Record not Found

                except Exception, e:               
                        payload['response_status'] = '96'           
                        lgr.info("Error on Querying Registry: %s" % e)      
                return payload

        def document_info(self, payload, node_info):
                try:            
			payload['response'] = 'OCR Camera Started'
			payload['response_status'] = '00'
                except Exception, e:               
                        payload['response_status'] = '96'           
                        lgr.info("Error on Querying Registry: %s" % e)      
                return payload

class Trade(System):
	pass

class Payments(System):
	pass

lgr = get_task_logger(__name__)
#Celery Tasks Here

from SimpleXMLRPCServer import SimpleXMLRPCDispatcher
from django.http import HttpResponse
from django.template import Context, loader
from django.shortcuts import render
from django.shortcuts import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
import simplejson as json
from django.utils import timezone
from django.core.exceptions import PermissionDenied
#from paygate.backend.processor import *

import logging
lgr = logging.getLogger('paygate')

#BRIDGE PORT = 732873 #SECURE

class mpesa:
	__responseParams = {'response_status':'30',}
	def mpesac2b(self, request):
		if request.method == 'POST' or request.method == 'GET':	
			if request.method == 'POST':
				view_data = request.POST.copy()
				lgr.info('This request is POST')
			else:
				view_data = request.GET.copy()
				lgr.info('This request is GET')
			
			details = dict([(str(k), str(v)) for k, v in view_data.items()])						
			try:
				#json_results = json.dumps(details)
				function = 'mpesac2b'

				details['credentials'] = {'username': details['user'], 'password': details['pass'],}
				details['MSISDN'] = details['mpesa_msisdn']
				details['transaction_id'] = details['mpesa_code']
				details['currency'] = 'KES'
				details['amount'] = int(float(details['mpesa_amt']))
				details['account'] = 'KES'
				details['transaction_timestamp'] = details['tstamp']
				if 'sub_gateway' not in details.keys():
					name = None
					if details['business_number'] == '987300':
						name = 'Micromobile'
					sub_gateway = SubGateways.objects.filter(name=name)	
					details['sub_gateway'] = sub_gateway[0].name
				if 'text' in details.keys():
					del details['text']
                                        del details['mpesa_code']
                                        del details['mpesa_amt']
                                        del details['tstamp']
					del details['routemethod_name']
					del details['mpesa_trx_date']
					del details['id']
					del details['mpesa_trx_time']
			except Exception, e:
				lgr.info('API formulation Failed: %s' % e)

			try:						
				lgr.info('Starting getResponse call')
				self.__responseParams = processor().get_response(details, function)
				if 'response_status' in self.__responseParams.keys() and self.__responseParams['response_status'] == '00':					
					#response  = "OK|This request is GET"
					if 'response' in self.__responseParams.keys():
						response  = self.__responseParams['response']
				else:
					response  = "FAILED | An Error Occured"
				lgr.info('Got getResponse call %s' % self.__responseParams)
			except Exception, e:
				response  = "FAILED | An Error Occured"
				self.__responseParams['response'] = e
				self.__responseParams['response_status'] = 96
				lgr.info('Failed to getResponse %s' % e)

			lgr.info('Reponse Payload: %s' % self.__responseParams)

			return HttpResponse(response)	
		else:
			raise PermissionDenied
	
class dispatchermethods:
	__responseParams = {'response_status':'30',}
	def __init__(self):
		pass
	def actionHandler(self, details, function):
		if  isinstance(details, dict) and isinstance(function, str):
			lgr.info('Validation passed: details is dict and function str')
			try:						
				lgr.info('Starting getResponse call')
				self.__responseParams = processor().get_response(details, function)
				lgr.info('Got getResponse call %s' % self.__responseParams)
			except Exception, e:
				self.__responseParams['response'] = e
				self.__responseParams['response_status'] = 96
				lgr.info('Failed to getResponse %s' % e)
		else:
			self.__responseParams['response'] = "Bad variable types sent by Client"
			self.__responseParams['response_status'] = 30			
			lgr.info('Failed to continue %s' % self.__responseParams)			
				
		return self.__responseParams		
	
class mpesaxmlrpc(dispatchermethods): 	
	def __init__(self):
	
		self.dispatcher = SimpleXMLRPCDispatcher(allow_none=False, encoding=None) # Python 2.5
		self.dispatcher.register_function(dispatchermethods().actionHandler, 'actionHandler')
	def mpesaxmlrpc(self, request):

		if request.method == 'POST':
			#lgr.info('Request %s' % request.body)
			response = HttpResponse(mimetype="application/xml")						
			response.write(self.dispatcher._marshaled_dispatch(request.body))
			#lgr.info('Response %s' % response)					
		elif request.method == 'GET':
		        methods = self.dispatcher.system_listMethods()
		        for method in methods:
		                sig = self.dispatcher.system_methodSignature(method)
		                help =  self.dispatcher.system_methodHelp(method)
			context = Context({
					'title':'XML-RPC Server', 
					'narration':'XML-RPC server accepts POST requests only.',
					'name':{'sign': sig, 'help':help}})
			template = loader.get_template('RPC2.html')

		        response = HttpResponse(template.render(context))

		response['Content-length'] = str(len(response.content))
		return response
		

	
	




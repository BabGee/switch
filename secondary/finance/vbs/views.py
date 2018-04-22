from SimpleXMLRPCServer import SimpleXMLRPCDispatcher
from django.http import HttpResponse
from django.template import Context, loader
#from vbs.backend.processor import *
import logging
lgr = logging.getLogger('secondary.finance.vbs')

#BRIDGE PORT = 732873 #SECURE

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
	
class bridgexmlrpc(dispatchermethods): 	
	def __init__(self):
	
		self.dispatcher = SimpleXMLRPCDispatcher(allow_none=False, encoding=None) # Python 2.5
		self.dispatcher.register_function(dispatchermethods().actionHandler, 'actionHandler')

	def bridgexmlrpc(self, request):

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
		

	
	




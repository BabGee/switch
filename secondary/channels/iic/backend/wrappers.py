from django.db.models import Q
import re
from django.utils.encoding import smart_str
from xml.sax.saxutils import escape, unescape

import logging
lgr = logging.getLogger('iic')

class Wrappers:
	def fill_input_variables(self, input_variable, payload):
		lgr.info('Filler input: %s' % input_variable)

	

		default_value5 = input_variable[5]
		if default_value5:
			#if input_variable[5] in payload.keys():
			variables = re.findall("\[(.*?)\]", default_value5)
			lgr.info("Found Variables: %s" % variables)
			for v in variables:
				if v in payload.keys():
					default_value5 = default_value5.replace('['+v+']',str(payload[v]))
				else:
					default_value5 = default_value5.replace('['+v+']',"")



			#Escape html entities
			#default_value5 = unescape(default_value5)
			#default_value5 = smart_str(default_value5)
			#default_value5 = escape(default_value5)		

			#new vaiable 5 value
			input_variable[5] = default_value5



		default_value8 = input_variable[8]
		if default_value8:
			#if input_variable[8] in payload.keys():
			variables = re.findall("\[(.*?)\]", default_value8)
			lgr.info("Found Variables: %s" % variables)
			for v in variables:
				if v in payload.keys():
					default_value8 = default_value8.replace('['+v+']',str(payload[v]))
				else:
					default_value8 = default_value8.replace('['+v+']',"")


			#Escape html entities
			#default_value8 = unescape(default_value8)
			#default_value8 = smart_str(default_value8)
			#default_value8 = escape(default_value8)		

			#new vaiable 5 value
			input_variable[8] = default_value8
	
		
		return input_variable


from django.db.models import Q
import re
from django.utils.encoding import smart_str
from xml.sax.saxutils import escape, unescape

import logging
lgr = logging.getLogger('iic')

class Wrappers:
	def fill_input_variables(self, input_variable, payload):
		lgr.info('Filler input: %s' % input_variable)


		default_value4 = input_variable[4]
		if default_value4:
			#if input_variable[4] in payload.keys():
			variables = re.findall("\[(.*?)\]", default_value4)
			lgr.info("Found Variables: %s" % variables)
			for v in variables:
				if v in payload.keys():
					default_value4 = default_value4.replace('['+v+']',str(payload[v]))


			#Escape html entities
			#default_value4 = unescape(default_value4)
			#default_value4 = smart_str(default_value4)
			#default_value4 = escape(default_value4)		

			#new vaiable 5 value
			input_variable[4] = default_value4
		

		default_value5 = input_variable[5]
		if default_value5:
			#if input_variable[5] in payload.keys():
			variables = re.findall("\[(.*?)\]", default_value5)
			lgr.info("Found Variables: %s" % variables)
			for v in variables:
				if v in payload.keys():
					default_value5 = default_value5.replace('['+v+']',str(payload[v]))


			#Escape html entities
			#default_value5 = unescape(default_value5)
			#default_value5 = smart_str(default_value5)
			#default_value5 = escape(default_value5)		

			#new vaiable 5 value
			input_variable[5] = default_value5
		
		return input_variable


from django.utils import timezone
from secondary.channels.vcs.models import *
from django.db.models import Q
from itertools import chain
from secondary.channels.vcs.backend.page_string import PageString
import json, re, crypt
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import base64, re, pytz
from primary.core.upc.tasks import Wrappers as UPCWrappers
from decimal import Decimal

class VAS:
	def validateEmail(self, email):
		try:
			validate_email(email)
			return True
		except ValidationError:
			return False

	def initialize(self, *args):
		lgr = self.node_info.log
		if 'timelimit' in args:
			self.channel = Channel.objects.get(id=self.payload["chid"])
			if self.channel.name == 'USSD':
				return 200
			elif self.channel.name == 'IVR':
				return 3600

		if 'mno' in args:
			#self.prefix = MNOPrefix.objects.filter(prefix=self.payload['msisdn'][4:][:3], mno__country__ccode=self.payload['msisdn'][1:][:3])
			#Get Country Prefix for 7,6 and 5 digits local number
			code1=(len(self.payload["msisdn"]) -7)
			code2=(len(self.payload["msisdn"]) -6)
			code3=(len(self.payload["msisdn"]) -5)

			self.prefix = MNOPrefix.objects.filter(prefix=self.payload["msisdn"][:code3])

			if len(self.prefix)<1:
				self.prefix = MNOPrefix.objects.filter(prefix=self.payload["msisdn"][:code2])
				if len(self.prefix)<1:
					self.prefix = MNOPrefix.objects.filter(prefix=self.payload["msisdn"][:code1])
		elif 'create_menu' in args:
			#If authenticated session, keep all navigation authenticated 
			authenticated = self.navigator.filter(pin_auth=True)
			if authenticated.exists() or self.pin_auth:
				self.pin_auth = True
				self.navigator = self.navigator.filter(pin_auth=True)
			
			if len(self.navigator) > 0 and self.payload['input']!='00':#Not a Main Menu Request
				if self.gateway_profile.exists():
					self.navigator = self.navigator.filter(session__gateway_profile=self.gateway_profile[0])
				self.nav = self.navigator[0]
				self.level=str(int(self.nav.menu.level)+1); self.group_select=self.nav.menu.group_select
				#self.level=int(self.nav.level)+1; self.group_select=self.nav.group_select
				self.nav_step = self.nav.nav_step; self.service = self.nav.menu.service;
				#Initiate Session
				self.session = self.nav.session
				if self.nav.session.gateway_profile is not None:
					self.menu = self.menu.filter(access_level=self.nav.session.gateway_profile.access_level, code=self.code[0],\
									profile_status=self.nav.session.gateway_profile.status)
				else:
					self.menu = self.menu.filter(access_level__name='SYSTEM', code=self.code[0],profile_status=None)

			elif self.payload['input'] == '00' or len(self.navigator)<1:#Main Menu Request|First call
				self.group_select=0
				self.nav_step = (self.navigator[0].nav_step + 1) if self.payload['input'] == '00' and len(self.navigator)>0 else 0
				self.level = '0';self.nav = None; self.service = None
				#Initiate Session
				self.session = Session(session_id=self.payload['sessionid'], channel=self.channel, reference=self.payload['msisdn'],status=SessionStatus.objects.get(name='CREATED'))
				if self.gateway_profile.exists():
					self.session.gateway_profile = self.gateway_profile[0]
					self.menu = self.menu.filter(access_level=self.gateway_profile[0].access_level, code=self.code[0],\
									profile_status=self.gateway_profile[0].status)
				else:
					self.menu = self.menu.filter(access_level__name='SYSTEM', code=self.code[0],profile_status=None)

				self.session.save()

	def menu_view(self):
		lgr = self.node_info.log
		self.view_data = {}
		self.item_list = []

		menuitems = MenuItem.objects.filter(status__name='ENABLED')
		if self.gateway_profile.exists():
			menuitems = menuitems.filter(access_level=self.gateway_profile[0].access_level,profile_status=self.gateway_profile[0].status)
		else:
			menuitems = menuitems.filter(access_level__name='SYSTEM',profile_status=None)

		#FIlter Enrollments
		if self.gateway_profile.exists():
			session_gateway_profile = self.gateway_profile[0]
			enrollment_list = Enrollment.objects.filter(profile=session_gateway_profile.user.profile, expiry__gte=timezone.now())

			if enrollment_list.exists():
				menuitems = menuitems.filter(Q(enrollment_type_included__in=[e.enrollment_type for e in enrollment_list])|Q(enrollment_type_included=None),\
							~Q(enrollment_type_excluded__in=[e.enrollment_type for e in enrollment_list]))
			else:
				menuitems = menuitems.filter(enrollment_type_included=None)



		def get_menu_items(menuitems):
			if len(menuitems)>0:
				if 'response_status' in self.payload.keys() and  self.payload['response_status'] == '00':
					menuitems = menuitems.filter(Q(response_status=None)|Q(response_status__response='00'))
				elif 'response_status' in self.payload.keys():
					menuitems = menuitems.filter(response_status__response=self.payload['response_status'])
				else:
					menuitems = menuitems.filter(response_status=None)

				menuitems = menuitems.order_by('item_order').values('menu_item','item_level')
				self.item_list = ['%s' % (item['menu_item']) for item in menuitems.filter(~Q(item_level=0))] #Escape 0 for back and main in navigator entry to avoid validation issues
				this_item_list = ['%s%s' % (str(item['item_level'])+':' if item['item_level']>0 else '',item['menu_item']) for item in menuitems] #Zero 0 entries to not show number/item_level
				menu_items = '\n'.join(this_item_list)
				return  '\n%s' % menu_items
			else:
				return ''

		if self.menu.exists():

			new_navigator = Navigator(session=self.session, menu=self.menu[0], pin_auth=self.pin_auth, level=self.level, group_select=self.group_select,invalid=self.menu[0].invalid)
			new_navigator.input_select = self.payload['input']

			new_navigator.nav_step = self.nav_step
			new_navigator.code = self.code[0]
			new_navigator.save()

			#Process Page String
			try: self.payload =  PageString().pagestring(new_navigator, self.payload, self.code, self.node_info)
			except Exception as e: lgr.info('Error on Processing Page String: %s' % e)

			menuitems = menuitems.filter(menu=self.menu[0])
			page_string = '%s%s' % (self.payload['page_string'], get_menu_items(menuitems))

			if len(self.item_list)>0:
				new_navigator.item_list = json.dumps(self.item_list)
			new_navigator.save()


			session_state = self.payload['session_state'] if 'session_state' in self.payload.keys() and  self.payload['session_state'] not in [None,''] else self.menu[0].session_state.name 
			input_type = self.menu[0].input_variable.variable_type.variable
			input_min = self.menu[0].input_variable.validate_min
			input_max = self.menu[0].input_variable.validate_max
		elif self.nav and self.menu.exists() == False:

			if len(self.navigator)<2 and self.nav.menu.level == 0:
				error_prefix = None
			else:
				error_prefix = self.nav.menu.error_prefix if self.nav.menu.error_prefix not in ['',None] else 'Invalid input!' 

			new_navigator = Navigator(session=self.session, menu=self.nav.menu, pin_auth=self.pin_auth, level=self.level, group_select=self.group_select,invalid=True)
			new_navigator.input_select = self.nav.input_select

			new_navigator.nav_step = self.nav_step
			new_navigator.code = self.code[0]
			new_navigator.save()
			
			#Process Page String
			try: self.payload =  PageString().pagestring(new_navigator, self.payload, self.code, self.node_info)
			except Exception as e: lgr.info('Error on Processing Page String: %s' % e)

			menuitems = menuitems.filter(menu=self.nav.menu)

			if error_prefix:
				message = error_prefix.split('|')
				if len(message)>1 and message[1].strip()=='REPLACE': page_string = '%s' % (message[0])
				else: page_string = '%s %s%s' % (error_prefix, self.payload['page_string'], get_menu_items(menuitems))
			else:
				page_string = '%s%s' % (self.payload['page_string'], get_menu_items(menuitems))

			if len(self.item_list)>0:
				new_navigator.item_list = json.dumps(self.item_list)
			new_navigator.save()

			session_state = self.payload['session_state'] if 'session_state' in self.payload.keys() and  self.payload['session_state'] not in [None,''] else self.nav.menu.session_state.name 
			input_type = self.nav.menu.input_variable.variable_type.variable
			input_min = self.nav.menu.input_variable.validate_min
			input_max = self.nav.menu.input_variable.validate_max

		else:
			new_navigator = Navigator(session=self.session, level=self.level, group_select=self.group_select)
			new_navigator.input_select = self.payload['input']

			new_navigator.nav_step = self.nav_step
			new_navigator.code = self.code[0]
			new_navigator.save()

			page_string = 'Sorry, no Menu Found!'
			input_type = None
			input_min = 0
			input_max = 0
			session_state = 'END'

		'''
		self.payload['page_string'] = page_string
		#Process Page String
		if new_navigator is not None and new_navigator.menu is not None:

			try: self.payload =  PageString().pagestring(new_navigator, self.payload, self.code)
			except Exception as e: lgr.info('Error on Processing Page String: %s' % e)
		'''
		#import goslate
		#gs = goslate.Goslate()
		#page_string = gs.translate(page_string, 'sw')
		self.view_data["PAGE_STRING"] = page_string
		self.view_data["MNO_RESPONSE_SESSION_STATE"] = session_state
		self.view_data["INPUT_TYPE"] = input_type
		self.view_data["INPUT_MIN"] = input_min
		self.view_data["INPUT_MAX"] = input_max

	def create_menu(self, **kwargs):
		lgr = self.node_info.log
		#if exists, get navigator & max of nav_step order_by(nav_step)[1], add nav_step + 1
		self.menu = Menu.objects.filter(menu_status__name='ENABLED')
		self.pin_auth = False
		self.selection = None

		#Get Access Point
		if 'access_point' in kwargs.keys():
			self.access_point = kwargs['access_point']
		else:
			if 'accesspoint' not in self.payload.keys() and len(self.navigator)>0:
				self.payload['accesspoint'] = str(self.navigator[0].code.code)

			self.access_point = self.payload['accesspoint']
			#create code for USSD to allow for Shortcuts
			if 'input' in self.payload.keys() and len(self.navigator)<1 and self.channel.name == 'USSD':#the ussd string is available on first request meaning is shortcut
				extension = self.payload['input']
				self.access_point = '*%s*%s#' % (self.access_point,extension)
			elif len(self.navigator)==1 and self.navigator[0].input_select != 'BEG' and \
			self.navigator[0].code.mno.name=='Safaricom':#A shortcut first call
				self.payload['input'] = 'B'
				self.access_point = self.navigator[0].code.code
			elif 'input' in self.payload.keys() and len(self.navigator)>0 and self.channel.name == 'USSD':#All Succeeding USSD calls
				ussd_string = self.payload['input'].split('*')
				#self.payload['input'] = ussd_string[len(ussd_string)-1]
				self.payload['input'] = ussd_string[-1]
				self.access_point = self.navigator[0].code.code
			elif 'input' in self.payload.keys() and self.channel.name == 'USSD':#Default ussd call with input
				ussd_string = self.payload['input'].split('*')
				#self.payload['input'] = ussd_string[len(ussd_string)-1]
				self.payload['input'] = ussd_string[-1]
				self.access_point = '*%s#' % self.access_point
			elif self.channel.name == 'USSD':#Default ussd call
				self.access_point = '*%s#' % self.access_point
			self.payload['access_point'] = self.access_point

		#Inject input if still missing (for all channels)
		if 'input' not in self.payload.keys():
			#Injecting Zero ensures that the menu does not progress in case of bad input, but remains on the same page as back entry is initiated
			self.payload['input'] = 'BEG' 

		#Filter Code
		self.code = Code.objects.filter(code=self.access_point,channel=self.channel)

		if len(self.code.filter(code_type__name='SHORT CODE'))>0:#Means Conflicting Shortcodes, needs filter
			self.initialize('mno') #MNO not filtered prior to this so as to allow services like IVR that accepts all MNO's.
			self.code = self.code.filter(code_type__name='SHORT CODE', mno=self.prefix[0].mno) #Conflicting or matching codes only allowed on shotcodes as MNO's can issue matching shortcodes which are MNO bound, longcodes should never conflict and would be the same no matter the MNO

		self.menu = self.menu.filter(code=self.code[0])
		self.navigator = self.navigator.filter(menu__code=self.code[0])

		#Get User
		self.gateway_profile = GatewayProfile.objects.filter(Q(msisdn__phone_number=self.payload['msisdn']),Q(gateway =self.code[0].gateway),\
									 ~Q(status__name__in=['DEACTIVATED','DELETED']))

		#Filter Level
		#Levels should be String (if override has to check for None or '' as 0 values may validate for false and not show)
		if 'level' in kwargs.keys():
			self.level=str(kwargs['level'])

		#Create Menu
		self.initialize('create_menu')
		if self.payload['input'] == '0' and len(self.navigator)>0:#Go back to Previous Menu
			self.level = str(int(self.navigator[0].menu.level) -1)
			self.nav_step = self.navigator[0].nav_step
			try: nav= self.navigator.filter(menu__level=self.level,nav_step=self.nav_step); self.service=nav[0].menu.service; self.group_select=nav[0].menu.group_select
			except:pass

		#Filter Group
		#if self.payload['accesspoint'] == self.payload['input']:
		#if self.payload['accesspoint'] == self.payload['input'] and not len(self.navigator):
		#	self.group_select=0
		#elif 'group_select' in kwargs.keys():
		#	self.group_select=kwargs['group_select']
		if 'group_select' in kwargs.keys(): self.group_select = kwargs['group_select']

		#Filter & Validate Input
		if self.nav and self.payload['input'] not in ['0','00']:#Validate input but dont filter Back 0 and Main 00
			try:
				allowed_input_list = self.nav.menu.input_variable.allowed_input_list
				if ((len(self.payload['input'])>=int(self.nav.menu.input_variable.validate_min) and \
				len(self.payload['input'])<=int(self.nav.menu.input_variable.validate_max)) or \
				(allowed_input_list and self.payload['input'] in allowed_input_list.split(','))) and \
				((self.nav.menu.input_variable.variable_type.variable == 'email' and self.validateEmail(self.payload['input'])) or \
				(self.nav.menu.input_variable.variable_type.variable == 'msisdn' and UPCWrappers().simple_get_msisdn(self.payload['input'],self.payload)) or \
				(self.nav.menu.input_variable.variable_type.variable == 'id_number' and UPCWrappers().simple_id_number(self.payload['input'])) or \
				(self.nav.menu.input_variable.variable_type.variable == 'passport_number' and UPCWrappers().simple_passport_number(self.payload['input'])) or \
				(self.nav.menu.input_variable.variable_type.variable == 'id_passport' and UPCWrappers().simple_id_passport(self.payload['input'])) or \
				(self.nav.menu.input_variable.variable_type.variable == 'kra_pin' and UPCWrappers().simple_kra_pin(self.payload['input'])) or \
				(self.nav.menu.input_variable.variable_type.variable not in ['msisdn','email','id_passport','kra_pin'] and \
				isinstance(globals()['__builtins__'][self.nav.menu.input_variable.variable_type.variable](self.payload['input']), \
				globals()['__builtins__'][self.nav.menu.input_variable.variable_type.variable]))):
					lgr.info('Validated')
					override_group_select = self.nav.menu.input_variable.override_group_select
					error_group_select = self.nav.menu.input_variable.error_group_select
					override_level = self.nav.menu.input_variable.override_level
					error_level = self.nav.menu.input_variable.error_level
					override_service = self.nav.menu.input_variable.override_service
					init_nav_step= self.nav.menu.input_variable.init_nav_step

					if (allowed_input_list not in [None,''] and self.payload['input'] in allowed_input_list.split(',')): pass
					elif ('Non-Existing ID Number' in self.nav.menu.input_variable.name and \
					GatewayProfile.objects.filter(Q(gateway=self.code[0].gateway),~Q(status__name__in=['DEACTIVATED','DELETED']),\
					Q(user__profile__national_id__iexact=self.payload['input'].strip())).exists()) or \
					('Non-Existing Mobile Number' in self.nav.menu.input_variable.name and \
					GatewayProfile.objects.filter(Q(gateway=self.code[0].gateway),~Q(status__name__in=['DEACTIVATED','DELETED']),\
					Q(msisdn__phone_number=UPCWrappers().simple_get_msisdn(self.payload['input'].strip(),self.payload))).exists()) or \
					('Non-Existing Passport/National ID' in self.nav.menu.input_variable.name and \
					GatewayProfile.objects.filter(Q(gateway=self.code[0].gateway),~Q(status__name__in=['DEACTIVATED','DELETED']),\
					Q(user__profile__passport_number__iexact=self.payload['input'].strip())|
					Q(user__profile__national_id__iexact=self.payload['input'].strip())).exists()) or \
					('Non-Existing Passport/ID Number' in self.nav.menu.input_variable.name and \
					GatewayProfile.objects.filter(Q(gateway=self.code[0].gateway),~Q(status__name__in=['DEACTIVATED','DELETED']),\
					Q(user__profile__passport_number__iexact=self.payload['input'].strip())|
					Q(user__profile__national_id__iexact=self.payload['input'].strip())).exists()) or \
					('Non-Existing Passport Number' in self.nav.menu.input_variable.name and \
					GatewayProfile.objects.filter(Q(gateway=self.code[0].gateway),~Q(status__name__in=['DEACTIVATED','DELETED']),\
					Q(user__profile__passport_number__iexact=self.payload['input'].strip())).exists()) or \
					('Non-Existing EMAIL' in self.nav.menu.input_variable.name and \
					GatewayProfile.objects.filter(Q(gateway=self.code[0].gateway),~Q(status__name__in=['DEACTIVATED','DELETED']),\
					Q(user__email__iexact=self.payload['input'].strip())).exists()):
						#Variables with an error page
						if error_group_select not in [None,'']: self.group_select = error_group_select
						else: self.group_select = 96 #Fail menu as list not matching
						if error_level not in [None,'']: self.level = str(error_level)
						else: pass

					elif 'Amount' in self.nav.menu.input_variable.name and (self.nav.menu.input_variable.min_amount or self.nav.menu.input_variable.max_amount):
						try: val = Decimal(self.payload['input'])
						except: val = None

						if val and self.nav.menu.input_variable.min_amount and val >= self.nav.menu.input_variable.min_amount: pass
						else:
							if error_group_select not in [None,'']: self.group_select = error_group_select
							else: self.group_select = 97 #Fail menu as list not matching
							if error_level not in [None,'']: self.level = str(error_level)
							else: pass

						if val and self.nav.menu.input_variable.max_amount and val <= self.nav.menu.input_variable.max_amount: pass
						else:
							if error_group_select not in [None,'']: self.group_select = error_group_select
							else: self.group_select = 98 #Fail menu as list not matching
							if error_level not in [None,'']: self.level = str(error_level)
							else: pass

					elif self.nav.menu.input_variable.name == 'Business Number':
						try: institution = Institution.objects.filter(business_number=str(self.payload['input'])[:6], status__name='ACTIVE')
						except: institution = []
						if len(institution)<1:
							self.group_select = 96 #Fail menu as list not matching

					elif self.nav.menu.input_variable.name == 'EService':
						try:item_list = json.loads(self.nav.item_list)
						except: item_list = []
						if len(item_list)>0:
							try:es_name = item_list[int(self.payload['input'])-1]
							except:es_name=None
						else:es_name = None
						es = EnrolledService.objects.filter(name=es_name, institution__business_number=PageString().get_nav(self.nav)['BUSINESS NUMBER'],\
								institution__status__name='ACTIVE')
						if len(es)>0:
							self.service = es[0].service

					elif 'Select' in self.nav.menu.input_variable.name: 
						if self.nav.menu.input_variable.name in ['Select','Strict Select'] or 'Select for' in self.nav.menu.input_variable.name:
							self.group_select = self.payload['input']

						if override_group_select not in [None,'']: self.group_select = override_group_select
						if override_level not in [None,'']: self.level = str(override_level)
						if override_service not in [None,'']: self.service = override_service
						if init_nav_step: self.nav_step = (self.navigator[0].nav_step + 1) if self.navigator.exists() else 0

						#Comes after overrides
						if 'Product of Select' in self.nav.menu.input_variable.name:
							self.group_select = str(int(self.payload['input'])*int(override_group_select)) if override_group_select  else self.payload['input']

						#Matches Saved List to Input
						try:item_list = json.loads(self.nav.item_list)
						except:item_list = []

						try: self.selection = item_list[int(self.payload['input'])-1]; nolist=False
						except: 
							if allowed_input_list and self.payload['input'] in allowed_input_list.split(','): nolist=False
							else: nolist= True
						#if len(item_list)<1 or nolist:
						if nolist:
							if error_group_select not in [None,'']: self.group_select = error_group_select
							else: self.group_select = 96  #Fail menu as list not matching

							if error_level not in [None,'']: self.level = str(error_level)
							else: pass
						else:
							if self.nav.menu.input_variable.name == 'None Select':
								if error_group_select not in [None,'']: self.group_select = error_group_select
								else: self.group_select = None
								if error_level not in [None,'']: self.level = str(error_level)
								else: pass

					elif self.nav.menu.input_variable.name == 'Initialize':
						self.group_select = 0
						self.level = '0'

					elif 'Validated Pin' in self.nav.menu.input_variable.name:

						if override_group_select not in [None,'']: self.group_select = override_group_select
						if override_level not in [None,'']: self.level = str(override_level)
						if override_service not in [None,'']: self.service = override_service
						if init_nav_step: self.nav_step = (self.navigator[0].nav_step + 1) if self.navigator.exists() else 0

						if self.gateway_profile.exists():
							session_gateway_profile = self.gateway_profile[0]
							hash_pin = crypt.crypt(str(self.payload['input']), str(session_gateway_profile.id))

							if hash_pin == session_gateway_profile.pin:
								session_gateway_profile.pin_retries = 0
								session_gateway_profile.save()
								self.pin_auth = True
								#Validated Pin last as initialize create menu with input 00 changes self.nave to None
								if self.nav.menu.input_variable.name == 'Validated Pin':
									self.group_select = 0
									self.level = '0'
							else:
								if session_gateway_profile.pin_retries >= self.code[0].gateway.max_pin_retries:
									session_gateway_profile.status = ProfileStatus.objects.get(name='LOCKED')
									self.level = '99'
								else:
									self.level = '100'
								session_gateway_profile.pin_retries = session_gateway_profile.pin_retries+1
								session_gateway_profile.save()

					else:
						if override_group_select not in [None,'']: self.group_select = override_group_select
						if override_level not in [None,'']: self.level = str(override_level)
						if override_service not in [None,'']: self.service = override_service
						if init_nav_step: self.nav_step = (self.navigator[0].nav_step + 1) if self.navigator.exists() else 0

				else:
					#Not for change to error_group_select as it would need a page or redirect to page on invalid input
					self.group_select = 96 #Fail menu as list not matching

					lgr.info('Input Validation Failed')

			except Exception as e: lgr.info('Error: %s' % e); self.group_select = 96

		lgr.info('LEVEL: %s | GROUP: %s | Protected: %s | Service: %s | Selection: %s ' % (self.level, self.group_select, self.pin_auth, self.service, self.selection))

		#FIlter Enrollments
		if self.gateway_profile.exists():
			session_gateway_profile = self.gateway_profile[0]
			enrollment_list = Enrollment.objects.filter(profile=session_gateway_profile.user.profile, expiry__gte=timezone.now())
			if enrollment_list.exists():
				self.menu= self.menu.filter(Q(enrollment_type_included__in=[e.enrollment_type for e in enrollment_list])|Q(enrollment_type_included=None),\
							~Q(enrollment_type_excluded__in=[e.enrollment_type for e in enrollment_list]))
			else:
				self.menu= self.menu.filter(enrollment_type_included=None)

		#Filter Protected & Level
		self.menu = self.menu.filter(protected=self.pin_auth, level=self.level)

		#Filter group select
		self.menu = self.menu.filter(group_select=self.group_select)

		#Filter Service
		if self.service:
			self.menu = self.menu.filter(service=self.service)

		#Filter SubMenu selection - Got to be last after final menu is selected
		if self.selection:
			sub_menu = self.menu.filter(selection=self.selection)
			if sub_menu.exists():
				self.menu = sub_menu
			else:
				self.menu = self.menu.filter(Q(selection='')|Q(selection=None))
		else:
			self.menu = self.menu.filter(Q(selection='')|Q(selection=None))


		self.menu_view()


	def menu_input(self, payload, node_info):
		self.node_info = node_info
		lgr = self.node_info.log
		try:
			self.payload = payload
			#Get the sessionId, input. 
			#Check if sessionId exists in navigator, 

			self.navigator = Navigator.objects.filter(session__channel__id=self.payload["chid"], \
			session__date_created__gte = timezone.localtime(timezone.now())-timezone.timedelta(seconds=self.initialize('timelimit'))).order_by('-date_created','-nav_step','-menu__level')

			if 'sessionid' in self.payload.keys() and len(self.navigator)>0:
				self.navigator = self.navigator.filter(session__session_id=self.payload['sessionid'])

			self.create_menu()
		except Exception as e:
			lgr.critical('An error getting the page because of the Error: %s' % e)
			self.create_menu(level=0, group_select=96, access_point='SYSTEM')#Unexpected input

		return self.view_data


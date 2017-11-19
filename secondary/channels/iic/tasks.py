from django.shortcuts import render
from secondary.channels.iic.models import *
from secondary.channels.iic.backend.wrappers import *
from django.db.models import Q
import operator
from django.core.validators import validate_email, URLValidator
from django.core.exceptions import ValidationError

import logging
lgr = logging.getLogger('iic')

class Generator:
        def validateEmail(self, email):
                try:
                        validate_email(str(email))
                        return True
                except ValidationError:
                        return False

        def validateURL(self, url):
		validate = URLValidator() 
                try:
                        validate(str(url))
                        return True
                except ValidationError:
                        return False



	def section_generator(self, payload, this_page_inputs):
		this_page = {}
		menu_page_group = None
		try:
			lgr.info('Starting Interface: %s' % this_page_inputs)

			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			if 'payment_method' in payload.keys():
				this_page_inputs = this_page_inputs.filter(Q(payment_method__name=payload['payment_method'])|Q(payment_method=None))

			lgr.info('This Page Inputs: %s' % this_page_inputs)
			#Add Interface for an Institution
			if 'institution_id' in payload.keys() and payload['institution_id'] not in ["",None,'None']:
				this_page_inputs = this_page_inputs.filter(Q(institution=None)|Q(institution__id=payload['institution_id']))
			elif gateway_profile.institution is not None:
				this_page_inputs = this_page_inputs.filter(Q(institution=None)|Q(institution=gateway_profile.institution))
			else:
				this_page_inputs = this_page_inputs.filter(institution=None)

			#Add Interface for a product_type
			if 'product_item_id' in payload.keys() and payload['product_item_id'] not in ["",None,'None']:
				product_item = ProductItem.objects.get(id=payload['product_item_id'])
				this_page_inputs = this_page_inputs.filter(Q(product_type=None)|Q(product_type=product_item.product_type))
			elif 'product_type_id' in payload.keys() and payload['product_type_id'] not in ["",None,'None']:
				this_page_inputs = this_page_inputs.filter(Q(product_type=None)|Q(product_type__id=payload['product_type_id']))
			else:
				this_page_inputs = this_page_inputs.filter(product_type=None)
			lgr.info('This Page Inputs: %s' % this_page_inputs)


			#Check if trigger Exists
			if 'trigger' in payload.keys():
				triggers = str(payload['trigger'].strip()).split(',')
				lgr.info('Triggers: %s' % triggers)
				trigger_list = Trigger.objects.filter(name__in=triggers)
				this_page_inputs = this_page_inputs.filter(Q(trigger__in=trigger_list)|Q(trigger=None))
				#Eliminate none matching trigger list
				for i in this_page_inputs:
					if i.trigger.all().exists():
						if False in [trigger_list.filter(id=t.id).exists() for t in i.trigger.all()]:
							this_page_inputs = this_page_inputs.filter(~Q(id=i.id))

			else:
				this_page_inputs = this_page_inputs.filter(Q(trigger=None))
				
			lgr.info('This Page Inputs: %s' % this_page_inputs)

			for input in this_page_inputs:
				input_page = input.page
				menu_page_group = input_page.page_group
				menu_page_group_level = input_page.page_group.item_level
	
				var = input.input_variable
				if menu_page_group_level not in this_page.keys():
					page_group_input_var = [menu_page_group.name, menu_page_group.icon]
					this_page[menu_page_group_level] = {'section_var': page_group_input_var }
				if menu_page_group_level in this_page.keys() and input_page.item_level not in this_page[menu_page_group_level].keys():

					page_input_var = [input_page.name, input_page.icon]
					this_page[menu_page_group_level][input_page.item_level] = {'page_var': page_input_var }
				if menu_page_group_level in this_page.keys() and input_page.item_level in this_page[menu_page_group_level].keys() and \
					 input_page.name not in this_page[menu_page_group_level][input_page.item_level].keys():
	
					this_page[menu_page_group_level][input_page.item_level][input_page.name] = {}
				if menu_page_group_level in this_page.keys() and input_page.item_level in this_page[menu_page_group_level].keys() and \
					 input_page.name in this_page[menu_page_group_level][input_page.item_level].keys() and \
					 input.page_input_group.item_level not in this_page[menu_page_group_level][input_page.item_level][input_page.name].keys():
	
					group_var = input.page_input_group.input_variable
					group_var_service = group_var.service.name if group_var.service else None
					#page_input_group_input_var = [group_var.name, group_var.variable_type.variable, group_var.validate_min, group_var.validate_max, group_var.variable_kind, group_var.default_value, input.page_input_group.style, input.page_input_group.section_size, input.page_input_group.icon,input.page_input_group.auto_submit, False, input.page_input_group.section_height, group_var_service]
					page_input_group_input_var = [input.page_input_group.name, group_var.variable_type.variable, group_var.validate_min, group_var.validate_max, group_var.name, group_var.default_value,  input.page_input_group.icon, input.page_input_group.section_size, group_var.variable_kind, input.page_input_group.auto_submit, input.page_input_group.style, group_var_service, input.page_input_group.section_height]

	
					this_page[menu_page_group_level][input_page.item_level][input_page.name][input.page_input_group.item_level] = {input.page_input_group.name: {'input_var': Wrappers().fill_input_variables(page_input_group_input_var, payload) } }
				if menu_page_group_level in this_page.keys() and input_page.item_level in this_page[menu_page_group_level].keys() and \
					input_page.name in this_page[menu_page_group_level][input_page.item_level].keys() and \
					input.page_input_group.item_level in this_page[menu_page_group_level][input_page.item_level][input_page.name].keys() and \
					input.page_input_group.name in this_page[menu_page_group_level][input_page.item_level][input_page.name][input.page_input_group.item_level].keys() and \
					input.item_level not in this_page[menu_page_group_level][input_page.item_level][input_page.name][input.page_input_group.item_level][input.page_input_group.name].keys():

					var_service = var.service.name if var.service else None
					this_page[menu_page_group_level][input_page.item_level][input_page.name][input.page_input_group.item_level][input.page_input_group.name][input.item_level] = \
					 [input.page_input, var.variable_type.variable, var.validate_min, var.validate_max, var.name, var.default_value, input.icon, input.section_size, var.variable_kind, True,input.style, var_service, input.section_height]
	
				try: this_page[menu_page_group_level][input_page.item_level][input_page.name][input.page_input_group.item_level][input.page_input_group.name][input.item_level] = \
				 Wrappers().fill_input_variables(this_page[menu_page_group_level][input_page.item_level][input_page.name][input.page_input_group.item_level][input.page_input_group.name][input.item_level], payload)
				except Exception, e: lgr.info('Error Getting Wrapper on Inputs: %s' % e)#pass #Escape sections with similar leveling (item_level)
		except Exception, e:
			lgr.info('Error Generating Section: %s' % e)

		return this_page

	def all_pages_generator(self, payload, this_page_inputs):
		page_groups = {}
		try:
			lgr.info('Starting All Pages')
			for this_input in this_page_inputs:
				a_page = this_input.page
				lgr.info("Page: %s" % a_page.name)
				if a_page.page_group.item_level in page_groups and len(page_groups[a_page.page_group.item_level])>0:
					if a_page.page_group.name in page_groups[a_page.page_group.item_level].keys() and len(page_groups[a_page.page_group.item_level][a_page.page_group.name])>0:
						page_groups[a_page.page_group.item_level][a_page.page_group.name][a_page.item_level] = [ a_page.name, a_page.icon ]
					else:
						page_groups[a_page.page_group.item_level][a_page.page_group.name] = {a_page.item_level:{}}
						page_groups[a_page.page_group.item_level][a_page.page_group.name][a_page.item_level] = [ a_page.name, a_page.icon ]		
				else:
					page_groups[a_page.page_group.item_level] = {}
					page_groups[a_page.page_group.item_level][a_page.page_group.name] = {}
					page_groups[a_page.page_group.item_level][a_page.page_group.name][a_page.item_level] =  [ a_page.name, a_page.icon ]

		except Exception, e:
			lgr.info('Error Generating All Pages: %s' % e)

		return page_groups
		
class System(Generator):
        def redirect(self, payload, node_info):
                try:
			if 'redirect' in payload.keys():
				if self.validateURL(payload['redirect']):
					log.info('A valid URL not allowed: %s' % payload['redirect'])
					payload['response'] = '/'
				else:
					payload['response'] = payload['redirect']
			
                        elif 'redirect' not in payload.keys() and payload['SERVICE'] == 'LOGIN':
                                payload['response'] = '/index/'
                        payload['response_status'] = '00'
                except Exception, e:
                        payload['response_status'] = '96'
                        lgr.info("Error on Login: %s" % e)
                return payload

	def get_interface(self, payload, node_info):
		try:
			lgr.info('Get Interface: %s' % payload)
			gui = {}
			
			#This Page
                        gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			lgr.info('Started This Page Inputs')
			#this_page_inputs = PageInput.objects.filter(Q(page__service__name=payload['SERVICE']),\

			'''
			this_page_inputs = PageInput.objects.filter( Q(page__service__name=payload['SERVICE']),\
					 Q(page_input_status__name='ACTIVE'), Q(access_level__name=payload['access_level']), \
					 Q(page__access_level__name=payload['access_level']), Q(channel__id=payload['chid']), ~Q(page__item_level=0), \
					 Q(page__page_group__gateway=gateway_profile.gateway) |Q(page__page_group__gateway=None),\
					 Q(page_input_group__gateway=gateway_profile.gateway) |Q(page_input_group__gateway=None),\
					 Q(page__gateway=gateway_profile.gateway) |Q(page__gateway=None),\
					 Q(gateway=gateway_profile.gateway) |Q(gateway=None)).\
					prefetch_related('trigger','page','access_level','institution','input_variable','page_input_group','gateway','channel','payment_method')

			'''

			this_page_inputs = PageInput.objects.filter( Q(page__service__name=payload['SERVICE']),Q(page_input_status__name='ACTIVE'),\
					 Q(Q(access_level=gateway_profile.access_level)|Q(access_level=None)),\
					 Q(Q(page__access_level=gateway_profile.access_level)|Q(page__access_level=None)),\
					 Q(Q(profile_status=gateway_profile.status)|Q(profile_status=None)),\
					 Q(Q(page__profile_status=gateway_profile.status)|Q(page__profile_status=None)),\
					 Q(channel__id=payload['chid']), ~Q(page__item_level=0), \
					 Q(page__page_group__gateway=gateway_profile.gateway) |Q(page__page_group__gateway=None),\
					 Q(page_input_group__gateway=gateway_profile.gateway) |Q(page_input_group__gateway=None),\
					 Q(page__gateway=gateway_profile.gateway) |Q(page__gateway=None),\
					 Q(gateway=gateway_profile.gateway) |Q(gateway=None)).\
					prefetch_related('trigger','page','access_level','institution','input_variable','page_input_group','gateway','channel','payment_method')
			#			 Q(page__access_level=profile[0].access_level) |Q(page__access_level__name='SYSTEM'), \
			#If a page input has a page_list with on of the pages on a none zero item_level, the section will be previewed on DASHBOARD (START SERVICE)

			gui['this_page_inputs'] = self.section_generator(payload, this_page_inputs)
			gui['all_pages'] = self.all_pages_generator(payload, this_page_inputs)

			payload['response'] = gui
			payload['response_status'] = '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error Fetching Interface: %s" % e)
		return payload

	def get_section(self, payload, node_info):
		try:
			lgr.info('Get Interface: %s' % payload)
			gui = {}
			
			#This Page
                        gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

			lgr.info('Started This Page Inputs')
			'''
			this_page_inputs = PageInput.objects.filter(Q(page__service__name=payload['SERVICE']),Q(page_input_status__name='ACTIVE'),\
					 Q(access_level__name=payload['access_level']), Q(page__access_level__name=payload['access_level']),\
					 Q(channel__id=payload['chid']), Q(page_input_group__gateway=gateway_profile.gateway) |Q(page_input_group__gateway=None),\
					 Q(page__gateway=gateway_profile.gateway) |Q(page__gateway=None),Q(gateway=gateway_profile.gateway) |Q(gateway=None)).\
					prefetch_related('trigger','page','access_level','institution','input_variable','page_input_group','gateway','channel','payment_method')
			'''
			this_page_inputs = PageInput.objects.filter(Q(page__service__name=payload['SERVICE']),Q(page_input_status__name='ACTIVE'),\
					 Q(Q(access_level=gateway_profile.access_level)|Q(access_level=None)),\
					 Q(Q(page__access_level=gateway_profile.access_level)|Q(page__access_level=None)),\
					 Q(Q(profile_status=gateway_profile.status)|Q(profile_status=None)),\
					 Q(Q(page__profile_status=gateway_profile.status)|Q(page__profile_status=None)),\
					 Q(channel__id=payload['chid']), Q(page_input_group__gateway=gateway_profile.gateway) |Q(page_input_group__gateway=None),\
					 Q(page__gateway=gateway_profile.gateway) |Q(page__gateway=None),Q(gateway=gateway_profile.gateway) |Q(gateway=None)).\
					prefetch_related('trigger','page','access_level','institution','input_variable','page_input_group','gateway','channel','payment_method')


			gui['this_page_inputs'] = self.section_generator(payload, this_page_inputs)

			payload['response'] = gui
			payload['response_status'] = '00'
		except Exception, e:
			payload['response_status'] = '96'
			lgr.info("Error Fetching Interface: %s" % e)
		return payload

class Registration(System):
	def runItems(self):
		import random
		import string
		chars = string.ascii_letters + string.punctuation + string.digits

		rnd = random.SystemRandom()
		s = ''.join(rnd.choice(chars) for i in range(20))
		lgr.info('Task: %s' % s)
		return s

class Trade(System):
	pass

class Payments(System):
	pass



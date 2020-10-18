from django.shortcuts import render
from secondary.channels.iic.models import *
from secondary.channels.iic.backend.wrappers import *
from django.db.models import Q
import operator
from django.core.validators import validate_email, URLValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from functools import reduce

import logging

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

	def section_generator(self, payload, this_page_inputs, node_info):
		this_page = {}
		menu_page_group = None
		lgr = node_info.log
		try:
			#lgr.info('Starting Interface: %s' % this_page_inputs)

			gateway_profile = GatewayProfile.objects.using('read').get(id=payload['gateway_profile_id'])

			if 'payment_method' in payload.keys():
				payment_method_list = payload['payment_method'].split(',')
				this_page_inputs = this_page_inputs.filter(
				Q(payment_method__name__in=payment_method_list) | Q(payment_method=None))

			#lgr.info('This Page Inputs: %s' % this_page_inputs)
			# Add Interface for an Institution
			if 'institution_id' in payload.keys() and payload['institution_id'] not in ["", None, 'None']:
				this_page_inputs = this_page_inputs.filter(
					Q(institution=None) | Q(institution__id=payload['institution_id']))
			elif gateway_profile.institution is not None:
				this_page_inputs = this_page_inputs.filter(
				Q(institution=None) | Q(institution=gateway_profile.institution))
			else:
				this_page_inputs = this_page_inputs.filter(institution=None)

			# Add Interface for a product_type
			if 'product_item_id' in payload.keys() and payload['product_item_id'] not in ["", None, 'None']:
				product_item = ProductItem.objects.using('read').get(id=payload['product_item_id'])
				this_page_inputs = this_page_inputs.filter(
				Q(product_type=None) | Q(product_type=product_item.product_type))
			elif 'product_type_id' in payload.keys() and payload['product_type_id'] not in ["", None, 'None']:
				this_page_inputs = this_page_inputs.filter(
				Q(product_type=None) | Q(product_type__id=payload['product_type_id']))
			else:
				this_page_inputs = this_page_inputs.filter(product_type=None)
				#lgr.info('This Page Inputs:1 %s' % this_page_inputs)

			# Check if trigger Exists
			if 'trigger' in payload.keys():
				triggers = str(payload['trigger'].strip()).split(',')
				#lgr.info('Triggers: %s' % triggers)
				trigger_list = Trigger.objects.using('read').filter(name__in=triggers).distinct()
				this_page_inputs = this_page_inputs.filter(Q(trigger__in=trigger_list) | Q(trigger=None))
				# Eliminate none matching trigger list
				for i in this_page_inputs:
					if i.trigger.all().exists():
						if i.trigger.all().count() == trigger_list.count():
							if False in [i.trigger.filter(id=t.id).exists() for t in trigger_list.all()]:
								this_page_inputs = this_page_inputs.filter(~Q(id=i.id))
						else:
							this_page_inputs = this_page_inputs.filter(~Q(id=i.id))
			else:
				this_page_inputs = this_page_inputs.filter(Q(trigger=None))

			# FIlter Enrollments
			enrollment_list = Enrollment.objects.using('read').filter(profile=gateway_profile.user.profile,
								expiry__gte=timezone.now())
			if enrollment_list.exists():
				this_page_inputs = this_page_inputs.filter(
					Q(enrollment_type_included__in=[e.enrollment_type for e in enrollment_list]) | Q(
					enrollment_type_included=None), \
					~Q(enrollment_type_excluded__in=[e.enrollment_type for e in enrollment_list]))
			else:
				this_page_inputs = this_page_inputs.filter(enrollment_type_included=None)

			#lgr.info('This Page Inputs:2 %s' % this_page_inputs)

			for input in this_page_inputs:
				input_page = input.page
				menu_page_group = input_page.page_group
				menu_page_group_level = input_page.page_group.item_level

				var = input.input_variable
				if menu_page_group_level not in this_page.keys():
					menu_page_group_icon = menu_page_group.icon.icon if menu_page_group.icon else None
					page_group_input_var = [menu_page_group.name, menu_page_group_icon]
					this_page[menu_page_group_level] = {'section_var': page_group_input_var}
				if menu_page_group_level in this_page.keys() and input_page.item_level not in this_page[
					menu_page_group_level].keys():
					input_page_icon = input_page.icon.icon if input_page.icon else None
					page_input_var = [input_page.name, input_page_icon]
					this_page[menu_page_group_level][input_page.item_level] = {'page_var': page_input_var}
				if menu_page_group_level in this_page.keys() and input_page.item_level in this_page[
					menu_page_group_level].keys() and \
					input_page.name not in this_page[menu_page_group_level][input_page.item_level].keys():
					this_page[menu_page_group_level][input_page.item_level][input_page.name] = {}
				if menu_page_group_level in this_page.keys() and input_page.item_level in this_page[
					menu_page_group_level].keys() and \
					input_page.name in this_page[menu_page_group_level][input_page.item_level].keys() and \
					input.page_input_group.item_level not in \
					this_page[menu_page_group_level][input_page.item_level][input_page.name].keys():
					group_var = input.page_input_group.input_variable
					group_var_service = group_var.service.name if group_var.service else None
					page_input_group_icon = input.page_input_group.icon.icon if input.page_input_group.icon else None
					bind_position = input.page_input_group.bind_position.name if input.page_input_group.bind_position else None

					# page_input_group_input_var = [group_var.name, group_var.variable_type.variable, group_var.validate_min, group_var.validate_max, group_var.variable_kind, group_var.default_value, input.page_input_group.style, input.page_input_group.section_size, input.page_input_group.icon,input.page_input_group.auto_submit, False, input.page_input_group.section_height, group_var_service]
					page_input_group_input_var = [input.page_input_group.name, group_var.variable_type.variable,
						  group_var.validate_min, group_var.validate_max, group_var.name,
						  group_var.default_value, page_input_group_icon,
						  input.page_input_group.section_size, group_var.variable_kind,
						  input.page_input_group.auto_submit, input.page_input_group.style,
						  group_var_service, input.page_input_group.section_height,
						  bind_position, group_var.details]

					this_page[menu_page_group_level][input_page.item_level][input_page.name][
					input.page_input_group.item_level] = {input.page_input_group.name: {
					'input_var': Wrappers().fill_input_variables(page_input_group_input_var, payload, node_info)}}
				if menu_page_group_level in this_page.keys() and input_page.item_level in this_page[
				menu_page_group_level].keys() and \
				input_page.name in this_page[menu_page_group_level][input_page.item_level].keys() and \
				input.page_input_group.item_level in this_page[menu_page_group_level][input_page.item_level][
				input_page.name].keys() and \
				input.page_input_group.name in \
				this_page[menu_page_group_level][input_page.item_level][input_page.name][
				input.page_input_group.item_level].keys() and \
				input.item_level not in \
				this_page[menu_page_group_level][input_page.item_level][input_page.name][
				input.page_input_group.item_level][input.page_input_group.name].keys():
					var_service = var.service.name if var.service else None
					input_icon = input.icon.icon if input.icon else None
					input_bind_position = input.bind_position.name if input.bind_position else None

					this_page[menu_page_group_level][input_page.item_level][input_page.name][
					input.page_input_group.item_level][input.page_input_group.name][input.item_level] = \
					[input.page_input, var.variable_type.variable, var.validate_min, var.validate_max, var.name,
					 var.default_value, input_icon, input.section_size, var.variable_kind, var.required, input.style,
					 var_service, input.section_height, input_bind_position, var.details]

				try:
					this_page[menu_page_group_level][input_page.item_level][input_page.name][
					input.page_input_group.item_level][input.page_input_group.name][input.item_level] = \
					Wrappers().fill_input_variables(
						this_page[menu_page_group_level][input_page.item_level][input_page.name][
						input.page_input_group.item_level][input.page_input_group.name][input.item_level],
						payload, node_info)
				except Exception as e:
					lgr.info('Error Getting Wrapper on Inputs: %s' % e)  # pass #Escape sections with similar leveling (item_level)
		except Exception as e:
			lgr.info('Error Generating Section: %s' % e)

		return this_page

	def all_pages_generator(self, payload, this_page_inputs, node_info):

		lgr = node_info.log
		page_groups = {}
		try:
			#lgr.info('Starting All Pages')
			for this_input in this_page_inputs:
				a_page = this_input.page
				#lgr.info("Page: %s" % a_page.name)
				if a_page.page_group.item_level in page_groups and len(page_groups[a_page.page_group.item_level]) > 0:
					if a_page.page_group.name in page_groups[a_page.page_group.item_level].keys() and len(
					page_groups[a_page.page_group.item_level][a_page.page_group.name]) > 0:
						a_page_icon = a_page.icon.icon if a_page.icon else None
						page_groups[a_page.page_group.item_level][a_page.page_group.name][a_page.item_level] = [
						a_page.name, a_page_icon]
					else:
						a_page_icon = a_page.icon.icon if a_page.icon else None
						page_groups[a_page.page_group.item_level][a_page.page_group.name] = {a_page.item_level: {}}
						page_groups[a_page.page_group.item_level][a_page.page_group.name][a_page.item_level] = [
						a_page.name, a_page_icon]
				else:
					a_page_icon = a_page.icon.icon if a_page.icon else None
					page_groups[a_page.page_group.item_level] = {}
					page_groups[a_page.page_group.item_level][a_page.page_group.name] = {}
					page_groups[a_page.page_group.item_level][a_page.page_group.name][a_page.item_level] = [a_page.name,
														a_page_icon]

		except Exception as e:
			lgr.info('Error Generating All Pages: %s' % e)

		return page_groups


class System(Generator):
	def update_role_permissions(self, payload, node_info):
		lgr = node_info.log
		try:
			'''
			{"action": "Enable", "role_id": "1", "role_rights": "1,2,3,4"}
			'''
			lgr.info('Update Role Permission Payload: %s' % payload)
			role_action = RoleAction.objects.get(name='VIEW') if payload.get('action') == 'Enable' else None 
			role = Role.objects.get(id=payload.get('role_id'))
			role_right_list = RoleRight.objects.filter(id__in=payload.get('role_rights').split(','))
			lgr.info('Role Action: %s | Role: %s | Rights: %s' % (role_action, role, role_right_list))
			for right in role_right_list:
				#Has Race Condition
				permission = RolePermission.objects.get_or_create(role=role, role_right=right)
				lgr.info('Permission: %s' % permission)
				if role_action:
					lgr.info('Adding')
					permission.role_action.add(role_action)
				else:
					lgr.info('Clearing')
					permission.role_action.clear()

			payload['response'] = 'Role Permissions Updated'
			payload['response_status'] = '00'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Update Role Permissions: %s" % e)
		return payload


	def redirect(self, payload, node_info):

		lgr = node_info.log
		try:
			if 'redirect' in payload.keys():
				if self.validateURL(payload['redirect']):
					log.info('A valid URL not allowed: %s' % payload['redirect'])
					payload['response'] = '/'
				else:
					payload['response'] = payload['redirect']

			elif 'redirect' not in payload.keys() and payload['SERVICE'] in ['LOGIN','CONFIRM ONE TIME PASSWORD','SET PASSWORD','CONFIRM ONE TIME PIN']:
				payload['response'] = '/index/'
			payload['response_status'] = '00'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error on Login: %s" % e)
		return payload

	def get_interface(self, payload, node_info):

		lgr = node_info.log
		try:
			lgr.info('Get Interface: %s' % payload)
			gui = {}

			# This Page
			gateway_profile = GatewayProfile.objects.using('read').get(id=payload['gateway_profile_id'])

			#lgr.info('Started This Page Inputs')
			this_page_inputs = PageInput.objects.using('read').filter(Q(page__service__name=payload['SERVICE']),
							Q(page_input_status__name='ACTIVE'), \
							Q(Q(access_level=gateway_profile.access_level) | Q(
								access_level=None)), \
							Q(Q(page__access_level=gateway_profile.access_level) | Q(
								page__access_level=None)), \
							Q(Q(profile_status=gateway_profile.status) | Q(
								profile_status=None)), \
							Q(Q(page__profile_status=gateway_profile.status) | Q(
								page__profile_status=None)), \
							Q(channel__id=payload['chid']), ~Q(page__item_level=0), \
							Q(page__page_group__gateway=gateway_profile.gateway) | Q(
								page__page_group__gateway=None), \
							Q(page_input_group__gateway=gateway_profile.gateway) | Q(
								page_input_group__gateway=None), \
							Q(page__gateway=gateway_profile.gateway) | Q(
								page__gateway=None), \
							Q(gateway=gateway_profile.gateway) | Q(gateway=None)). \
					prefetch_related('trigger', 'page', 'access_level', 'institution', 'input_variable', 'page_input_group',
						 'gateway', 'channel', 'payment_method')

			#Structure Filters | If gateway has structure, only load where structure exists
			if gateway_profile.gateway.structure:
				this_page_inputs = this_page_inputs.filter(structure=gateway_profile.gateway.structure)
			else:
				this_page_inputs = this_page_inputs.filter(structure=None)
			#Template Filters | If institution has template, only load where template exists or where institution is explicitly defined
			if 'template_enabled' in payload.keys() and payload['template_enabled']:
				if gateway_profile.institution and gateway_profile.institution.template:
					this_page_inputs = this_page_inputs.filter(template=gateway_profile.institution.template)
				elif 'institution_id' in payload.keys(): #Explicitly defined institution
					institution = Institution.objects.using('read').get(id=payload['institution_id'])
					if institution.template: this_page_inputs = this_page_inputs.filter(template=institution.template)
					else:this_page_inputs = this_page_inputs.filter(template=None)
				else:
					this_page_inputs = this_page_inputs.filter(template=None)

			#lgr.info('This Page Inputs 1L %s' % this_page_inputs)
			#Role Filters
			if gateway_profile.role:
				role_permission = RolePermission.objects.using('read').filter(role=gateway_profile.role)

				pages = {}
				for permission in role_permission:
					for page in permission.role_right.page.all():
						if page not in pages.keys():
							pages[page] = []
							for action in permission.role_action.all(): 
								if action not in pages[page]: pages[page].append(action)
				if pages:
					query = reduce(operator.or_, ( Q(Q(page=k),Q(Q(role_action=None)|Q(role_action__in=v))) for k,v in pages.items() ))
					#lgr.info('Query: %s' % query)
					this_page_inputs = this_page_inputs.filter(query)
				else:
					this_page_inputs = this_page_inputs.none()

			#lgr.info('This Page Inputs 2L %s' % this_page_inputs)
			gui['this_page_inputs'] = self.section_generator(payload, this_page_inputs, node_info)
			gui['all_pages'] = self.all_pages_generator(payload, this_page_inputs, node_info)

			payload['response'] = gui
			payload['response_status'] = '00'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error Fetching Interface: %s" % e)
		return payload

	def get_section(self, payload, node_info):
		lgr = node_info.log
		try:
			#lgr.info('Get Interface: %s' % payload)
			gui = {}

			# This Page
			gateway_profile = GatewayProfile.objects.using('read').get(id=payload['gateway_profile_id'])

			#lgr.info('Started This Page Inputs')
			this_page_inputs = PageInput.objects.using('read').filter(Q(page__service__name=payload['SERVICE']),
							Q(page_input_status__name='ACTIVE'), \
							Q(Q(access_level=gateway_profile.access_level) | Q(
								access_level=None)), \
							Q(Q(page__access_level=gateway_profile.access_level) | Q(
								page__access_level=None)), \
							Q(Q(profile_status=gateway_profile.status) | Q(
								profile_status=None)), \
							Q(Q(page__profile_status=gateway_profile.status) | Q(
								page__profile_status=None)), \
							Q(channel__id=payload['chid']),
							Q(page_input_group__gateway=gateway_profile.gateway) | Q(
								page_input_group__gateway=None), \
							Q(page__gateway=gateway_profile.gateway) | Q(
								page__gateway=None),
							Q(gateway=gateway_profile.gateway) | Q(gateway=None)). \
						prefetch_related('trigger', 'page', 'access_level', 'institution', 'input_variable', 'page_input_group',
								 'gateway', 'channel', 'payment_method')

			gui['this_page_inputs'] = self.section_generator(payload, this_page_inputs, node_info)

			payload['response'] = gui
			payload['response_status'] = '00'
		except Exception as e:
			payload['response_status'] = '96'
			lgr.info("Error Fetching Interface: %s" % e)
		return payload


class Registration(System):
	pass

class Trade(System):
	pass


class Payments(System):
	pass

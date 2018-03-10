from secondary.channels.vcs.models import *
from primary.core.api.views import ServiceCall

from django.db.models import Count, Avg, Max, Min, Q, F
from django.utils import timezone
from datetime import datetime, timedelta

import operator, json, re, locale, string
from decimal import Decimal


import logging
lgr = logging.getLogger('vcs')
class Wrappers:
	def sale_charge_bill(self, balance_bf, product_item, gateway):
		from secondary.erp.pos.models import SaleCharge
		#Sale Charge Item Bill entry
		sale_charge = SaleCharge.objects.filter(Q(min_amount__lt=balance_bf,max_amount__gt=balance_bf,credit=False),\
						Q(Q(product_type=product_item.product_type)|Q(product_type=None)),\
						Q(Q(institution=product_item.institution)|Q(institution=None)),\
						Q(Q(gateway=gateway)|Q(gateway=None)))

		def get_balance(balance_bf, item, product_item):
			if item.currency <> product_item.currency:
				forex = Forex.objects.filter(base_currency=product_item.currency, quote_currency=item.currency)
				total = Decimal(0)
				if forex.exists():
					total = balance_bf/forex[0].exchange_rate

				balance_bf = balance_bf + total
				lgr.info('Forex Calculate balance_bf to %s|from: %s| %s' % (product_item.currency, item.currency, balance_bf) )

			return balance_bf


		for sc in sale_charge:
			item = sc.sale_charge_type.product_item
			charge = Decimal(0)
			if sc.is_percentage:
				charge = charge + ((sc.charge_value/100)*Decimal(balance_bf))
			else:
				charge_value = get_balance(sc.charge_value, item, product_item)
				charge = charge+charge_value

			balance_bf = balance_bf + charge

		return balance_bf



class PageString(ServiceCall, Wrappers):
	def __init__(self, name=None, app_name='tags'):
		self._registry = {} # model_class class -> admin_class instance
	def get_nav(self, navigator, attrs={}):
		navigator_list = Navigator.objects.filter(Q(session=navigator.session), Q(nav_step=navigator.nav_step),\
			~Q(input_select__in=['']),Q(invalid=False)).order_by('-date_created','-menu__level')

		nav = {}

		'''
		for value in navigator_list:
			if value.input_select in ['00'] or value.menu.level == 0: #Ensure that if menu level is 0, captures data but ends capture(level 0=main menu)
				item[int(value.menu.level)] = value
				break
			elif value.input_select in ['0'] or int(value.menu.level) in item.keys(): #Ensure that any input select to back is not included & Existing keys not replaced[mostly with back 0]
				continue
			else:
				item[int(value.menu.level)] = value

		for key, value in item.items():
			if value.menu.selection_preview == True:
				item_level = value.menu.level + 1
				try:item_list = json.loads(value.item_list)
				except: item_list = []
				if len(item_list) > 0:
					lgr.info('Item List not None: %s|Item Level: %s' % (item_list,item_level) )
					try: input_nav = item_list[int(item[item_level].input_select) - 1]
					except Exception, e:lgr.info('Error on item_list: %s' % e);input_nav = None
				else:
					lgr.info('Item List None')
					try:input_nav = item[item_level].input_select 
					except Exception, e:lgr.info('Error on item_list: %s' % e);input_nav = None
				nav[value.menu.menu_description] = input_nav
		'''
		'''
		for value in navigator_list:
			if value.input_select in ['00'] or value.level == 0: #Ensure that if menu level is 0, captures data but ends capture(level 0=main menu)
				item[value.id] = value
				break
			elif value.input_select in ['0'] or value.id in item.keys(): #Ensure that any input select to back is not included & Existing keys not replaced[mostly with back 0]
				continue
			elif value.menu in [v.menu for v in item.values()]:
				continue
			else:
				item[value.id] = value

		for key, value in item.items():
			#add menu details
			try: 
				details = json.loads(value.menu.details)
				if isinstance(details,dict): nav.update(details)
			except: pass

			if value.menu.selection_preview == True:

				lgr.info('Key: %s | Val: %s' % (key,value))
				item_val = navigator_list.filter(id__gt=value.id).last()
				lgr.info('Item Val: %s' % item_val)
				item_level = item_val.id if item_val else 0
				lgr.info('Item Level: %s' % item_level)
				try:item_list = json.loads(value.item_list)
				except: item_list = []
				lgr.info('Item List: %s' % item_list)
				lgr.info('variable: %s' % value.menu.menu_description)
				if len(item_list) > 0:
					lgr.info('Item List not None: %s|Item Level: %s' % (item_list,item_level) )
					try: 
						lgr.info("Item: %s" % item)
						input_nav = item_list[int(item[item_level].input_select) - 1]
						lgr.info('Input Nav: %s' % input_nav)
					except Exception, e:lgr.info('Error on item_list: %s' % e);input_nav = None
				else:
					lgr.info('Item List None')
					try:input_nav = item[item_level].input_select 
					except Exception, e:lgr.info('Error on item_list: %s' % e);input_nav = None
				if input_nav: nav[value.menu.menu_description] = input_nav
		'''

		def gen_payload(nav, navigator_list, value):
			#add menu details
			try: 
				details = json.loads(value.menu.details)
				if isinstance(details,dict): nav.update(details)
			except: pass

			if value.menu.selection_preview == True:

				lgr.info('Key: %s | Val: %s' % (value.id,value))
				lgr.info('NAvigator: %s' % navigator_list)
				item_val = navigator_list.filter(id__gt=value.id).last()
				lgr.info('Item Val: %s' % item_val)
				item_level = item_val.id if item_val else 0
				lgr.info('Item Level: %s' % item_level)
				try:item_list = json.loads(value.item_list)
				except: item_list = []
				lgr.info('Item List: %s' % item_list)
				lgr.info('variable: %s' % value.menu.menu_description)
				if len(item_list) > 0:
					lgr.info('Item List not None: %s|Item Level: %s' % (item_list,item_level) )
					try: 
						input_nav = item_list[int(navigator_list.get(id=item_level).input_select) - 1]
						lgr.info('Input Nav: %s' % input_nav)
					except Exception, e:
						lgr.info('Error on item_list: %s' % e);
						input_nav = None
				else:
					lgr.info('Item List None')
					try:input_nav = navigator_list.get(id=item_level).input_select 
					except Exception, e:
						lgr.info('Error on item_list: %s' % e);
						input_nav = None
				if input_nav and value.menu.menu_description not in nav.keys(): nav[value.menu.menu_description] = input_nav
			return nav

		for value in navigator_list:
			if value.input_select in ['00'] or value.level == 0: #Ensure that if menu level is 0, captures data but ends capture(level 0=main menu)
				navigator_list = navigator_list.filter(~Q(id__lt=value.id))
				nav = gen_payload(nav,navigator_list,value)
				break
			elif value.input_select in ['0']: #Ensure that any input select to back is not included & Existing keys not replaced[mostly with back 0]
				navigator_list = navigator_list.filter(~Q(Q(menu=value.menu),~Q(id=value.id)))
				#nav = gen_payload(nav,navigator_list,value)
				continue
			else:
				nav = gen_payload(nav,navigator_list,value)

		lgr.info('Nav: %s' % nav)
		return nav

	def pagestring(self, navigator, payload, code):
		#Find Variable
		#Process Submit and input not in ['0','00']
		page_string = payload['page_string']
		del payload['page_string']

		payload.update(self.get_nav(navigator))


		if navigator is not None and navigator.menu is not None and navigator.menu.submit == True:
			#payload = {}
			#payload['chid'] = navigator.session.channel.id
			#payload['ip_address'] = 'vcs'

			#Get Menu Payload items
			if code[0].institution:payload['institution_id'] = code[0].institution.id

			gateway_profile = navigator.session.gateway_profile
			if gateway_profile is None: #If profile is unexistent
				gateway_profile_list = GatewayProfile.objects.filter(gateway =code[0].gateway,user__username='System@User', status__name__in=['ACTIVATED'])
                	        if len(gateway_profile_list) > 0 and gateway_profile_list[0].user.is_active:
					gateway_profile = gateway_profile_list[0]

			payload = dict(map(lambda (key, value):(string.lower(key),json.dumps(value) if isinstance(value, dict) else str(value)), payload.items()))
			payload = self.api_service_call(navigator.menu.service, gateway_profile, payload)
			item = ''
			if 'response' in payload.keys():
				for key, value in payload['response'].items():
					if navigator.session.channel.name == 'IVR':
						item = '%s\n%s is %s' % (item, key.replace('_',' ').title(), value)
					elif navigator.session.channel.name == 'USSD':
						item = '%s\n%s: %s' % (item, key.replace('_',' ').title(), value)
			if '[RESPONSE]' in page_string:
				page_string = page_string.replace('[RESPONSE]',item)

		variables = re.findall("\[(.*?)\]", page_string)
		for v in variables:
			variable_key, variable_val = None, None
		        n = v.find("=")
		        if n >=0:
		                variable_key = v[:n]
                		variable_val = v[(n+1):].strip()
		        else:
                		variable_key = v

			lgr.info('\n\n\n\n Variable Found: Key:%s|Val: %s\n\n\n\n' % (variable_key, variable_val))
			if variable_key is not None:
					
				if variable_key == 'RESPONSE_SUMMARY':
					from primary.core.administration.models import ResponseStatus
					SUCCESS,ERROR = variable_val.split("|")
					item = ''
					if 'response_status' in payload.keys() and payload['response_status'] == '00':
						success_list = SUCCESS.split('@')
						lgr.info('success_list: %s' % success_list)
						if len(success_list)>1 and len(success_list[1].split(' '))==1:
							try:item =  payload['response'][success_list[1]]
							except: item = SUCCESS
						else:item = SUCCESS
					else:
						if ERROR == 'RESPONSE':
							#ERR = ResponseStatus.objects.get(response=payload['response_status']).description
							ERR = payload['last_response']
							#Success message Can be used to mask error as well
							success_list = SUCCESS.split('@')
							lgr.info('success_list: %s' % success_list)
							if len(success_list)>1 and len(success_list[1].split(' '))==1:
								try:item =  payload['response'][success_list[1]]
								except: item = ERR
							else:item = ERR 
						else:item = ERROR

					page_string = page_string.replace('['+v+']', item)

				elif variable_key == 'session_variable':
					item = ''

					params = payload
					new_payload = payload.copy()
					new_payload.update(params)
					lgr.info('New Payload: %s' % new_payload)
					if str(variable_val) in new_payload.keys():
						item = str(new_payload[str(variable_val)])

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'SELECTION':
					item = ''
					for key, value in self.get_nav(navigator, {'selection':True}).items():
						key = key.replace("_"," ")
						if navigator.session.channel.name == 'IVR':
							item = '%s\n%s is %s.' % (item, key.title(), value)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s.' % (item, key.title(), value)

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'PRODUCT TYPE':
					from products.regix.models import Product
					trf = Product.objects.filter(institution_till__institution=code[0].institution).values('product_type__name').annotate()
					item = ''
					item_list = []
					count = 1
					for i in trf:
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, i['product_type__name'], count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, i['product_type__name'])
						item_list.append(i['product_type__name'])
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()
					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'CITY':
					from products.regix.models import Product
					trf = Product.objects.filter(institution_till__institution=code[0].institution).values('institution_till__city').annotate()
					item = ''
					item_list = []
					count = 1
					for i in trf:
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, i['institution_till__city'], count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, i['institution_till__city'])
						item_list.append(i['institution_till__city'])
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'TILL':
					from products.regix.models import Product
					trf = Product.objects.filter(institution_till__institution=code[0].institution, institution_till__city=payload['CITY']).values('institution_till__name').annotate()#Filters to till with tiers. Otherwise, only tills in the institution
					item = ''
					item_list = []
					count = 1
					for i in trf:
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, i['institution_till__name'], count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, i['institution_till__name'])
						item_list.append(i['institution_till__name'])
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'PREVIEW':
					preview_list = ['USSD menu inline','Subscribe for SMS']
					item = ''
					item_list = []
					count = 1
					for i in preview_list:
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, i, count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, i)
						item_list.append(i)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'ESERVICE':
					from primary.core.bridge.models import EnrolledService
					es = EnrolledService.objects.filter(till__institution=code[0].institution,institution__business_number=payload['BUSINESS NUMBER'], institution__status__name='ACTIVE').values('name').annotate()
					item = ''
					item_list = []
					count = 1
					for i in es:
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, i['name'], count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, i['name'])
						item_list.append(i['name'])
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'INSTITUTION_NAME':
					from products.regix.models import EnrolledService
					es = EnrolledService.objects.filter(till__institution=code[0].institution,institution__business_number=payload['BUSINESS NUMBER'][:6],\
							institution__status__name='ACTIVE')
					item = ''
					if len(es)>0:
						item = es[0].institution.name

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'live_bid_details':
					from thirdparty.bidfather.models import BidRequirement, BidRequirementApplication

					params = payload
					gateway_profile_list = GatewayProfile.objects.filter(gateway=code[0].gateway, msisdn__phone_number=payload['msisdn'])

					bid_requirement = BidRequirement.objects.get(id=params['bid_requirement_id'])

					item = ''
					item = '%s-%s' % (bid_requirement.quantity, bid_requirement.bid.name)

					bid_requirement_application = BidRequirementApplication.objects.filter(bid_requirement__id=params['bid_requirement_id'],\
									 bid_application__institution__in=[i.institution for i in gateway_profile_list])

					if bid_requirement_application.exists():
						unit_cost = bid_requirement_application[0].unit_price
		                                cost = '{0:,.2f}'.format(unit_cost) if unit_cost > 0 else None
						item = '%s@%s' % (item, cost)

					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'bid_requirements':
					from thirdparty.bidfather.models import BidRequirement,BidApplication

					params = payload
					bid_application = BidApplication.objects.get(id=params['bid_application_id'])
					bid_requirement = BidRequirement.objects.filter(bid=bid_application.bid).order_by('id')

					'''
					if variable_val not in ['',None]:
						product_item = product_item.filter(product_type__name=variable_val)
					if 'product_type' in params.keys():
						product_item = product_item.filter(product_type__name=params['product_type'])
					'''

					bid_requirement = bid_requirement[:20]
					item = ''
					item_list = []
					count = 1
					for i in bid_requirement:
                                                name = '%s' % (i.name)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, name, count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, name)

						item_list.append(i.id)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'selected_bids':
					from thirdparty.bidfather.models import BidApplication

					params = payload

					gateway_profile_list = GatewayProfile.objects.filter(gateway=code[0].gateway, msisdn__phone_number=payload['msisdn'])

					bid_applications = BidApplication.objects.filter(institution__in=[i.institution for i in gateway_profile_list]).order_by('id')

					'''
					if variable_val not in ['',None]:
						product_item = product_item.filter(product_type__name=variable_val)
					if 'product_type' in params.keys():
						product_item = product_item.filter(product_type__name=params['product_type'])
					'''

					bid_applications = bid_applications[:20]
					item = ''
					item_list = []
					count = 1
					if bid_applications.exists():
						for i in bid_applications:
        	                                        cost = '{0:,.2f}'.format(i.current_total_price)
                	                                name = '%s' % (i.bid.name)
							if navigator.session.channel.name == 'IVR':
								item = '%s\nFor %s, press %s.' % (item, name, count)
							elif navigator.session.channel.name == 'USSD':
								if variable_key == 'product_item_cost':
									item = '%s\n%s:%s-%s' % (item, count, name,cost)
								else:
									#item = '%s\n%s:%s' % (item, count, name)
									item = '%s\n%s:%s-%s' % (item, count, name,cost)

							item_list.append(i.id)
							count+=1
						navigator.item_list = json.dumps(item_list)
						navigator.save()
					else:
						item = 'No Selected Bid Available'

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'created_bids':
					from thirdparty.bidfather.models import Bid

					params = payload

					gateway_profile_list = GatewayProfile.objects.filter(gateway=code[0].gateway, msisdn__phone_number=payload['msisdn'])

					bid = Bid.objects.filter(institution__in=[i.institution for i in gateway_profile_list]).order_by('id')

					'''
					if variable_val not in ['',None]:
						product_item = product_item.filter(product_type__name=variable_val)
					if 'product_type' in params.keys():
						product_item = product_item.filter(product_type__name=params['product_type'])
					'''

					bid = bid[:20]
					item = ''
					item_list = []
					count = 1
					if bid.exists():
						for i in bid:
                	                                name = '%s' % (i.name)
							if navigator.session.channel.name == 'IVR':
								item = '%s\nFor %s, press %s.' % (item, name, count)
							elif navigator.session.channel.name == 'USSD':
								#item = '%s\n%s:%s' % (item, count, name)
								item = '%s\n%s:%s' % (item, count, name)

							item_list.append(i.id)
							count+=1
						navigator.item_list = json.dumps(item_list)
						navigator.save()
					else:
						item = 'No Created Bid Available'

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'live_bids':
					from thirdparty.bidfather.models import BidApplication

					params = payload

					gateway_profile_list = GatewayProfile.objects.filter(gateway=code[0].gateway, msisdn__phone_number=payload['msisdn'])

					bid_applications = BidApplication.objects.filter(institution__in=[i.institution for i in gateway_profile_list],\
								bid__bid_close__gte=timezone.now(),bid__bid_open__lte=timezone.now()).order_by('id')

					'''
					if variable_val not in ['',None]:
						product_item = product_item.filter(product_type__name=variable_val)
					if 'product_type' in params.keys():
						product_item = product_item.filter(product_type__name=params['product_type'])
					'''

					bid_applications = bid_applications[:20]
					item = ''
					item_list = []
					count = 1
					if bid_applications.exists():
						for i in bid_applications:
        	                                        cost = '{0:,.2f}'.format(i.current_total_price) if i.current_total_price else 0
                	                                name = '%s' % (i.bid.name)
							if navigator.session.channel.name == 'IVR':
								item = '%s\nFor %s, press %s.' % (item, name, count)
							elif navigator.session.channel.name == 'USSD':
								item = '%s\n%s:%s-%s' % (item, count, name,cost)

							item_list.append(i.id)
							count+=1
						navigator.item_list = json.dumps(item_list)
						navigator.save()
					else:
						item = 'No live bid Available'

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'survey_top_ten':
					from secondary.erp.survey.models import SurveyResponse

					survey_response = SurveyResponse.objects.filter(item__survey__group__data_name=variable_val,\
							 item__survey__institution__id=code[0].institution.id,\
							 item__survey__status__name='ACTIVE',
							 status__name='ACTIVE').annotate(num_polls=Count('item__id')).order_by('-num_polls')[:10]
					item = ''
					item_list = []
					count = 1
					for i in survey_response:
						name = '%s' % (i.item.name)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, name, count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, name)
						item_list.append(name)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'i_invest.investmentfundinfo':
					from thirdparty.i_invest.models import InvestmentFund

					params = payload

					investmentfund = InvestmentFund.objects.filter(name=params['from_investmentfund'])

					item = ''
					if investmentfund.exists():
						item = '%s' % (investmentfund[0].ussd_info)

					page_string = page_string.replace('['+v+']',item)



				elif variable_key == 'i_invest.investmentfund':
					from thirdparty.i_invest.models import InvestmentFund

					investmentfund = InvestmentFund.objects.filter(status__name='ENABLED').order_by('id')
					item = ''
					item_list = []
					count = 1
					investmentfund = investmentfund[:10]

					for i in investmentfund:
						name = '%s' % (i.name)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, name, count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, name)
						item_list.append(i.name)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'i_invest.sourceoffund':
					from thirdparty.i_invest.models import SourceOfFund

					sourceoffund = SourceOfFund.objects.filter(status__name='ENABLED').order_by('id')
					item = ''
					item_list = []
					count = 1
					sourceoffund = sourceoffund[:10]

					for i in sourceoffund:
						name = '%s' % (i.name)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, name, count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, name)
						item_list.append(i.name)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'i_invest.profile.occupation':
					from thirdparty.i_invest.models import InvestmentProfile

					item = ''

					if navigator.session.gateway_profile and navigator.session.gateway_profile.user.profile.investmentprofile and navigator.session.gateway_profile.user.profile.investmentprofile.occupation:
						item = navigator.session.gateway_profile.user.profile.investmentprofile.occupation.name

					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'i_invest.occupation':
					from thirdparty.i_invest.models import Occupation

					occupation = Occupation.objects.filter(status__name='ENABLED').order_by('id')
					item = ''
					item_list = []
					count = 1
					occupation = occupation[:10]

					for i in occupation:
						name = '%s' % (i.name)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, name, count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, name)
						item_list.append(i.name)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'notification_product':
					from secondary.channels.notify.models import Contact

					contact= Contact.objects.filter(gateway_profile__msisdn__phone_number=payload['msisdn'],\
						product__notification__code__institution__id=code[0].institution.id,\
						product__subscribable=True,status__name='ACTIVE', subscribed=True)
					contact = contact[:10]
					item = ''
					item_list = []
					count = 1
					for i in contact:
                                                name = '%s' % (i.product.name)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, name, count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, name)
						item_list.append(name)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'account_manager_payment_method':

					from secondary.finance.vbs.models import AccountType,AccountManager

					params = payload

					mipay_gateway_profile = GatewayProfile.objects.filter(msisdn__phone_number=payload['msisdn'],gateway__name='MIPAY')

					account_type = AccountManager.objects.get(id=payload['account_manager_id']).dest_account.account_type
					payment_method = account_type.product_item.product_type.payment_method.filter(Q(channel__id=payload['chid'])|Q(channel=None))

					if variable_val == 'Send':
						payment_method = payment_method.filter(send=True)
					elif variable_val == 'Receive':
						payment_method = payment_method.filter(receive=True)


					item = ''
					item_list = []
					count = 1
					for i in payment_method:
						account_balance = None
						if i.name == 'MIPAY' and variable_val <> 'Send' and mipay_gateway_profile.exists():
							session_account_manager = AccountManager.objects.filter(dest_account__account_status__name='ACTIVE',\
									dest_account__profile=mipay_gateway_profile[0].user.profile,\
									dest_account__account_type__gateway__name='MIPAY').\
									order_by('-date_created')[:1]

							if session_account_manager.exists():
								account_balance = session_account_manager[0].balance_bf
							else: continue
							if (account_balance is not None and account_balance>0) or variable_val=='Send': pass
							else: continue
						name = '%s' % (i.name)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, name, count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, name)
							if account_balance is not None and account_balance>0: 
								account_balance = '{0:,.2f}'.format(account_balance) 
								item = '%s(%s)' % (item,account_balance)

						item_list.append(name)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'all_installment_details':

					from secondary.finance.vbs.models import SavingsCreditManager

					params = payload

					savings_credit_manager = SavingsCreditManager.objects.filter(account_manager__id=payload['account_manager_id'], credit_paid=False).\
									order_by('-date_created')

					currency = savings_credit_manager[0].account_manager.dest_account.account_type.product_item.currency.code
					due_date = savings_credit_manager[0].due_date
					account_type = savings_credit_manager[0].account_manager.dest_account.account_type.name

					amount = Decimal(0)
					for i in savings_credit_manager:
						amount = amount + i.outstanding

					item = ''
					amount = '{0:,.2f}'.format(amount)
					item = '%s-%s %s %s' % (account_type, currency, amount,\
									due_date.strftime("%d/%b/%Y"))

					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'any_installment_details':

					from secondary.finance.vbs.models import SavingsCreditManager

					params = payload

					savings_credit_manager = SavingsCreditManager.objects.filter(account_manager__id=payload['account_manager_id'], credit_paid=False).\
									order_by('-date_created')[:1]

					account_type = savings_credit_manager[0].account_manager.dest_account.account_type.name
					amount = Decimal(payload['amount'])

					currency = savings_credit_manager[0].account_manager.dest_account.account_type.product_item.currency.code
					due_date = savings_credit_manager[0].due_date
					item = ''
					amount = '{0:,.2f}'.format(amount)
					item = '%s-%s %s %s' % (account_type, currency, amount,\
									due_date.strftime("%d/%b/%Y"))

					page_string = page_string.replace('['+v+']',item)



				elif variable_key == 'one_installment_details':

					from secondary.finance.vbs.models import SavingsCreditManager

					params = payload

					savings_credit_manager = SavingsCreditManager.objects.filter(account_manager__id=payload['account_manager_id'],credit_paid=False).\
									order_by('-date_created')[:1]

					account_type = savings_credit_manager[0].account_manager.dest_account.account_type.name
					amount = savings_credit_manager[0].outstanding

					currency = savings_credit_manager[0].account_manager.dest_account.account_type.product_item.currency.code
					due_date = savings_credit_manager[0].due_date
					item = ''
					amount = '{0:,.2f}'.format(amount)
					item = '%s-%s %s %s' % (account_type, currency, amount,\
									due_date.strftime("%d/%b/%Y"))

					page_string = page_string.replace('['+v+']',item)



				elif variable_key == 'loan_installment_amount':

					from secondary.finance.vbs.models import SavingsCreditManager

					params = payload

					savings_credit_manager = SavingsCreditManager.objects.filter(account_manager__id=payload['account_manager_id'],credit_paid=False).\
									order_by('-date_created')[:1]


					savings_credit_manager = savings_credit_manager[:10]
					item = ''
					item_list = []
					count = 1
					if savings_credit_manager.exists():
						for i in savings_credit_manager:
       		                                        amount = '{0:,.2f}'.format(i.outstanding)
               		                                name = 'Days:%s %s %s - %s' % (i.installment_time, i.account_manager.dest_account.account_type.product_item.currency.code, amount, i.due_date.strftime("%d/%b/%Y"))

							if navigator.session.channel.name == 'IVR':
								item = '%s\nFor %s, press %s.' % (item, name, count)
							elif navigator.session.channel.name == 'USSD':
								item = '%s\n%s:%s' % (item, count, name)

							item_list.append(str(i.outstanding))
							count+=1
						navigator.item_list = json.dumps(item_list)
						navigator.save()
					else:
						item = 'No Record Available'

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)



				elif variable_key == 'outstanding_loan':

					from secondary.finance.vbs.models import AccountManager, SavingsCreditManager

					params = payload

					account_manager = AccountManager.objects.filter(Q(credit=False),Q(credit_paid=False),\
									~Q(credit_due_date=None),~Q(credit_time=None),\
									Q(dest_account__profile=navigator.session.gateway_profile.user.profile),\
									Q(dest_account__account_type__gateway=code[0].gateway)).\
									order_by('-date_created')

					if 'institution_id' in params.keys():
						account_manager = account_manager.filter(Q(dest_account__account_type__institution__id=params['institution_id'])\
											|Q(dest_account__account_type__institution=None))
					else:
						account_manager = account_manager.filter(Q(dest_account__account_type__institution=code[0].institution)|Q(dest_account__account_type__institution=None))

					account_manager = account_manager[:10]
					item = ''
					item_list = []
					count = 1
					if account_manager.exists():
						for i in account_manager:
							savings_credit_manager = SavingsCreditManager.objects.filter(account_manager=i, credit_paid=False).order_by('-date_created')

							amount = Decimal(0)
							for a in savings_credit_manager:
								amount = amount + a.outstanding

       		                                        amount = '{0:,.2f}'.format(amount)
               		                                name = '%s %s %s - %s' % (i.dest_account.account_type.product_item.currency.code, i.dest_account.account_type.product_item.currency.code, amount, i.credit_due_date.strftime("%d/%b/%Y"))

							if navigator.session.channel.name == 'IVR':
								item = '%s\nFor %s, press %s.' % (item, name, count)
							elif navigator.session.channel.name == 'USSD':
								item = '%s\n%s:%s' % (item, count, name)

							item_list.append(i.id)
							count+=1
						navigator.item_list = json.dumps(item_list)
						navigator.save()
					else:
						item = 'No Record Available'

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'my_loan_request':

					from thirdparty.wahi.models import Loan

					params = payload

					loan = Loan.objects.filter(processed=False,\
									account__profile=navigator.session.gateway_profile.user.profile,\
									gateway_profile__user__profile=F('loan__account__profile'),\
									gateway=code[0].gateway).\
									order_by('-date_created')

					if 'institution_id' in params.keys():
						loan = loan.filter(Q(institution__id=params['institution_id'])\
											|Q(loan__institution=None))
					else:
						loan = loan.filter(Q(institution=code[0].institution)|Q(loan__institution=None))

					loan = loan[:10]
					item = ''
					item_list = []
					count = 1
					if loan.exists():
						for i in loan:
       		                                        amount = '{0:,.2f}'.format(i.amount)
               		                                name = '%s %s%s' % (i.currency.code, amount, i.date_created.strftime("%d/%b/%Y"))

							if navigator.session.channel.name == 'IVR':
								item = '%s\nFor %s, press %s.' % (item, name, count)
							elif navigator.session.channel.name == 'USSD':
								item = '%s\n%s:%s' % (item, count, name)

							item_list.append(i.id)
							count+=1
						navigator.item_list = json.dumps(item_list)
						navigator.save()
					else:
						item = 'No Record Available'

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'p2p_loan_details':
					from thirdparty.wahi.models import Loan

					params = payload

					loan = Loan.objects.get(id=params['loan_id'])

					amount = loan.amount


					given_amount = Decimal(0)
					approved_loan = Loan.objects.filter(follow_on_loan=loan,loan_status__name='APPROVED')
					for f in approved_loan:
						given_amount = given_amount + f.amount

					amount = amount - given_amount

					item = ''
					cost = '{0:,.2f}'.format(amount) if amount else ''
					item = '%s@(%s%%)-%s %s' % (loan.loan_type.name, loan.interest_rate,\
									loan.currency.code,\
									cost)

					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'p2p_loan_approval':

					from thirdparty.wahi.models import Loan

					params = payload

					loan = Loan.objects.filter(Q(loan_status__name='CREATED'),Q(processed=False),\
							Q(follow_on_loan__account__profile=navigator.session.gateway_profile.user.profile),\
							Q(gateway=code[0].gateway)).\
							order_by('-date_created')

					lgr.info('Loan: %s' % loan)

					if 'institution_id' in params.keys():
						loan = loan.filter(Q(institution__id=params['institution_id'])\
											|Q(loan__institution=None))
					elif code[0].institution:
						loan = loan.filter(Q(loan__institution=code[0].institution)|Q(loan__institution=None))
					else:
						lgr.info('None')
						loan = loan.filter(institution=None)

					lgr.info('Loan: %s' % loan)
					loan = loan[:10]
					item = ''
					item_list = []
					count = 1

					if loan.exists():
						for i in loan:
							amount = '{0:,.2f}'.format(i.amount)
							name = '%s %s%s %s' % (i.gateway_profile.user.last_name[:6], i.currency.code, amount, i.date_created.strftime("%d/%b/%Y"))

							if navigator.session.channel.name == 'IVR':
								item = '%s\nFor %s, press %s.' % (item, name, count)
							elif navigator.session.channel.name == 'USSD':
								item = '%s\n%s:%s' % (item, count, name)

							item_list.append(i.id)
							count+=1

						navigator.item_list = json.dumps(item_list)
						navigator.save()
					else:
						item = 'No Record Available'

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'p2p_loan_offer':

					from thirdparty.wahi.models import Loan

					params = payload

					loan = Loan.objects.filter(Q(status__name='CREATED'), Q(processed=False),\
										Q(loan_status__name='CREATED'),Q(follow_on_loan=None),\
										~Q(account__profile=navigator.session.gateway_profile.user.profile),\
										Q(gateway_profile__user__profile=F('account__profile')),\
										Q(gateway=code[0].gateway),\
										Q(credit=True)).\
										order_by('-date_created')

					if 'institution_id' in params.keys():
						loan = loan.filter(Q(institution__id=params['institution_id'])\
											|Q(institution=None))
					else:
						loan = loan.filter(Q(institution=code[0].institution)|Q(institution=None))

					loan = loan[:10]
					item = ''
					item_list = []
					count = 1

					for i in loan:
						amount = i.amount
						given_amount = Decimal(0)
						approved_loan = Loan.objects.filter(follow_on_loan=i,loan_status__name='APPROVED')
						for f in approved_loan:
							given_amount = given_amount + f.amount

						amount = amount - given_amount
						if amount > Decimal(0):
							amount = '{0:,.2f}'.format(amount)
							name = '%s %s%s@%s%% %s' % (i.gateway_profile.user.last_name[:6], i.currency.code, amount, i.interest_rate, i.date_created.strftime("%d/%b/%Y"))

							if navigator.session.channel.name == 'IVR':
								item = '%s\nFor %s, press %s.' % (item, name, count)
							elif navigator.session.channel.name == 'USSD':
								item = '%s\n%s:%s' % (item, count, name)

							item_list.append(i.id)
							count+=1

					navigator.item_list = json.dumps(item_list)
					navigator.save()
					if len(item_list)==0:
						item = 'No Record Available'

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'p2p_loan_request':

					from thirdparty.wahi.models import Loan

					params = payload

					loan = Loan.objects.filter(Q(status__name='CREATED'), Q(processed=False),\
										Q(loan_status__name='CREATED'),Q(follow_on_loan=None),\
										~Q(account__profile=navigator.session.gateway_profile.user.profile),\
										Q(gateway_profile__user__profile=F('account__profile')),\
										Q(gateway=code[0].gateway),\
										Q(credit=False)).\
										order_by('-date_created')

					if 'institution_id' in params.keys():
						loan = loan.filter(Q(institution__id=params['institution_id'])\
											|Q(institution=None))
					else:
						loan = loan.filter(Q(institution=code[0].institution)|Q(institution=None))

					loan = loan[:10]
					item = ''
					item_list = []
					count = 1

					for i in loan:
						amount = i.amount
						given_amount = Decimal(0)
						approved_loan = Loan.objects.filter(follow_on_loan=i,loan_status__name='APPROVED')
						for f in approved_loan:
							given_amount = given_amount + f.amount

						amount = amount - given_amount
						if amount > Decimal(0):
							amount = '{0:,.2f}'.format(amount)
							#name = '%s %s%s %s' % (i.gateway_profile.user.last_name[:6], i.currency.code, amount, i.date_created.strftime("%d/%b/%Y"))
							name = '%s %s%s@%s%% %s' % (i.gateway_profile.user.last_name[:6], i.currency.code, amount, i.interest_rate, i.date_created.strftime("%d/%b/%Y"))

							if navigator.session.channel.name == 'IVR':
								item = '%s\nFor %s, press %s.' % (item, name, count)
							elif navigator.session.channel.name == 'USSD':
								item = '%s\n%s:%s' % (item, count, name)

							item_list.append(i.id)
							count+=1

					navigator.item_list = json.dumps(item_list)
					navigator.save()
					if len(item_list)==0:
						item = 'No Record Available'

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'default_payment_method':

					from primary.core.bridge.models import PaymentMethod

					payment_method = PaymentMethod.objects.filter(Q(channel__id=payload['chid'])|Q(channel=None))

					if variable_val == 'Send':
						payment_method = payment_method.filter(send=True)
					elif variable_val == 'Receive':
						payment_method = payment_method.filter(receive=True)


					item = ''
					item_list = []
					count = 1
					for i in payment_method:
						account_balance = None
						if i.name == 'MIPAY' and variable_val <> 'Send' and mipay_gateway_profile.exists():
							session_account_manager = AccountManager.objects.filter(dest_account__account_status__name='ACTIVE',\
									dest_account__profile=mipay_gateway_profile[0].user.profile,\
									dest_account__account_type__gateway__name='MIPAY').\
									order_by('-date_created')[:1]

							if session_account_manager.exists():
								account_balance = session_account_manager[0].balance_bf
							else: continue
							if (account_balance is not None and account_balance>0) or variable_val=='Send': pass
							else: continue
						name = '%s' % (i.name)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, name, count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, name)
							if account_balance is not None and account_balance>0: 
								account_balance = '{0:,.2f}'.format(account_balance) 
								item = '%s(%s)' % (item,account_balance)

						item_list.append(name)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'account_payment_method':

					from secondary.finance.vbs.models import AccountType,AccountManager

					params = payload

					mipay_gateway_profile = GatewayProfile.objects.filter(msisdn__phone_number=payload['msisdn'],gateway__name='MIPAY')

					account_type = AccountType.objects.get(id=params['account_type_id'])
					payment_method = account_type.product_item.product_type.payment_method.filter(Q(channel__id=payload['chid'])|Q(channel=None))

					if variable_val == 'Send':
						payment_method = payment_method.filter(send=True)
					elif variable_val == 'Receive':
						payment_method = payment_method.filter(receive=True)


					item = ''
					item_list = []
					count = 1
					for i in payment_method:
						account_balance = None
						if i.name == 'MIPAY' and variable_val <> 'Send' and mipay_gateway_profile.exists():
							session_account_manager = AccountManager.objects.filter(dest_account__account_status__name='ACTIVE',\
									dest_account__profile=mipay_gateway_profile[0].user.profile,\
									dest_account__account_type__gateway__name='MIPAY').\
									order_by('-date_created')[:1]

							if session_account_manager.exists():
								account_balance = session_account_manager[0].balance_bf
							else: continue
							if (account_balance is not None and account_balance>0) or variable_val=='Send': pass
							else: continue
						name = '%s' % (i.name)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, name, count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, name)
							if account_balance is not None and account_balance>0: 
								account_balance = '{0:,.2f}'.format(account_balance) 
								item = '%s(%s)' % (item,account_balance)

						item_list.append(name)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'order_payment_method':

					from secondary.finance.vbs.models import AccountManager
					from secondary.erp.pos.models import BillManager

					params = payload

					mipay_gateway_profile = GatewayProfile.objects.filter(msisdn__phone_number=payload['msisdn'],gateway__name='MIPAY')

					bill_manager_list = BillManager.objects.filter(order__gateway_profile__msisdn__phone_number=payload['msisdn'],\
									order__reference=params['reference'],order__status__name='UNPAID').order_by("-date_created")
					if 'institution_id' in params.keys():
						bill_manager_list = bill_manager_list.filter(order__cart_item__product_item__institution__id=params['institution_id'])
					else:
						bill_manager_list = bill_manager_list.filter(order__cart_item__product_item__institution__id=code[0].institution.id)

					item = ''
					item_list = []
					count = 1
					if bill_manager_list.exists():
						payment_method = []
						cart_item_list = bill_manager_list[0].order.cart_item.all()

						#cart_item_list = bill_manager_list[0].order.cart_item.filter(Q(product_item__product_type__payment_method__channel__id=payload['chid'])|Q(product_item__product_type__payment_method__channel=None))
						cart_item_payment_method = cart_item_list.filter(Q(product_item__product_type__payment_method__channel__id=payload['chid'])|Q(product_item__product_type__payment_method__channel=None)).\
										values('product_item__product_type__payment_method__name','product_item__currency__code').\
										annotate(num_payments=Count('product_item__product_type__payment_method__name'))
						#cart_item_payment_method = cart_item_list.values('product_item__product_type__payment_method__name').\
						#			annotate(num_payments=Count('product_item__product_type__payment_method__name'))
						max_payment_method = cart_item_payment_method.aggregate(Max('num_payments'))

						lgr.info('\n\n\n\tCart Item Payment Method: %s|Max(%s)\n\n\n' % (cart_item_payment_method, max_payment_method))

						for i in cart_item_payment_method:
							if max_payment_method['num_payments__max']==i['num_payments']:
								account_balance = None
								if i['product_item__product_type__payment_method__name'] == 'MIPAY' and mipay_gateway_profile.exists():
									session_account_manager = AccountManager.objects.filter(dest_account__account_status__name='ACTIVE',\
											dest_account__profile=mipay_gateway_profile[0].user.profile,\
											dest_account__account_type__gateway__name='MIPAY',\
											dest_account__account_type__product_item__currency__code=i['product_item__currency__code']).\
											order_by('-date_created')[:1]
									if session_account_manager.exists():
										account_balance = session_account_manager[0].balance_bf
									else: continue
									if account_balance is not None and account_balance>0: pass
									else: continue
								name = '%s' % (i['product_item__product_type__payment_method__name'])
								if navigator.session.channel.name == 'IVR':
									item = '%s\nFor %s, press %s.' % (item, name, count)
								elif navigator.session.channel.name == 'USSD':
									item = '%s\n%s:%s' % (item, count, name)
									if account_balance is not None and account_balance>0: 
										account_balance = '{0:,.2f}'.format(account_balance) 
										item = '%s(%s)' % (item,account_balance)

								item_list.append(name)
								count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'music_payment_method':

					from secondary.finance.vbs.models import AccountManager
					from products.muziqbit.models import Music

					mipay_gateway_profile = GatewayProfile.objects.filter(msisdn__phone_number=payload['msisdn'],gateway__name='MIPAY')

					params = payload
					song = params['SONG']
					#get artiste name
					artiste_list = re.findall("\((.*?)\)", song)
					artiste = ''
					if len(artiste_list)>0:
						artiste = artiste_list[len(artiste_list)-1]
						song = song.replace('('+artiste+')','')

					music = Music.objects.filter(product_item__name=song,artiste=artiste,product_item__institution__id=code[0].institution.id,\
						product_item__status__name='ACTIVE').order_by('-release_date')


					item = ''
					item_list = []
					count = 1
					if len(music)>0:
						payment_method = music[0].product_item.product_type.payment_method.filter(Q(channel__id=payload['chid'])|Q(channel=None))
						for i in payment_method:
							account_balance = None
							if i.name == 'MIPAY' and mipay_gateway_profile.exists():
								session_account_manager = AccountManager.objects.filter(dest_account__account_status__name='ACTIVE',\
										dest_account__profile=mipay_gateway_profile[0].user.profile,\
										dest_account__account_type__gateway__name='MIPAY',\
										dest_account__account_type__product_item__currency=music[0].product_item.currency).\
										order_by('-date_created')[:1]

								if session_account_manager.exists():
									account_balance = session_account_manager[0].balance_bf
								else: continue
								if account_balance is not None and account_balance>0: pass
								else: continue
							name = '%s' % (i.name)
							if navigator.session.channel.name == 'IVR':
								item = '%s\nFor %s, press %s.' % (item, name, count)
							elif navigator.session.channel.name == 'USSD':
								item = '%s\n%s:%s' % (item, count, name)
								if account_balance is not None and account_balance>0: 
									account_balance = '{0:,.2f}'.format(account_balance) 
									item = '%s(%s)' % (item,account_balance)

							item_list.append(name)
							count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'loan_time':

					loan_time_list = variable_val.split("|") if variable_val not in ['',None] else []
					item = ''
					item_list = []
					count = 1
					if len(loan_time_list)>0:
						query = []
						for t in loan_time_list:
							name, time = t.split("-")
							if navigator.session.channel.name == 'IVR':
								item = '%s\nFor %s, press %s.' % (item, name, count)
							elif navigator.session.channel.name == 'USSD':
								item = '%s\n%s:%s' % (item, count, name)

							item_list.append(int(time))
							count+=1
						navigator.item_list = json.dumps(item_list)
						navigator.save()
					else:
						item = 'No Time RecordAvailable'

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)



				elif variable_key == 'account_type_id':
					from secondary.finance.vbs.models import Account

					params = payload

					session_gateway_profile = GatewayProfile.objects.filter(gateway=code[0].gateway, msisdn__phone_number=payload['msisdn'])

					if session_gateway_profile.exists():
						account_list = Account.objects.filter(profile=session_gateway_profile[0].user.profile, account_status__name='ACTIVE',\
									account_type__gateway =code[0].gateway).order_by('account_type__name')
					else:
						account_list = Account.objects.none()

					if variable_val not in ['',None]:
						account_list = account_list.filter(account_type__product_item__product_type__name=variable_val)

					item = ''
					item_list = []
					count = 1
					if account_list.exists():
						for a in account_list:
							i = a.account_type
							preview_name = '%s(%s)' % (i.name,i.product_item.currency.code)

							if navigator.session.channel.name == 'IVR':
								item = '%s\nFor %s, press %s.' % (item, preview_name, count)
							elif navigator.session.channel.name == 'USSD':
								item = '%s\n%s:%s' % (item, count, preview_name)

							item_list.append(i.id)
							count+=1
						navigator.item_list = json.dumps(item_list)
						navigator.save()
					else:
						item = 'No Record Available'

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'payment_method':
					from secondary.erp.crm.models import ProductItem
					from secondary.finance.vbs.models import AccountManager

					mipay_gateway_profile = GatewayProfile.objects.filter(msisdn__phone_number=payload['msisdn'],gateway__name='MIPAY')


					product_item = ProductItem.objects.filter(Q(institution=code[0].institution)|Q(institution__gateway=code[0].gateway),Q(status__name='ACTIVE'))

					if 'product_item_id' in payload.keys():
						product_item = product_item.filter(id=payload['product_item_id'])
					elif 'item' in payload.keys():
						product_item = product_item.filter(name=payload['item']).order_by('id')[:10]
					else:
						product_item = product_item.none()

					if variable_val not in ['',None]:
						product_item = product_item.filter(Q(product_type__name=variable_val)|Q(product_type__product_category__name=variable_val))


					item = ''
					item_list = []
					count = 1
					if product_item.exists():
						payment_method = product_item[0].product_type.payment_method.filter(Q(channel__id=payload['chid'])|Q(channel=None))
						for i in payment_method:
							account_balance = None
							if i.name == 'MIPAY' and mipay_gateway_profile.exists():
								session_account_manager = AccountManager.objects.filter(dest_account__account_status__name='ACTIVE',\
										dest_account__profile=mipay_gateway_profile[0].user.profile,\
										dest_account__account_type__gateway__name='MIPAY',\
										dest_account__account_type__product_item__currency=product_item[0].currency).\
										order_by('-date_created')[:1]

								if session_account_manager.exists():
									account_balance = session_account_manager[0].balance_bf
								else: continue
								if account_balance is not None and account_balance>0: pass
								else: continue
							name = '%s' % (i.name)
							if navigator.session.channel.name == 'IVR':
								item = '%s\nFor %s, press %s.' % (item, name, count)
							elif navigator.session.channel.name == 'USSD':
								item = '%s\n%s:%s' % (item, count, name)
								if account_balance is not None and account_balance>0: 
									account_balance = '{0:,.2f}'.format(account_balance) 
									item = '%s(%s)' % (item,account_balance)

							item_list.append(name)
							count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'account_balance':
					from secondary.finance.vbs.models import AccountManager
					params = payload


					session_gateway_profile = GatewayProfile.objects.filter(gateway=code[0].gateway, msisdn__phone_number=payload['msisdn'])

					session_account_manager = AccountManager.objects.filter(dest_account__account_status__name='ACTIVE',\
											dest_account__profile=session_gateway_profile[0].user.profile,\
											dest_account__account_type__id=params['account_type_id']).\
											order_by('-date_created')[:1]
					account_balance = Decimal(0)
					currency = 'KES'
					if session_account_manager.exists():
						account_balance = session_account_manager[0].balance_bf
						currency = session_account_manager[0].dest_account.account_type.product_item.currency.code

					item = ''
					item_list = []
					count = 1

					amount = '{0:,.2f}'.format(account_balance)
					item = '%s %s\n' % (currency,amount)

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'account_credit_limit':
					from secondary.finance.vbs.models import Account
					params = payload

					session_gateway_profile = GatewayProfile.objects.filter(gateway=code[0].gateway, msisdn__phone_number=payload['msisdn'])

					if session_gateway_profile.exists():
						account_list = Account.objects.filter(profile=session_gateway_profile[0].user.profile,account_status__name='ACTIVE',\
									account_type__id=params['account_type_id'],account_type__gateway =code[0].gateway).order_by('account_type__name')
					else:
						account_list = Account.objects.none()

					if variable_val not in ['',None]:
						account_list = account_list.filter(account_type__product_item__product_type__name=variable_val)

					item = ''
					item_list = []
					count = 1

					if account_list.exists():
		                                amount = '{0:,.2f}'.format(account_list[0].credit_limit) if account_list[0].credit_limit else 0
						currency = account_list[0].account_type.product_item.currency.code
						item = '%s %s\n' % (currency,amount)

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'product_amount_limit':
					from secondary.erp.crm.models import ProductItem


					params = payload

					if 'product_item_id' in params.keys():
						product_item = ProductItem.objects.filter(id=params['product_item_id'])
					elif 'item' in params.keys() and code[0].institution:
						product_item = ProductItem.objects.filter(name=params['item'],institution__id=code[0].institution.id, status__name='ACTIVE').order_by('id')[:10]
					else:
						product_item = ProductItem.objects.none()


					if variable_val not in ['',None]:
						product_item = product_item.filter(Q(product_type__name=variable_val)|Q(product_type__product_category__name=variable_val))

					item = ''

					if product_item.exists():
						max_amount = product_item[0].unit_limit_max
						max_amount = max_amount if max_amount > 0 else Decimal(0)
	        	                        max_amount = '{0:,.2f}'.format(max_amount) 

						min_amount = product_item[0].unit_limit_min
						min_amount = min_amount if min_amount > 0 else Decimal(0)
	                                	min_amount = '{0:,.2f}'.format(min_amount) 
						currency = product_item[0].currency.code
						item = '\nMin:%s %s\nMax:%s %s\n' % (currency,min_amount,currency,max_amount)

					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'account_manager_amount_limit':
					from secondary.finance.vbs.models import AccountManager, AccountCharge
					params = payload

					account_type = AccountManager.objects.get(id=params['account_manager_id']).dest_account.account_type

					max_amount = account_type.product_item.unit_limit_max
					max_amount = max_amount if max_amount > 0 else Decimal(0)
	                                max_amount = '{0:,.2f}'.format(max_amount) 

					min_amount = account_type.product_item.unit_limit_min
					min_amount = min_amount if min_amount > 0 else Decimal(0)
	                                min_amount = '{0:,.2f}'.format(min_amount) 
					currency = account_type.product_item.currency.code
					item = '\nMin:%s %s\nMax:%s %s\n' % (currency,min_amount,currency,max_amount)

					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'account_amount_limit':
					from secondary.finance.vbs.models import AccountType, AccountCharge
					params = payload

					account_type = AccountType.objects.get(id=params['account_type_id'])

					max_amount = account_type.product_item.unit_limit_max
					max_amount = max_amount if max_amount > 0 else Decimal(0)
	                                max_amount = '{0:,.2f}'.format(max_amount) 

					min_amount = account_type.product_item.unit_limit_min
					min_amount = min_amount if min_amount > 0 else Decimal(0)
	                                min_amount = '{0:,.2f}'.format(min_amount) 
					currency = account_type.product_item.currency.code
					item = '\nMin:%s %s\nMax:%s %s\n' % (currency,min_amount,currency,max_amount)

					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'account_type_details':
					from secondary.finance.vbs.models import AccountType, AccountCharge, SavingsCreditType
					params = payload

					account_type = AccountType.objects.get(id=params['account_type_id'])
					unit_cost = account_type.product_item.unit_cost

					item = ''
					if  account_type.product_item.variable_unit and 'quantity' in params.keys():
						unit_cost = unit_cost*Decimal(params['quantity'])	
					elif account_type.product_item.variable_unit and 'amount' in params.keys():
						unit_cost = Decimal(params['amount'])	



	                                cost = '{0:,.2f}'.format(unit_cost) if unit_cost > 0 else None
					item = '%s@%s %s' % (account_type.name,account_type.product_item.currency.code,\
								cost )

					charge = Decimal(0)
					charge_list = AccountCharge.objects.filter(account_type__id=params['account_type_id'],min_amount__lte=unit_cost,\
							max_amount__gte=unit_cost,service=navigator.menu.service)
					lgr.info('Charge List: %s' % charge_list)
					lgr.info('Charge List: %s|%s' % (charge_list, params))

					if 'payment_method' in params.keys():
						lgr.info('Charge List: %s|%s' % (charge_list, params))
						charge_list = charge_list.filter(Q(payment_method__name=str(params['payment_method']))|Q(payment_method=None))
						lgr.info('Charge List: %s|%s' % (charge_list, params))

					if variable_val == 'Credit':
						charge_list = charge_list.filter(credit=True)
					else:
						charge_list = charge_list.filter(credit=False)
					lgr.info('Charge List: %s' % charge_list)


					for c in charge_list:
						if c.is_percentage:
							charge = charge + ((c.charge_value/100)*Decimal(unit_cost))
						else:
							charge = charge+c.charge_value		

					lgr.info('Charge: %s' % charge)

					if charge>Decimal(0):
						item = '%s\nCharges@%s %s' % (item,account_type.product_item.currency.code,'{0:,.2f}'.format(charge))

					loan_amount = unit_cost
					if 'loan_time' in payload.keys():
						credit_type = SavingsCreditType.objects.filter(account_type=account_type,\
									 min_time__lte=int(payload['loan_time']), max_time__gte=int(payload['loan_time']))

						for c in credit_type:
							loan_amount = loan_amount + ((c.interest_rate/100)*(int(payload['loan_time'])/c.interest_time)*unit_cost)

	                                loan_cost = '{0:,.2f}'.format(loan_amount) if loan_amount > 0 else None
					item = '%s\nLoan Amount@%s %s' % (item,account_type.product_item.currency.code,loan_cost)

					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'user.email':

					item = ''

					if navigator.session.gateway_profile:
						item = navigator.session.gateway_profile.user.email

					page_string = page_string.replace('['+v+']',item)



				elif variable_key == 'email':

					item = ''

					if navigator.session.gateway_profile:
						item = navigator.session.gateway_profile.user.email

					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'postal_code':

					item = ''

					if navigator.session.gateway_profile and navigator.session.gateway_profile.user.profile.postal_code:
						item = navigator.session.gateway_profile.user.profile.postal_code

					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'postal_address':

					item = ''

					if navigator.session.gateway_profile and navigator.session.gateway_profile.user.profile.postal_address:
						item = navigator.session.gateway_profile.user.profile.postal_address

					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'document_number':

					item = ''

					if navigator.session.gateway_profile and navigator.session.gateway_profile.user.profile.national_id:
						item = navigator.session.gateway_profile.user.profile.national_id
					elif navigator.session.gateway_profile and navigator.session.gateway_profile.user.profile.passport_number:
						item = navigator.session.gateway_profile.user.profile.passport_number

					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'order_item_details':
					from secondary.erp.pos.models import BillManager

					params = payload

					bill_manager_list = BillManager.objects.filter(order__gateway_profile__msisdn__phone_number=payload['msisdn'],\
									order__reference=params['reference'],order__status__name='UNPAID').order_by("-date_created")
					if 'institution_id' in params.keys():
						bill_manager_list = bill_manager_list.filter(order__cart_item__product_item__institution__id=params['institution_id'])
					else:
						bill_manager_list = bill_manager_list.filter(order__cart_item__product_item__institution__id=code[0].institution.id)

					item = ''
					if bill_manager_list.exists():
		                                cost = '{0:,.2f}'.format(bill_manager_list[0].balance_bf) if bill_manager_list[0].balance_bf > 0 else bill_manager_list[0].order.amount
						item = '%s(%s)@%s %s' % (bill_manager_list[0].order.reference, bill_manager_list[0].order.cart_item_list()[:10],\
									bill_manager_list[0].order.currency.code,\
									cost )
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'music_item_details':
					from products.muziqbit.models import Music


					params = payload
					song = params['SONG']
					#get artiste name
					artiste_list = re.findall("\((.*?)\)", song)
					artiste = ''
					if len(artiste_list)>0:
						artiste = artiste_list[len(artiste_list)-1]
						song = song.replace('('+artiste+')','')

					music = Music.objects.filter(product_item__name=song,artiste=artiste,product_item__institution__id=code[0].institution.id,\
							product_item__status__name='ACTIVE').order_by('-release_date')

					item = ''
					if len(music)>0:
		                                cost = '{0:,.2f}'.format(music[0].product_item.unit_cost) if music[0].product_item.unit_cost > 0 else None
						item = '%s(%s)@%s %s' % (music[0].product_item.name,music[0].artiste,\
									music[0].product_item.currency.code,\
									cost )
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'product_item_details':
					from secondary.erp.crm.models import ProductItem

					product_item = ProductItem.objects.filter(Q(institution=code[0].institution)|Q(institution__gateway=code[0].gateway),Q(status__name='ACTIVE'))

					if 'product_item_id' in payload.keys():
						product_item = product_item.filter(id=payload['product_item_id'])
					elif 'item' in payload.keys():
						product_item = product_item.filter(name=payload['item']).order_by('id')[:10]
					else:
						product_item = product_item.none()

					if variable_val not in ['',None]:
						product_item = product_item.filter(Q(product_type__name=variable_val)|Q(product_type__product_category__name=variable_val))

					item = ''
					if product_item.exists():
						unit_cost = product_item[0].unit_cost
						if  product_item[0].variable_unit and 'quantity' in payload.keys():
							unit_cost = unit_cost*Decimal(payload['quantity'])
						elif product_item[0].variable_unit and 'amount' in payload.keys():
							unit_cost = Decimal(payload['amount'])	

						unit_cost = self.sale_charge_bill(unit_cost, product_item[0], code[0].gateway)
		                                cost = '{0:,.2f}'.format(unit_cost) if unit_cost > 0 else None
						item = '%s@%s %s' % (product_item[0].name,\
									product_item[0].currency.code,\
									cost )
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'purchase_order_institution_id':
					from secondary.erp.pos.models import PurchaseOrder

					purchase_order = PurchaseOrder.objects.filter(status__name='UNPAID',gateway_profile__msisdn__phone_number=payload['msisdn'],\
								cart_item__product_item__institution__gateway=code[0].gateway).\
								values('cart_item__product_item__institution__id','cart_item__product_item__institution__name').distinct('cart_item__product_item__institution__id','cart_item__product_item__institution__name')
					purchase_order = purchase_order[:10]
					item = ''
					item_list = []
					count = 1
					if purchase_order.exists():
						for i in purchase_order:
        	                                        #cost = '{0:,.2f}'.format(i.unit_cost) if i.unit_cost > 0 else None
	                                                name_id = i['cart_item__product_item__institution__id']
							name = i['cart_item__product_item__institution__name']
							if navigator.session.channel.name == 'IVR':
								item = '%s\nFor %s, press %s.' % (item, name, count)
							elif navigator.session.channel.name == 'USSD':
								item = '%s\n%s:%s' % (item, count, name)
							item_list.append(name_id)
							count+=1
						navigator.item_list = json.dumps(item_list)
						navigator.save()
					else:
						item = 'No Record Available'

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'purchase_order':
					from secondary.erp.pos.models import BillManager
					params = payload

					bill = BillManager.objects.filter(order__status__name='UNPAID',order__gateway_profile__msisdn__phone_number=payload['msisdn'],\
							order__cart_item__product_item__institution__gateway=code[0].gateway).\
							distinct('order__id','order__date_created').order_by('-order__date_created')
					if 'institution_id' in params.keys():
						bill = bill.filter(order__cart_item__product_item__institution__id=params['institution_id'])
					elif code[0].institution:
						bill = bill.filter(order__cart_item__product_item__institution=code[0].institution)

					if variable_val not in ['',None]:
						bill = bill.filter(order__cart_item__product_item__product_type__name=variable_val)


					bill = bill[:10]
					item = ''
					item_list = []
					count = 1
					if bill.exists():
						for i in bill:
							lgr.info('Bill Items: %s' % i)
        	                                        cost = '{0:,.2f}'.format(i.balance_bf)
                	                                name = '%s %s-%s-%s' % (i.order.currency.code, cost, i.order.date_created.strftime("%d/%b/%Y"),i.order.reference)
							if navigator.session.channel.name == 'IVR':
								item = '%s\nFor %s, press %s.' % (item, name[:40], count)
							elif navigator.session.channel.name == 'USSD':
								item = '%s\n%s:%s' % (item, count, name[:40])
							item_list.append(i.order.reference)
							count+=1
						navigator.item_list = json.dumps(item_list)
						navigator.save()
					else:
						item = 'No Record Available'

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'product_type':
					from secondary.erp.crm.models import ProductItem

					product_type_item= ProductItem.objects.filter(institution__id=code[0].institution.id, status__name='ACTIVE').\
								distinct('product_type__name','product_type__date_modified').\
								order_by('product_type__date_modified')
					if variable_val not in ['',None]:
						product_type_item = product_type_item.filter(product_type__product_category__name=variable_val)

					product_type_item = product_type_item[:10]
					item = ''
					item_list = []
					count = 1
					for i in product_type_item:
                                                #cost = '{0:,.2f}'.format(i.unit_cost) if i.unit_cost > 0 else None
                                                name = '%s' % (i.product_type.name)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, name, count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, name)
						item_list.append(name)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'amka_investment_product_item':
					from thirdparty.amkagroup_co_ke.models import Investment, InvestmentType

					investment = Investment.objects.filter(account__profile=navigator.session.gateway_profile.user.profile)[:1]

					item = ''
					item_list = []
					count = 1
					if investment.exists():
						investment_type = InvestmentType.objects.filter(~Q(name='M-Chaama Enrollment')) #Enrollment investment not needed if investment exists
						for i in investment_type:
							name = '%s' % (i.product_item.name)
							if navigator.session.channel.name == 'IVR':
								item = '%s\nFor %s, press %s.' % (item, name, count)
							elif navigator.session.channel.name == 'USSD':
								item = '%s\n%s:%s' % (item, count, name)
							item_list.append(name)
							count+=1
					else:
						investment_type = InvestmentType.objects.get(name='M-Chaama Enrollment') #Enrollment only needed if no investment
						name = '%s' % (investment_type.product_item.name)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, name, count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, name)
						item_list.append(name)
					
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'gateway_product_item' or variable_key == 'gateway_product_item_cost':
					from secondary.erp.crm.models import ProductItem

					params = payload

					product_item = ProductItem.objects.filter(institution__gateway=code[0].gateway, status__name='ACTIVE').order_by('id')

					if variable_val not in ['',None]:
						product_item = product_item.filter(product_type__name=variable_val)
					if 'product_type' in params.keys():
						product_item = product_item.filter(product_type__name=params['product_type'])


					product_item = product_item[:20]
					item = ''
					item_list = []
					count = 1
					for i in product_item:
                                                cost = '{0:,.2f}'.format(i.unit_cost) if i.unit_cost > 0 else None
                                                name = '%s' % (i.name)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, name, count)
						elif navigator.session.channel.name == 'USSD':
							if variable_key == 'gateway_product_item_cost':
								item = '%s\n%s:%s@%s%s' % (item, count, name,i.currency.code,cost)
							else:
								item = '%s\n%s:%s' % (item, count, name)

						item_list.append(name)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'investment_product_item_id' or variable_key == 'investment_product_item_id_cost':
					from secondary.erp.crm.models import Enrollment, ProductItem

					params = payload

					enrollment_list = Enrollment.objects.filter(profile=navigator.session.gateway_profile.user.profile)

					if variable_val not in ['',None]:
						enrollment_list = enrollment_list.filter(Q(enrollment_type__product_item__product_type__name=variable_val)|Q(enrollment_type__product_item__product_type__name='Membership Plan'))
					elif 'product_type' in params.keys():
						enrollment_list = enrollment_list.filter(enrollment_type__product_item__product_type__name=params['product_type'])
					else:
						enrollment_list = enrollment_list.filter(enrollment_type__product_item__product_type__name='Membership Plan')

					if code[0].institution:
						product_item = ProductItem.objects.filter(institution__id=code[0].institution.id, status__name='ACTIVE').order_by('id')
					else:
						product_item = ProductItem.objects.filter(institution__gateway=code[0].gateway, institution__in=[e.enrollment_type.product_item.institution for e in enrollment_list], status__name='ACTIVE').order_by('id')


					if variable_val not in ['',None]:
						product_item = product_item.filter(product_type__name=variable_val)
					elif 'product_type' in params.keys():
						product_item = product_item.filter(product_type__name=params['product_type'])


					product_item = product_item[:20]
					item = ''
					item_list = []
					count = 1
					for i in product_item:
                                                cost = '{0:,.2f}'.format(i.unit_cost) if i.unit_cost > 0 else None
                                                name = '%s' % (i.name)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, name, count)
						elif navigator.session.channel.name == 'USSD':
							if variable_key == 'product_item_id_cost':
								item = '%s\n%s:%s@%s%s' % (item, count, name,i.currency.code,cost)
							else:
								item = '%s\n%s:%s' % (item, count, name)

						item_list.append(i.id)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)



				elif variable_key == 'product_item_id' or variable_key == 'product_item_id_cost':
					from secondary.erp.crm.models import ProductItem

					params = payload
					if code[0].institution:
						product_item = ProductItem.objects.filter(institution__id=code[0].institution.id, status__name='ACTIVE').order_by('id')
					else:
						product_item = ProductItem.objects.filter(institution__gateway=code[0].gateway, status__name='ACTIVE').order_by('id')

					if variable_val not in ['',None]:
						product_item = product_item.filter(product_type__name=variable_val)
					elif 'product_type' in params.keys():
						product_item = product_item.filter(product_type__name=params['product_type'])


					product_item = product_item[:20]
					item = ''
					item_list = []
					count = 1
					for i in product_item:
                                                cost = '{0:,.2f}'.format(i.unit_cost) if i.unit_cost > 0 else None
                                                name = '%s' % (i.name)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, name, count)
						elif navigator.session.channel.name == 'USSD':
							if variable_key == 'product_item_id_cost':
								item = '%s\n%s:%s@%s%s' % (item, count, name,i.currency.code,cost)
							else:
								item = '%s\n%s:%s' % (item, count, name)

						item_list.append(i.id)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)



				elif variable_key == 'product_item' or variable_key == 'product_item_cost':
					from secondary.erp.crm.models import ProductItem

					params = payload

					if code[0].institution:
						product_item = ProductItem.objects.filter(institution__id=code[0].institution.id, status__name='ACTIVE').order_by('id')
					else:
						product_item = ProductItem.objects.filter(institution__gateway=code[0].gateway, status__name='ACTIVE').order_by('id')

					if variable_val not in ['',None]:
						product_item = product_item.filter(product_type__name=variable_val)
					if 'product_type' in params.keys():
						product_item = product_item.filter(product_type__name=params['product_type'])


					product_item = product_item[:20]
					item = ''
					item_list = []
					count = 1
					for i in product_item:
                                                cost = '{0:,.2f}'.format(i.unit_cost) if i.unit_cost > 0 else None
                                                name = '%s' % (i.name)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, name, count)
						elif navigator.session.channel.name == 'USSD':
							if variable_key == 'product_item_cost':
								item = '%s\n%s:%s@%s%s' % (item, count, name,i.currency.code,cost)
							else:
								item = '%s\n%s:%s' % (item, count, name)

						item_list.append(name)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'survey_product_item':
					from secondary.erp.survey.models import Survey

					survey = Survey.objects.filter(Q(institution__id=code[0].institution.id), Q(status__name='ACTIVE')).order_by('id')

					if variable_val not in ['',None]:
						survey = survey.filter(Q(group__data_name=variable_val)|Q(product_item__product_type__name=variable_val)|Q(product_type__name=variable_val))

					params = payload
					if 'group' in params.keys():
						survey = survey.filter(Q(group__data_name=params['group'])|Q(product_item__product_type__name=params['group'])|Q(product_type__name=params['group'])|Q(group__name=params['group']))
					survey = survey[:20]
					item = ''
					item_list = []
					count = 1
					for i in survey:
						name = '%s' % (i.product_item.name)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, name, count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, name)
						item_list.append(name)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'survey':
					from secondary.erp.survey.models import Survey

					survey = Survey.objects.filter(Q(institution__id=code[0].institution.id), Q(status__name='ACTIVE')).order_by('id')

					if variable_val not in ['',None]:
						survey = survey.filter(Q(group__data_name=variable_val)|Q(product_item__product_type__name=variable_val)|Q(product_type__name=variable_val))

					params = payload
					if 'group' in params.keys():
						survey = survey.filter(Q(group__data_name=params['group'])|Q(product_item__product_type__name=params['group'])|Q(product_type__name=params['group'])|Q(group__name=params['group']))
					survey = survey[:20]
					item = ''
					item_list = []
					count = 1
					for i in survey:
						name = '%s' % (i.name)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, name, count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, name)
						item_list.append(name)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'survey_group':
					from secondary.erp.survey.models import Survey

					survey = Survey.objects.filter(Q(institution__id=code[0].institution.id), Q(status__name='ACTIVE')).distinct('group__name','group__date_modified').order_by('group__date_modified')
					survey = survey[:20]
					item = ''
					item_list = []
					count = 1
					for i in survey:
						name = '%s' % (i.group.name)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, name, count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, name)
						item_list.append(name)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'survey_details':
					from secondary.erp.crm.models import ProductItem

					params = payload

					survey = Survey.objects.filter(group__data_name=params['group'],name=params['item'],\
							institution__id=code[0].institution.id, status__name='ACTIVE').\
							order_by('id')[:10]
					item = ''
					if len(survey)>0:
						item = '%s(%s)' % (survey[0].group,survey[0].name)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'road_street':
					from thirdparty.roadroute.models import RoadStreet

					params = payload

					road_street = RoadStreet.objects.all()
					if variable_val not in ['',None]:
						road_street = road_street.filter(town_city__name=variable_val)

					if 'Search' in params.keys():
						query0 = reduce(operator.or_, ( Q(name__icontains=s.strip()) for s in payload['Search'].split(" ") ))
						query1 = reduce(operator.and_, ( Q(name__icontains=s.strip()) for s in payload['Search'].split(" ") ))

						if len(road_street)>0:
							road_street0 = road_street.filter(query1)
							if len(road_street0)>0:
								road_street1 = road_street0.filter(Q(name__icontains=payload['Search']))
								if len(road_street1)>0:
									road_street = road_street1
								else:
									road_street = road_street0

					road_street = road_street[:10]
					item = ''
					item_list = []
					count = 1
					for i in road_street:
						street = '%s(%s)' % (i.name,i.town_city.name)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, street, count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, street)
						item_list.append(street)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)



				elif variable_key == 'survey_item':
					from secondary.erp.survey.models import SurveyItem

					lgr.info("Search for string: %s" % payload['Search'])

					query0 = reduce(operator.or_, ( Q(name__icontains=s.strip()) for s in payload['Search'].split(" ") ))
					query1 = reduce(operator.and_, ( Q(name__icontains=s.strip()) for s in payload['Search'].split(" ") ))

					survey_item = SurveyItem.objects.filter(query0,Q(survey__group__data_name=variable_val),Q(survey__institution__id=code[0].institution.id) )
					if len(survey_item)>0:
						survey_item0 = survey_item.filter(query1)
						if len(survey_item0)>0:
							survey_item1 = survey_item0.filter(Q(name__icontains=payload['Search']))
							if len(survey_item1)>0:
								survey_item = survey_item1
							else:
								survey_item = survey_item0

					survey_item = survey_item[:10]
					item = ''
					item_list = []
					count = 1
					for i in survey_item:
						name = '%s' % (i.name)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, name, count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, name)
						item_list.append(name)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'ARTISTE_SEARCH_RESULTS':
					from secondary.erp.crm.models import Enrollment

					lgr.info("Search for string: %s" % payload['Search'])

					query0 = reduce(operator.or_, ( Q(member_alias__icontains=s.strip()) for s in payload['Search'].split(" ") ))
					query1 = reduce(operator.and_, ( Q(member_alias__icontains=s.strip()) for s in payload['Search'].split(" ") ))

					enrollment = Enrollment.objects.filter(query0,Q(institution__id=code[0].institution.id) )
					if len(enrollment)>0:
						enrollment0 = enrollment.filter(query1)
						if len(enrollment0)>0:
							enrollment1 = enrollment0.filter(Q(member_alias__icontains=payload['Search']))
							if len(enrollment1)>0:
								enrollment = enrollment1
							else:
								enrollment = enrollment0

					enrollment = enrollment[:10]
					item = ''
					item_list = []
					count = 1
					for i in enrollment:	
						artiste = '%s' % (i.member_alias)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, artiste, count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, artiste)
						item_list.append(artiste)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'mcsk_regions':
					from thirdparty.mcsk.models import Region

					regions = Region.objects.all()
					item = ''
					item_list = []
					count = 1
					for i in regions:
						lgr.info("Region: %s" % i)
						name = '%s' % (i.name)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, name, count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, name)
						item_list.append(name)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)

				elif variable_key == 'MUSIC_TOP_TEN':
					from products.muziqbit.models import Download

					download = Download.objects.filter(Q(music__product_item__institution__id=code[0].institution.id),\
								 music__product_item__status__name='ACTIVE').\
								values("music__product_item__name","music__artiste").\
								annotate(num_music=Count("music__product_item__name")).order_by("-num_music")[:10]

					#download = download[:10]

					item = ''
					item_list = []
					count = 1
					for i in download:
						song = '%s(%s)' % (i['music__product_item__name'],i['music__artiste'])
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, song, count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, song)
						item_list.append(song)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)


				elif variable_key == 'MUSIC_SEARCH_RESULTS':
					from products.muziqbit.models import Music

					lgr.info("Search for string: %s" % payload['Search'])

					query0 = reduce(operator.or_, ( Q(product_item__name__icontains=s.strip()) for s in payload['Search'].split(" ") ))
					query1 = reduce(operator.or_, ( Q(artiste__icontains=s.strip()) for s in payload['Search'].split(" ") ))
					query2 = reduce(operator.and_, ( Q(product_item__name__icontains=s.strip()) for s in payload['Search'].split(" ") ))
					query3 = reduce(operator.and_, ( Q(artiste__icontains=s.strip()) for s in payload['Search'].split(" ") ))

					#music = Music.objects.filter(Q(query0, query1) |Q(artiste__icontains=payload['Search'])|Q(product_item__name__icontains=payload['Search']) | query2 |query3,\
					#		 Q(product_item__institution__id=code[0].institution.id) )[:10]


					music = Music.objects.filter(query0|query1,Q(product_item__institution__id=code[0].institution.id),\
								 product_item__status__name='ACTIVE').order_by('-release_date')


					if len(music)>1:
						music0 = music.filter(query0|query1)
						if len(music0)>1:
							music1 = music0.filter(Q(product_item__name__icontains=payload['Search']) |Q(artiste__icontains=payload['Search']))
							if len(music1) > 1:
								music = music1
							else:
								music2 = music0.filter(query0,query1)
								if len(music2) > 1:
									music = music2
								else:
									music = music0

					music = music[:10]

					item = ''
					item_list = []
					count = 1
					for i in music:
						song = '%s(%s)' % (i.product_item.name,i.artiste)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, song, count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, song)
						item_list.append(song)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)



				elif variable_key == 'MUSIC_LATEST':
					from products.muziqbit.models import Music

					music = Music.objects.filter(product_item__institution__id=code[0].institution.id,\
								 product_item__status__name='ACTIVE').order_by('-release_date')[:10]

					item = ''
					item_list = []
					count = 1
					for i in music:
						song = '%s(%s)' % (i.product_item.name,i.artiste)
						if navigator.session.channel.name == 'IVR':
							item = '%s\nFor %s, press %s.' % (item, song, count)
						elif navigator.session.channel.name == 'USSD':
							item = '%s\n%s:%s' % (item, count, song)
						item_list.append(song)
						count+=1
					navigator.item_list = json.dumps(item_list)
					navigator.save()

					lgr.info('Your List: %s' % item)
					page_string = page_string.replace('['+v+']',item)


		payload['page_string'] = page_string

		return payload


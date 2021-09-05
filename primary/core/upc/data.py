from primary.core.upc.models import *

import logging

lgr = logging.getLogger('primary.core.upc')

class Data:
	def get_points_awarded(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['cols'] = []

		params['data'] = []
		params['lines'] = []

		max_id = 0
		min_id = 0
		ct = 0
		push = {}
        
		lgr.info('Started purchases_summary')
        
		item = {}
		item['count'] = 1500
        
		params['rows'] = [item]       

		return params,max_id,min_id,ct,push
    
	def get_points_redeemed(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['cols'] = []

		params['data'] = []
		params['lines'] = []

		max_id = 0
		min_id = 0
		ct = 0
		push = {}
        
		lgr.info('Started get_points_redeemed')
        
		item = {}
		item['count'] = 1000
		params['rows'] = [item]       

		return params,max_id,min_id,ct,push

	def get_successful_referrals(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['cols'] = []

		params['data'] = []
		params['lines'] = []

		max_id = 0
		min_id = 0
		ct = 0
		push = {}
        
		lgr.info('Started get_successful_referrals')
        
		item = {}
		item['count'] = 700

		params['rows'] = [item]       

		return params,max_id,min_id,ct,push    

    
	def get_refferal_earnings(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['cols'] = []

		params['data'] = []
		params['lines'] = []

		max_id = 0
		min_id = 0
		ct = 0
		push = {}
        
		lgr.info('Started get_refferal_earnings')
        
		item = {}
		item['count'] = 7000
        
		params['rows'] = [item]       

		return params,max_id,min_id,ct,push
 
	def mcsk_survey(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = [{"label": "index", "type": "string"}, {"label": "name", "type": "string"},
				  {"label": "image", "type": "string"}, {"label": "checked", "type": "string"},
				  {"label": "selectValue", "type": "string"}, {"label": "description", "type": "string"},
				  {"label": "color", "type": "string"}]

		item = {}
		item['count'] = 1000
		params['cols'] = [item]

		return params

	def points_awarded(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['cols'] = []

		params['data'] = []
		params['lines'] = []

		max_id = 0
		min_id = 0
		ct = 0
		push = {}
        
		lgr.info('Started points_awarded')
        
		item1 = {"January": 23, "February": 78}
		item2 = {"March": 43, "April": 27}
        
		params['rows'] = [item1, item2]       

		return params,max_id,min_id,ct,push    
    
	def notifications_summary(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = [{"label": "index", "type": "string"}, {"label": "name", "type": "string"},
				  {"label": "image", "type": "string"}, {"label": "checked", "type": "string"},
				  {"label": "selectValue", "type": "string"}, {"label": "description", "type": "string"},
				  {"label": "color", "type": "string"}]

		params['data'] = []
		params['lines'] = []

		max_id = 0
		min_id = 0
		ct = 0
		push = {}

		lgr.info('Started Notifications')

		try:
			outbound = Outbound.objects.using('read').filter(contact__product__notification__code__gateway=gateway_profile.gateway,\
				contact__product__notification__code__institution=gateway_profile.institution, date_created__gte=timezone.now()-timezone.timedelta(days=7)). \
				values('state__name'). \
				annotate(state_count=Count('state__name'))

			for o in outbound:
				item = {}
				item['name'] = o['state__name']
				item['count'] = '%s' % '{0:,.2f}'.format(o['state_count'])
				params['rows'].append(item)
		except Exception as e:
			lgr.info('Error on notifications: %s' % e)
		return params,max_id,min_id,ct,push
    
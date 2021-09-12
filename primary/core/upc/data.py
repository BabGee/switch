from primary.core.upc.models import *

from secondary.channels.notify import *

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
 

    
	def points_awarded(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = [{"label": "Event", "type": "string"}, {"label": "Points awarded", "type": "string"},
				  {"label": "Awarded date", "type": "string"}, {"label": "Expiry date", "type": "string"},
				  {"label": "Amount spent", "type": "string"}, {"label": "Points earned", "type": "string"},
				  {"label": "Available", "type": "string"}]

		params['data'] = []
		params['lines'] = []

		max_id = 0
		min_id = 0
		ct = 0
		push = {}

		lgr.info('Started points_awarded')

		item1 = ['Buy Goods', '2500', '29-08-2021', '30-08-2022', '25000', '250', '250']
		item2 = ['Pay Bill', '500', '31-08-2021', '2-09-2022', '2000', '50', '50']        
      
		params['rows'] = [item1, item2]
       
		return params,max_id,min_id,ct,push 
   

	def monthly_points_awarded(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = [{"label": "Month", "type": "string"}, {"label": "Points awarded", "type": "string"}]

		params['data'] = []
		params['lines'] = []

		max_id = 0
		min_id = 0
		ct = 0
		push = {}

		lgr.info('Started points_awarded')

		item1 = ['1', '70']
		item2 = ['2', '80']
		item3 = ['3', '150']
		item4 = ['4', '180'] 
		item5 = ['5', '120']
		item6 = ['6', '90']  
		item7 = ['7', '150']
		item8 = ['8', '130']
		item9 = ['9', '200']
		item10 = ['10', '180'] 
		item11 = ['11', '190']
		item12 = ['12', '210']        
      
		params['rows'] = [item1, item2, item3, item4, item5, item6, item7, item8, item9, item10, item11, item12]
       
		return params,max_id,min_id,ct,push
    
    
	def get_referrals_distribution(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []        
		params['cols'] = [{"label": "SMS", "type": "string"}, {"label": "Whatsapp", "type": "string"},
				  {"label": "Twitter", "type": "string"}, {"label": "Facebook", "type": "string"}]

		params['data'] = []
		params['lines'] = []

		max_id = 0
		min_id = 0
		ct = 0
		push = {}
        
		lgr.info('Started get_referrals_distribution')

		item = ['60', '70', '40', '90']
      
		params['rows'] = [item]       

		return params,max_id,min_id,ct,push    
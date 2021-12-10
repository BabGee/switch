from primary.core.upc.models import *

from secondary.channels.notify import *

from products.nikobizz.models import *

from django.db.models import Sum

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
        
		lgr.info('Started get_points_awarded')
        
		item = {}
		item['count'] = 1500
		# gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
		# institution = gateway_profile.institution
		# total_points = PointsEarned.objects.filter(customer__institution=institution).aggregate(Sum('points_earned'))
		# item['count'] = total_points['points_earned__sum']    
    
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
		params['cols'] = [{"label": "Event", "type": "string", "search_fields":True}, {"label": "Points awarded", "type": "string"},
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

		item1 = ['Order 307', '300', '29-08-2021', '30-08-2022', '3000', '300', '250']
		item2 = ['Order 308', '500', '31-08-2021', '2-09-2022', '5000', '5000', '100']
		item3 = ['Order 309', '100', '31-08-2021', '2-09-2022', '1000', '100', '50']
		item4 = ['Order 310', '250', '31-08-2021', '2-09-2022', '2500', '250', '250']
		item5 = ['Order 311', '350', '1-09-2021', '3-09-2022', '3500', '350', '80']        
      
		params['rows'] = [item1, item2, item3, item4, item5]
       
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
		params['cols'] = [{"label": "PEDIATRICIAN", "type": "string"}, {"label": "EYE CHECKUP", "type": "string"},
				  {"label": "DENTIST", "type": "string"}, {"label": "OTHERS", "type": "string"}]

		params['data'] = []
		params['lines'] = []

		max_id = 0
		min_id = 0
		ct = 0
		push = {}
        
		lgr.info('Started get_referrals_distribution')

		item = ['160', '300', '90', '150']
      
		params['rows'] = [item]       

		return params,max_id,min_id,ct,push  
    
    
	def get_gender_distribution(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []        
		params['cols'] = [{"label": "MALE", "type": "string"}, {"label": "FEMALE", "type": "string"}]

		params['data'] = []
		params['lines'] = []

		max_id = 0
		min_id = 0
		ct = 0
		push = {}
        
		lgr.info('Started get_gender_distribution')

		item = ['160', '300']
      
		params['rows'] = [item]       

		return params,max_id,min_id,ct,push    
    
    
	def get_payments(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []
		params['cols'] = [{"label": "DAYS", "type": "string"}, {"label": "PAYMENTS", "type": "string"}]

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
    
    
	def get_upcoming_appointments(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params["rows"] = []
		params["cols"] = [
            {
               "label":"Time",
               "type":"string",
               "value":"id"
            },
            {
               "label":"Patient Name",
               "type":"string",
               "value":"name"
            },
            {
               "label":"Appointed to",
               "type":"string",
               "value":"description"
            },
            {
               "label":"Department",
               "type":"file",
               "value":"image"
            }
         ]      
               
		params['data'] = []
		params['lines'] = []       

		max_id = 0
		min_id = 0
		ct = 0
		push = {}

		lgr.info('Started get_upcoming_appointments')     
      
		params["rows"] = [
            [
               {
                  "from":1638622447680,
                  "to":1638622447680
               },
               "Customize messages",
               "mpesa",
               "src/themes/dsv1.0/img/mastercard.svg"
            ],
            [
               {
                  "from":1638439899572,
                  "to":1638439899572
               },
               "Reach contact groups",
               "mpesa",
               "src/themes/dsv1.0/img/mpesa.svg"
            ],
            [
               {
                  "from":1638439899572,
                  "to":1638439899572
               },
               "Purchase Float",
               "mpesa",
               "src/themes/dsv1.0/img/paypal.svg"
            ]]
       
		return params,max_id,min_id,ct,push    

    
	def get_next_client(self, payload, gateway_profile, profile_tz, data):
		params = {}
		params['rows'] = []        
		params['cols'] = [
         {'type': 'string', 'value': 'contact_group__id', 'label': 'Upcoming Appointment'},
         {'type': 'string', 'value': 'contact_group__name', 'label': 'Last Appointment'},
         {'type': 'string', 'value': 'contact_group__description', 'label': 'Total Visits'},
         {'type': 'number', 'value': 'Contact Count', 'label': 'Reason'},
       ]

		params['data'] = []
		params['lines'] = []
        
        
		# groups = [{
		# age: 23,
		# name: "Nathan Machoka",
		# gender: "Male",
		# image: "src/themes/dsv1.0/img/mastercard.svg"
		# }]

		max_id = 0
		min_id = 0
		ct = 0
		push = {}
        
		lgr.info('Started get_next_client')


		item = ["29-08-2021", "29-08-2021", '1', "Eye Problem"]    
		params['rows'] = [item]       

		return params,max_id,min_id,ct,push    
    
    
    
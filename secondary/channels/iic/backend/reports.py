from pos.models import *
from decimal import Decimal, ROUND_DOWN
from django.utils import timezone
from django.db.models import Count, Min, Sum, Avg, Max
from datetime import datetime, timedelta
from django.utils.dateformat import DateFormat 
import pytz,  time
import simplejson as json
from django.utils.translation import ugettext, ungettext
from django.db.models import Q

import logging
lgr = logging.getLogger('secondary.channels.iic')

class DataSource:
	payload, input_variable, data, delta = {}, [], {}, None
	institution_till, registry_products, product_transaction = [],[],[]
	def __init__(self):
		#Place Queries before filters	
		self.registry_products = RegistryProduct.objects.select_related()
		self.product_transaction = ProductTransaction.objects.select_related()
		self.products= Product.objects.select_related()
		self.featured = FeaturedProduct.objects.select_related()
		self.institution_till = InstitutionTill.objects.select_related()

	def time_ago(self):
		date_str = ''
		if self.delta is not None:
			chunks = (
				(365.0, lambda n: ungettext('year', 'years', n)),
				(30.0, lambda n: ungettext('month', 'months', n)),
				(7.0, lambda n : ungettext('week', 'weeks', n)),
				(1.0, lambda n : ungettext('day', 'days', n)),
				)

			for i, (chunk, name) in enumerate(chunks):
				if abs(self.delta.days) >= chunk:
					count = abs(round(self.delta.days / chunk, 0))
					break

			if self.delta.days == 0: date_str = "today"
			elif self.delta.days == -1: date_str = "yesterday"
			elif self.delta.days == 1: date_str = "tomorrow"
			else: date_str = ugettext('%(number)d %(type)s') % {'number': count, 'type': name(count)}
		else:
			date_str = 'Not Provided'

		return date_str

	def create_report(self):#Do Query Filters
		lgr.info('Self Paylod: %s' % self.payload)
		#if self.input_variable[4] == 'PieChart':
		days30 = datetime.now() + timedelta(-180)
		user = User.objects.filter(id=self.payload['user_id'])
		timezone.activate(pytz.timezone(user[0].profile.timezone))
		lgr.info('DateTime: %s' % days30)
		local_days30 = pytz.timezone(user[0].profile.timezone).localize(days30)
		timezone.activate(pytz.timezone(user[0].profile.timezone))

		if 'institution_id' in self.payload.keys() and self.payload['institution_id'] not in ["",None,'None']:
			lgr.info('Filter for All with Institution')
			self.registry_products = self. registry_products.filter(product__institution_till__institution__id=self.payload['institution_id'])
			self.product_transaction = self.product_transaction.filter(created_by__profile__institution__id=self.payload['institution_id'], date_created__gte=local_days30)
			self.products = self.products.filter(institution_till__institution__id=self.payload['institution_id'])
			self.featured = self.featured.filter(product__institution_till__institution__id=self.payload['institution_id'], date_created__gte=local_days30)
			self.institution_till = self.institution_till.filter(institution__id=self.payload['institution_id'])

		else: 
			lgr.info('DateTime Aware: %s' % local_days30)
			#trans = RegistryTransaction.objects.filter(date_created__gte=start_date, date_created__lte=end_date).order_by('-date_created')[:500]
			if user[0].profile.access_level.name in ['OPERATOR','MANAGER','SUPERVISOR']:
				lgr.info('Filter for Operator, Manager & SUPERVISOR')
				self.registry_products = self. registry_products.filter(product__institution_till__institution=user[0].profile.institution)
				self.product_transaction = self.product_transaction.filter(created_by__profile__institution=user[0].profile.institution, date_created__gte=local_days30)
				self.products = self.products.filter(institution_till__institution=user[0].profile.institution)
				self.featured = self.featured.filter(product__institution_till__institution=user[0].profile.institution, date_created__gte=local_days30)
				self.institution_till = self.institution_till.filter(institution=user[0].profile.institution)

			else:
				lgr.info('Filter for Rest of Profile and No Institution to None')
				self.registry_products = self. registry_products.none()
				self.product_transaction = self.product_transaction.none()
				self.products = self.products.none()
				self.featured = self.featured.none()
				self.institution_till = self.institution_till.none()

		if self.input_variable[4] == 'SELECT PRODUCT':
			lgr.info('Getting Product Select')
			content = {}
			for t in self.products:
				content[t.id] = '%s %s (%s)' % (t.name, t.kind, t.product_type.metric)

			lgr.info('Content: %s' % content)
			self.input_variable[5] = content

		elif self.input_variable[0] == 'PRODUCT IMAGES':

			images = []
			#Filters
			for t in self.products.filter(id=self.payload['reference']):
				images.append(t.photo.name)
				for i in ProductImage.objects.filter(product=t):
					images.append(i.photo.name)
			lgr.info('Product Images: %s' % images)
			self.input_variable[5] = images


		elif self.input_variable[0] == 'SEARCH RESULTS':
			content = {}
			#Filters
			if 'PRICE RANGE' in self.payload.keys() and self.payload['PRICE RANGE'] not in [';','',None]:
				price = self.payload['PRICE RANGE'].split(';')
				self.products = self.products.filter(unit_cost__gte=price[0],unit_cost__lte=price[1]) if (len(price)>1) else self.products
			if 'PRODUCT TYPE CATEGORY' in self.payload.keys() and self.payload['PRODUCT TYPE CATEGORY'] not in [';','',None]:
				product = self.payload['PRODUCT TYPE CATEGORY'].split(';')
				self.products = self.products.filter(product_type__product_category__name=product[0],product_type__name=product[1]) if (len(product)>1) else self.products
			if 'PRODUCT NAME KIND' in self.payload.keys() and self.payload['PRODUCT NAME KIND'] not in [';','',None]:
				product = self.payload['PRODUCT NAME KIND'].split(';')
				self.products = self.products.filter(name=product[0],kind=product[1]) if (len(product)>1) else self.products

			for t in self.products:
				cost = '{0:,.2f}'.format(t.unit_cost) if t.unit_cost > 0 else str(t.cost_status.name)
				currency = t.institution_till.till_currency.code
				price = '%s %s' % (currency, cost)

				manufactured = str(DateFormat(t.manufactured).format('Y-m-d')) if t.manufactured is not None else None
				images = []
				images.append(t.photo.name)
				for i in ProductImage.objects.filter(product=t):
					images.append(i.photo.name)
				content[t.id] = {
							'reference': t.id,
							'name': t.name,
							'kind': t.kind,
							'images': images,
							'price': price,
							'type': t.product_type.name,
							'category': t.product_type.product_category.name,
							'trading': t.trading.name,	
								}

				details = json.loads(t.details.decode('string-escape').strip('"')) if t.details not in [None,''] else {}
				content[t.id].update(details)

			lgr.info('Featured Products Content: %s' % content)
			self.input_variable[5] = content

		elif self.input_variable[4] == 'TILL LOCATION':
			lgr.info('Getting Price Range')
			total_products = self.products.values('institution_till__city').distinct()
			content = {}
			for t in total_products:
				if t['institution_till__city'] not in [None, '']:
					content[t['institution_till__city']] = t['institution_till__city']

			lgr.info('Content: %s' % content)
			self.input_variable[5] = content

		elif self.input_variable[4] == 'PRICE RANGE':
			lgr.info('Getting Price Range')
			total_products = self.products.values('institution_till__till_currency__code').annotate(Max('unit_cost'),Min('unit_cost'))
			content = {}
			lgr.info('Total Products: %s' % total_products)
			for t in total_products:
				lgr.info('Price Range Item: %s' % t)
				if t['unit_cost__min'] is not None and t['unit_cost__max'] is not None:
					content['min'] = int(t['unit_cost__min'])
					content['max'] = int(t['unit_cost__max'])
					content['step'] = '100000'
					content['range'] = t['institution_till__till_currency__code']
			lgr.info('Content: %s' % content)
			self.input_variable[5] = content

		elif self.input_variable[4] == 'YEAR RANGE':
			lgr.info('Getting Year Range')
			content = {}
			for t in self.products.extra(select={"max": "MAX(EXTRACT(YEAR  FROM manufactured))", "min": "MIN(EXTRACT(YEAR  FROM manufactured))"}).distinct().values('min','max'):
				if t['min'] is not None and t['max'] is not None:
					content['min'] = int(t['min'])
					content['max'] = int(t['max'])
					content['step'] = '1'
					content['range'] = 'Y'
			lgr.info('Content: %s' % content)
			self.input_variable[5] = content

		elif self.input_variable[4] == 'PRODUCT TYPE CATEGORY':
			lgr.info('Getting Institution Tills')
			content = {}
			for t in self.products.values('product_type__product_category__name','product_type__name').annotate():
				if t['product_type__product_category__name'] not in content.keys():
					content[t['product_type__product_category__name']] = []
				if t['product_type__name'] not in content[t['product_type__product_category__name']]:
					content[t['product_type__product_category__name']].append(t['product_type__name'])
			self.input_variable[5] = content

		elif self.input_variable[4] == 'PRODUCT NAME KIND':
			lgr.info('Getting Institution Tills')
			content = {}
			for t in self.products.values('name','kind').annotate():
				if t['name'] not in content.keys():
					content[t['name']] = []
				if t['kind'] not in content[t['name']]:
					content[t['name']].append(t['kind'])
			self.input_variable[5] = content

		elif self.input_variable[0] == 'INSTITUTION TILLS':
			lgr.info('Getting Institution Tills')
			content = {}
			for t in self.institution_till:
				lgr.info('Started Loop!: %s' % t)
				if t.name not in content.keys():
					content[t.name] = {}
				content[t.name]['logo'] = t.logo 
				content[t.name]['institution'] = t.institution.name
				content[t.name]['city'] = t.city
				content[t.name]['physical address'] = t.physical_addr
				details = json.loads(t.details.decode('string-escape').strip('"')) if t.details not in [None,''] else {}
				content[t.name].update(details)

			lgr.info('Products Categories Content: %s' % content)
			self.input_variable[5] = content

		elif self.input_variable[0] == 'CONTACT MAP':
			content = []
                        for t in self.institution_till:
				s = [t.geometry.y, t.geometry.x, t.name]
				content.append(s)

			self.input_variable[5] = content

		elif self.input_variable[0] == 'PRODUCT CATEGORIES':
			content = {}
			total_products = self.products.values('product_type__id','product_type__name','product_type__product_category__name','product_type__product_category__icon').annotate(product_sum=Count('id'))

			for t in total_products:
				if t['product_type__product_category__name'] not in content.keys():
					content[t['product_type__product_category__name']] = {'icon': t['product_type__product_category__icon']}
				content[t['product_type__product_category__name']][t['product_type__name']] = [t['product_type__id'], t['product_sum']]
			lgr.info('Products Categories Content: %s' % content)
			self.input_variable[5] = content

		elif self.input_variable[0] == 'RECENT PRODUCTS':

			content = {}
			count = 0
                        for t in self.products.order_by("-date_created"):
				content[count] = {}
				self.delta = timezone.now()-t.date_created
				content[count]['Time Available'] =  str(self.time_ago())
				content[count]['name'] =  t.name
				content[count]['kind'] =  t.kind

				cost = '{0:,.2f}'.format(t.unit_cost) if t.unit_cost > 0 else str(t.cost_status.name)
				currency = t.institution_till.till_currency.code
				price = '%s %s' % (currency, cost)
				content[count]['price'] =  price

				content[count]['type'] =  t.product_type.name
				content[count]['category'] =  t.product_type.product_category.name
				content[count]['trade'] =  t.trading.name
				images = []
				images.append(t.photo.name)
				for i in ProductImage.objects.filter(product=t):
					images.append(i.photo.name)
				content[count]['images'] =  images
				details = json.loads(t.details.decode('string-escape').strip('"')) if t.details not in [None,''] else {}
				content[count].update(details)

				count +=1
			self.input_variable[5] = content


		elif self.input_variable[0] == 'RECENT SIDEBAR PRODUCTS':
			content = {}
			count = 0
			for t in self.products.order_by('-date_created')[:5]:
				cost = '{0:,.2f}'.format(t.unit_cost) if t.unit_cost > 0 else str(t.cost_status.name)
				currency = t.institution_till.till_currency.code
				price = '%s %s' % (currency, cost)

				manufactured = str(DateFormat(t.manufactured).format('Y-m-d')) if t.manufactured not in [None,'']else None
				
				content[count] = {
							'reference': t.id,
							'name': t.name,
							'kind': t.kind,
							'image': t.photo.name,
							'price': price,
							'type': t.product_type.name,
							'category': t.product_type.product_category.name,
							'trading': t.trading.name,	
							}

				details = json.loads(t.details.decode('string-escape').strip('"')) if t.details not in [None,''] else {}
				content[count].update(details)

				count+=1

			lgr.info('Recent Products Content: %s' % content)
			self.input_variable[5] = content

		elif self.input_variable[0] == 'FEATURED PRODUCTS':
			content = {}
			for t in self.featured[:5]:
				cost = '{0:,.2f}'.format(t.product.unit_cost) if t.product.unit_cost > 0 else str(t.product.cost_status.name)

				currency = t.product.institution_till.till_currency.code
				if cost > 0:
					price = '%s %s' % (currency, cost)
				manufactured = str(DateFormat(t.product.manufactured).format('Y-m-d')) if t.product.manufactured is not None else None

				content[t.item_level] = {
							'reference': t.product.id,
							'name': t.product.name,
							'kind': t.product.kind,
							'image': t.product.photo.name,
							'price': price,
							'type': t.product.product_type.name,
							'category': t.product.product_type.product_category.name,
							'trading': t.product.trading.name,	
								}

				details = json.loads(t.product.details.decode('string-escape').strip('"')) if t.product.details not in [None,''] else {}
				content[t.item_level].update(details)

			lgr.info('Featured Products Content: %s' % content)
			self.input_variable[5] = content

		elif self.input_variable[0] == 'TOTAL REGISTRIES':
			total_registrations = self.registry_products.values('user__id').distinct().count()
			self.input_variable[5] = ['TOTAL REGISTRIES',total_registrations]

		elif self.input_variable[0] == 'REGISTRY TRANSACTIONS':
			total_transactions = self.product_transaction.values('id').distinct().count()
			self.input_variable[5] = ['REGISTRY TRANSACTIONS',total_transactions]

		elif self.input_variable[0] == 'REGISTRY PRODUCTS':
			total_products = self.registry_products.values('product__id').distinct().count()
			self.input_variable[5] = ['REGISTRY PRODUCTS',total_products]

		elif self.input_variable[0] == 'TOTAL PRODUCTS':
			total_products = self.products.values('name').distinct().count()
			self.input_variable[5] = ['TOTAL PRODUCTS',total_products]


		elif self.input_variable[0] == 'PRODUCTS PIE CHART':
			lgr.info('Started Products Pie Chart')
			total_products = self.registry_products.values('product__product_type__product_category__name').annotate(Count('id', distinct=True))
			lgr.info('Got Products: %s' % total_products)

			header = ['Product', 'No. of Registry with Product']
			content = []
			content.append(header)
			count = 0
			for p in total_products:
				s = [p['product__product_type__product_category__name'],p['id__count']]
				content.append(s)
				count+=1
			if count>0:
				self.input_variable[5] = content

		elif self.input_variable[0] == 'TRANSACTION DISTRIBUTION':
			content = []
                        for t in self.product_transaction:
				user = None
				if t.user is not None:
					user = '%s %s' % (t.user.first_name, t.user.last_name)
				s = [t.transaction.geometry.y, t.transaction.geometry.x, user]
				content.append(s)

			self.input_variable[5] = content

			lgr.info('Response: %s' % self.input_variable)

		elif self.input_variable[0] == 'REGISTRATION DISTRIBUTION':
			total_registrations = self.registry_products.distinct('user__id')
			content = []
                        for t in total_registrations:
				s = [t.user.profile.geometry.y, t.user.profile.geometry.x, t.user.first_name]
				content.append(s)

			self.input_variable[5] = content
			'''
			if self.input_variable[4] == 'GeoChart':
				self.input_variable[5] =  [
					['Lat', 'Long', 'Name', 'Registrations'],
					  [1.2833, 36.8167, 'KE-NBI', 10900],
					  [4.0500, 39.6667, 'KE-MBA', 200],
				          [1.5167, 37.2667, 'US-NJ', 70000],
						]
			elif self.input_variable[4] == 'Map':
				self.input_variable[5] =  [
					['Lat', 'Long', 'tooltip'],
					  [1.2833, 36.8167, '<div class="row">KE-NBI <br> Registrations: 10900</div>'],
					  [4.0500, 39.6667, '<div class="row">KE-MBA  <br> Registrations: 200</div>'],
			        	  [1.5167, 37.2667, '<div class="row">US-N  <br> Registrations: J70000</div>'],
							]
			'''
		elif self.input_variable[0] == 'REGISTRATION TRENDS':
			total_registrations = self.registry_products.extra({'created':"date(regix_registryproduct.date_created)"}).values('created').annotate(Count('user__id', distinct=True))
			content = []
                        header = ['Timeline', 'No. of Registries']
			content.append(header)
                        for t in total_registrations:
				s = [DateFormat(t['created']).format('Y-m-d'), t['user__id__count']]
				content.append(s)

			self.input_variable[5] = content


		elif self.input_variable[0] == 'TRANSACTION TRENDS':
			total_transactions = self.product_transaction.extra({'created':"date(regix_producttransaction.date_created)"}).values('created', 'transaction_type__name').annotate(Count('id', distinct=True))
			content = []
                        header = ['Timeline',]
                        for t in total_transactions:
				s = [DateFormat(t['created']).format('Y-m-d')]
				if t['transaction_type__name'] not in header:
					header.append(t['transaction_type__name'])
				if len(header)>len(s):
					for i in range(len(s),len(header)):
						s.append(0)
				if t['transaction_type__name'] in header:
					s[header.index(t['transaction_type__name'])] = t['id__count']
				content.append(s)

			content_write = []
			content_write.append(header)
			for c in content:
				for i in range(len(c), len(header)):
					c.append(0)
				content_write.append(c)
			self.input_variable[5] = content_write


		elif self.input_variable[0] == 'REGISTRATION TRANSACTIONS':
			content_write = []
                        header = ['ID', 'CUSTOMER','REFERENCE','CREATED']
			content_write.append(header)
			for t in self.product_transaction:
				date_created = t.date_created
                                date_created = timezone.localtime(date_created)
                                #df = DateFormat(date_created)
                                #df.format(get_format('DATE_FORMAT'))
                                #df.format('d-m-Y H:i:s Zz')
                                amount = '%s %s' % (t.amount, t.currency.code)
                                quantity = '%s %s' % (t.quantity, t.metric.si_unit)
                                this_t= 'T%d' % t.id
                                #content = [this_t, t.id_number, t.reference.name, quantity, amount, t.comment, t.status.name, str(date_created.strftime("%d %b %Y %I:%M:%S %p %Z %z"))]
                                content = [this_t, t.id_number, t.reference.name, str(date_created.strftime("%d %b %Y %I:%M:%S %p %Z %z"))]

                                #content = [str(c).replace(',','&#44;') for c in content]
                                content_write.append(content)
			
			self.input_variable[5] = content_write

		elif self.input_variable[0] == 'RECENT TRANSACTIONS':
			content = {}
			count = 0
                        for t in self.product_transaction.order_by("-date_created"):
                                date_created = timezone.localtime(t.date_created)
				content[count] = {}
				content[count]['created by'] = str(t.created_by.first_name)
				content[count]['reference'] =  t.reference
				content[count]['name'] =  t.transaction_type.product_type.name
				content[count]['kind'] =  t.transaction_type.product_type.product_category.name

				if t.quantity is not None:
					content[count]['quantity'] =  '%s %s' % (t.quantity, t.transaction_type.product_type.metric)
				if t.user is not None:
					if t.user.profile.dob is not None: self.delta = timezone.now().date()-t.user.profile.dob
					content[count]['user name'] = str(t.user.first_name+' '+t.user.last_name).title()
					content[count]['gender '] = str(t.user.profile.gender)
					content[count]['age'] =  str(self.time_ago())
				count +=1
			self.input_variable[5] = content

		elif self.input_variable[0] == 'RECENT PROFILES':
			content = {}
                        for t in self.registry_products.order_by("-date_created"):
                                date_created = timezone.localtime(t.date_created)
				content[t.id] = {}
				content[t.id]['created by'] = str(t.created_by.first_name)
				if t.user is not None:
					if t.user.profile.dob is not None: self.delta = timezone.now().date()-t.user.profile.dob
					content[t.id]['reference'] =  t.user.id,
					content[t.id]['name'] = str(t.user.first_name+' '+t.user.last_name).title()
					content[t.id]['kind'] = str(t.user.profile.gender)
					content[t.id]['images'] =  []
					content[t.id]['age'] =  str(self.time_ago())


			self.input_variable[5] = content

		elif self.input_variable[0] == 'DAILY REGISTRATION':
			self.input_variable[5] =  [
				['Year', 'Sales', 'Expenses'],
                		  ['2004',  1000,      400],
        	        	  ['2005',  1170,      460],
        	        	  ['2006',  660,       1120],
        		          ['2007',  1030,      540]
						]
class Report(DataSource):
	def fetch(self, payload, input_variable):
		try:
			self.payload = payload
			self.input_variable = input_variable
			lgr.info('\n\n\tInput Info: %s\n\n' % self.input_variable)
			self.create_report()
		except Exception, e:
			lgr.info('Error on Report: %s' % e)
		return self.input_variable


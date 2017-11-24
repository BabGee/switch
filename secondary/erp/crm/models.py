from django.contrib.gis.db import models
from primary.core.bridge.models import *

class Metric(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	si_unit = models.CharField(max_length=45)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.si_unit)

class ProductStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class ProductCategory(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	industry = models.ForeignKey(Industry)
	description = models.CharField(max_length=100)
	status = models.ForeignKey(ProductStatus)
	icon = models.CharField(max_length=45, null=True, blank=True)
	def __unicode__(self):
		return u'%s %s' % (self.name, self.industry)

class ShopProductCategory(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	status = models.ForeignKey(ProductStatus)
	icon = models.CharField(max_length=45, null=True, blank=True)
	industry = models.ForeignKey(IndustryClass,null=True, blank=True)
	def __unicode__(self):
		return u'%s %s' % (self.name, self.industry)

class ProductionFrequency(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	status = models.ForeignKey(ProductStatus)
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class ProductType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	product_category = models.ForeignKey(ProductCategory)
	metric = models.ForeignKey(Metric, null=True, blank=True)
	description = models.CharField(max_length=100)
	status = models.ForeignKey(ProductStatus)
	service = models.ForeignKey(Service, null=True, blank=True) #For Processing LOCAL endpoints
	institution_till = models.ForeignKey(InstitutionTill, blank=True, null=True)
	icon = models.CharField(max_length=45, null=True, blank=True)
	payment_method = models.ManyToManyField(PaymentMethod, blank=True)
	def __unicode__(self):
		return u'%s' % (self.name)
	def payment_method_list(self):
		return "\n".join([a.name for a in self.payment_method.all()])

class ShopProductType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45)
	shop_product_category = models.ForeignKey(ShopProductCategory)
	description = models.CharField(max_length=100)
	status = models.ForeignKey(ProductStatus)
	icon = models.CharField(max_length=45, null=True, blank=True)
	institution = models.ForeignKey(Institution)
	def __unicode__(self):
		return u'%s' % (self.name)


class ProductCharge(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	institution = models.ManyToManyField(Institution, blank=True)
	product_type = models.ManyToManyField(ProductType, blank=True)
	credit = models.BooleanField(default=False) #Dr | Cr (add charge if Dr, sub charge if Cr)
	till = models.ManyToManyField(InstitutionTill, blank=True)#If blank, all tills would work with discount
	expiry = models.DateTimeField(null=True, blank=True)
	min_amount = models.IntegerField()
	max_amount = models.IntegerField()
	currency = models.ForeignKey(Currency)
	charge_value = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	is_percentage = models.BooleanField(default=False)
	description = models.CharField(max_length=200, null=True, blank=True)
	for_float = models.NullBooleanField(default=False) #True=Float Manager Charge
	payment_method = models.ManyToManyField(PaymentMethod, blank=True)
	def __unicode__(self):
		return u'%s %s' % (self.product_type,self.charge_value)
	def institution_list(self):
		return "\n".join([a.name for a in self.institution.all()])
	def product_type_list(self):
		return "\n".join([a.name for a in self.product_type.all()])
	def till_list(self):
		return "\n".join([a.name for a in self.till.all()])
	def payment_method_list(self):
		return "\n".join([a.name for a in self.payment_method.all()])

class ProductDiscount(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	institution = models.ManyToManyField(Institution, blank=True)
	coupon = models.CharField(max_length=45, null=True, blank=True)
	product_type = models.ManyToManyField(ProductType, blank=True)
	credit = models.BooleanField(default=False) #Dr | Cr (add charge if Dr, sub charge if Cr)
	till = models.ManyToManyField(InstitutionTill, blank=True)#If blank, all tills would work with discount
	expiry = models.DateTimeField(null=True, blank=True)
	min_amount = models.IntegerField()
	max_amount = models.IntegerField()
	currency = models.ForeignKey(Currency)
	charge_value = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	is_percentage = models.BooleanField(default=False)
	description = models.CharField(max_length=200, null=True, blank=True)
	for_float = models.NullBooleanField(default=False) #True=Float Manager Coupon
	def __unicode__(self):
		return u'%s' % (self.coupon)
	def institution_list(self):
		return "\n".join([a.name for a in self.institution.all()])
	def product_type_list(self):
		return "\n".join([a.name for a in self.product_type.all()])
	def till_list(self):
		return "\n".join([a.name for a in self.till.all()])

class ProductDisplay(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class ProductItem(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45)
	description = models.CharField(max_length=200, null=True, blank=True)
	status = models.ForeignKey(ProductStatus)
	product_type = models.ForeignKey(ProductType)
	#institution_till = models.ManyToManyField(InstitutionTill, blank=True)
	unit_limit_min = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	unit_limit_max = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	unit_cost =  models.DecimalField(max_digits=19, decimal_places=2) 
	variable_unit = models.NullBooleanField(default=False) #The product cost has no fixed unit sale, e.g. donations
	float_limit_min = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	float_limit_max = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	float_cost =  models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True) 
	institution = models.ForeignKey(Institution)
	currency = models.ForeignKey(Currency)
	vat =  models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True) 
	discount =  models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True) 
	institution_url = models.CharField(max_length=640, null=True, blank=True)
	institution_username = models.CharField(max_length=320, null=True, blank=True, help_text='Optional')
	institution_password = models.CharField(max_length=320, null=True, blank=True, help_text='Optional')
	default_image = models.ImageField(upload_to='crm_productitem_imagepath/', max_length=200, null=True,blank=True)
	product_display = models.ForeignKey(ProductDisplay)
	uneditable = models.BooleanField(default=False)
	kind = models.CharField(max_length=100, null=True, blank=True)
	default_product = models.FileField(upload_to='crm_productitem_productpath/', max_length=200, blank=True, null=True)
	buying_cost =  models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True) 
	shop_product_type = models.ForeignKey(ShopProductType, blank=True, null=True)
	def __unicode__(self):
		return u'%s %s' % (self.id, self.name)
	def institution_till_list(self):
		return "\n".join([a.name for a in self.institution_till.all()])

class ProductImage(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	product_item = models.ForeignKey(ProductItem)
	image = models.ImageField(upload_to='crm_productitem_imagepath/', max_length=200, null=True,blank=True)
	name = models.CharField(max_length=45, blank=True, null=True)
	description = models.CharField(max_length=100, blank=True, null=True)
	default = models.BooleanField(default=False)
	def __unicode__(self):
		return u'%s' % (self.name)

class ItemExtra(models.Model):
	product_item = models.OneToOneField(ProductItem)
	product_source_capacity_min = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	product_source_capacity_max = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	default_image = models.ImageField(upload_to='productitem_default_image/', max_length=200, blank=True, null=True)
	product_path = models.FileField(upload_to='crm_productitem_productpath/', max_length=200, blank=True, null=True)
	product_url = models.CharField(max_length=400, null=True, blank=True)
	condition = models.CharField(max_length=200, null=True, blank=True)
	feature = models.CharField(max_length=200, null=True, blank=True)
	manufacturer = models.CharField(max_length=200, null=True, blank=True)
	manufactured = models.DateField(null=True, blank=True)
	product_owner = models.ForeignKey(User, null=True, blank=True) #Seller
	details = models.CharField(max_length=1240, null=True, blank=True)
	def __unicode__(self):
		return u'%s' % (self.product_item)


class EnrollmentStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class EnrollmentType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	product_item = models.ForeignKey(ProductItem)
	def __unicode__(self):
		return u'%s' % (self.name)

class Enrollment(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	record = models.CharField(max_length=200)
	alias = models.CharField(max_length=50)
	status = models.ForeignKey(EnrollmentStatus)
	enrollment_date = models.DateField()
	enrollment_type = models.ForeignKey(EnrollmentType)
	profile = models.ForeignKey(Profile)
	def __unicode__(self):
		return u'%s %s %s' % (self.profile, self.record, self.alias)

class PaymentOptionStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class PaymentOption(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	account_alias = models.CharField(max_length=200, null=True, blank=True)
	account_record = models.CharField(max_length=50)
	status = models.ForeignKey(PaymentOptionStatus)
	payment_method = models.ForeignKey(PaymentMethod)
	profile = models.ForeignKey(Profile)
	def __unicode__(self):
		return u'%s %s' % (self.profile, self.account_alias)


class NominationStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class Nomination(models.Model):
	date_modified = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	profile = models.ForeignKey(Profile)
	account_alias = models.CharField(max_length=200, null=True, blank=True)
	account_record = models.CharField(max_length=50)
	institution = models.ForeignKey(Institution)
	product_type = models.ForeignKey(ProductType)
	status = models.ForeignKey(NominationStatus)
	def __unicode__(self):
		return u'%s %s' % (self.profile, self.account_record)

class RecurrentServiceStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class RecurrentService(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	nomination = models.ForeignKey(Nomination, null=True, blank=True)
	enrollment = models.ForeignKey(Enrollment, null=True, blank=True)
	currency = models.ForeignKey(Currency, null=True, blank=True)
	amount = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	request = models.CharField(max_length=1920)
	service = models.ForeignKey(Service)#Tip: If failure, reverse service to notify
	request_auth = models.BooleanField(default=False) #If True, Bill automatically, false, request for auth
	scheduled_send = models.DateTimeField()
	scheduled_days = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
	expiry = models.DateTimeField(null=True, blank=True)
	status = models.ForeignKey(RecurrentServiceStatus)
	def __unicode__(self):
		return u'%s %s %s' % (self.enrollment, self.service, self.amount)



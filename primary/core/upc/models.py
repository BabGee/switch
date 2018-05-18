from django.contrib.gis.db import models
from primary.core.administration.models import *
from primary.core.api.models import *
from django.core.validators import RegexValidator


class InstitutionStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class MSISDN(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	#phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
	phone_regex = RegexValidator(regex=r'^\+\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
	phone_number = models.CharField(validators=[phone_regex], max_length=15, unique=True) # validators should be a list
	is_active = models.NullBooleanField(default=False)
	def __unicode__(self):
		return u'%s' % (self.phone_number)

class Institution(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=200)
	business_number = models.CharField(max_length=8, unique=True, help_text="This is a business uniqe identifier within the switch, not a business registration number")
	background_image = models.CharField(max_length=200)
	description = models.CharField(max_length=100)	
	status = models.ForeignKey(InstitutionStatus)
	tagline = models.CharField(max_length=140)
	logo = models.ImageField(upload_to='upc_institution_logo/', max_length=200, blank=True, null=True)
	documents = models.FileField(upload_to='upc_institution_documents/', max_length=200, blank=True, null=True)
	details = models.CharField(max_length=1200, null=True, blank=True)
	industries = models.ManyToManyField(IndustryClass,related_name='industries')
	default_color = models.CharField(max_length=100)
	website = models.CharField(max_length=200, blank=True, null=True)
	physical_address = models.CharField(max_length=200, blank=True, null=True) #HQ
	address = models.CharField(max_length=200, blank=True,null=True,help_text='Post Office Box')
	gateway = models.ManyToManyField(Gateway)
	currency = models.ManyToManyField(Currency, blank=True) #Allowed Currencies
	country = models.ForeignKey(Country)
	geometry = models.PointField(srid=4326)
	objects = models.GeoManager()
	theme = models.ForeignKey(Theme)
	primary_color = models.CharField(max_length=100, blank=True, null=True)
	secondary_color = models.CharField(max_length=100, blank=True, null=True)
	accent_color = models.CharField(max_length=100, blank=True, null=True)
	registration_number = models.CharField(max_length=200, blank=True, null=True)
	tax_pin = models.CharField(max_length=100, blank=True, null=True)
	def __unicode__(self):
		return u'%s %s' % (self.id, self.name)
	def gateway_list(self):
		return "\n".join([a.name for a in self.gateway.all()])
	def currency_list(self):
		return "\n".join([a.code for a in self.currency.all()])

class ProfileStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)
		
class Profile(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	middle_name = models.CharField(max_length=30, null=True, blank=True)
	api_key = models.CharField(max_length=200)
	timezone = models.CharField(max_length=50)
	language = models.ForeignKey(Language)
	geometry = models.PointField(srid=4326)
	objects = models.GeoManager()
	country = models.ForeignKey(Country, null=True, blank=True)
	dob = models.DateField(null=True, blank=True)
	gender = models.ForeignKey(Gender, null=True, blank=True)
	physical_address = models.CharField(max_length=200, blank=True, null=True, help_text="Physical Address/Street/Location")
	photo = models.ImageField(upload_to='upc_profile_photo/', max_length=200, blank=True, null=True)
	user = 	models.OneToOneField(User)
	national_id = models.CharField(max_length=45, blank=True, null=True)
	city = models.CharField(max_length=200, blank=True, null=True, help_text="City/Town")
	region = models.CharField(max_length=200, blank=True, null=True, help_text="Region/State/County")
	address = models.CharField(max_length=200, blank=True, null=True, help_text="Address 2/Postal Address")
	postal_code = models.CharField(max_length=200, blank=True, null=True)
	passport_number = models.CharField(max_length=45, blank=True, null=True)
	passport_expiry_date = models.DateField(blank=True, null=True)
	postal_address = models.CharField(max_length=200, blank=True, null=True)
	tax_pin = models.CharField(max_length=100, blank=True, null=True)
	def __unicode__(self):
		return '%s %s %s %s %s' % (self.user.username, self.user.first_name, self.user.last_name, self.national_id, self.user.email)

class GatewayProfile(models.Model):#Enforce one gateway profile per gateway per user
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	user = 	models.ForeignKey(User)
	gateway = models.ForeignKey(Gateway)
	pin = models.CharField(max_length=200, null=True, blank=True)
	msisdn = models.ForeignKey(MSISDN, null=True, blank=True)
	status = models.ForeignKey(ProfileStatus)
	access_level = models.ForeignKey(AccessLevel)
	role = models.ForeignKey(Role, null=True, blank=True)
	institution = models.ForeignKey(Institution, blank=True, null=True) #(enforce one profile institution only per gateway)
	pin_retries = models.SmallIntegerField(default=0, help_text="Max PIN retries=3 then locks profile")
	activation_code = models.CharField(max_length=45, blank=True, null=True)
	device_id = models.CharField(max_length=200, blank=True, null=True)
	activation_device_id = models.CharField(max_length=200, blank=True, null=True)
	email_activation_code = models.CharField(max_length=45, blank=True, null=True)
        allowed_host = models.ManyToManyField(Host, blank=True)
	def __unicode__(self):
		return u'%s %s %s %s %s %s' % (self.id, self.user.first_name, self.user.last_name, self.msisdn,self.gateway, self.access_level)
	def allowed_host_list(self):
		return "\n".join([a.host for a in self.allowed_host.all()])


class GatewayProfileDevice(models.Model):#Enforce one gateway profile per gateway per user
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	gateway_profile = models.ForeignKey(GatewayProfile)
	channel = models.ForeignKey(Channel)
	activation_code = models.CharField(max_length=45, blank=True, null=True)
	device_id = models.CharField(max_length=200, blank=True, null=True)
	activation_device_id = models.CharField(max_length=200, blank=True, null=True)
	email_activation_code = models.CharField(max_length=45, blank=True, null=True)
	def __unicode__(self):
		return u'%s %s %s %s' % (self.id, self.gateway_profile, self.channel, self.device_id)

class ChangeProfileMSISDNStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)


class ChangeProfileMSISDN(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	gateway_profile = models.OneToOneField(GatewayProfile)
	msisdn = models.ForeignKey(MSISDN)
	expiry = models.DateTimeField()
	change_pin = models.CharField(max_length=200, null=True, blank=True)
	status = models.ForeignKey(ChangeProfileMSISDNStatus)
	def __unicode__(self):
		return u'%s %s %s' % (self.gateway_profile, self.msisdn, self.expiry)

'''
class TillTypeStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

#Whether Online or Shop Till	
class TillType(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	status = models.ForeignKey(TillTypeStatus)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)
		
class InstitutionTill(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45) #Each institution to have unique names within its list, enforced on code.
	institution = models.ForeignKey(Institution)
	image = models.ImageField(upload_to='upc_institutiontill_image/', max_length=200, blank=True, null=True)
	till_type = models.ForeignKey(TillType)
	till_number = models.IntegerField()
	till_currency = models.ForeignKey(Currency)
	description = models.CharField(max_length=100)	
	qr_code = models.CharField(max_length=200, blank=True, null=True)
	city = models.CharField(max_length=200, blank=True, null=True, help_text="City/Town")
	physical_address = models.CharField(max_length=200, blank=True, null=True)
	is_default = models.BooleanField(default=False)
	geometry = models.PointField(srid=4326)
	details = models.CharField(max_length=1200, null=True, blank=True)
	objects = models.GeoManager()
	def __unicode__(self):
		return '%s %s %s' % (self.name, self.institution, self.till_currency)
'''

class PasswordStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)
		
class PasswordPolicy(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	user = models.ForeignKey(User)
	reset_key = models.CharField(max_length=200, blank=True, null=True)
	old_password = models.CharField(max_length=400)
	status = models.ForeignKey(PasswordStatus)
	def __unicode__(self):
		return u'%s' % (self.name)


class SessionStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class Session(models.Model):
        date_modified  = models.DateTimeField(auto_now=True)
        date_created = models.DateTimeField(auto_now_add=True) #order by date created
	session_id = models.CharField(max_length=500) 
	channel = models.ForeignKey(Channel) #For unique field with session id which is external
	gateway_profile = models.ForeignKey(GatewayProfile, null=True, blank=True) #Blank For unexisting/first time profiles which is external
	reference = models.CharField(max_length=100, null=True, blank=True) #For tracking sends and recording unregistered users
	num_of_tries = models.IntegerField(null=True, blank=True)
	num_of_sends = models.IntegerField(null=True, blank=True)
	status = models.ForeignKey(SessionStatus)
	def __unicode__(self):
		return u'%s %s %s' % (self.session_id, self.gateway_profile, self.reference)


from django.db import models
from django.contrib.gis.db.models import MultiPolygonField, PointField, Manager as GeoManager
from primary.core.administration.models import *
from primary.core.api.models import *

from django.utils import timezone

class InstitutionStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)

class MSISDN(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	#phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
	phone_regex = RegexValidator(regex=r'^\+\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
	phone_number = models.CharField(validators=[phone_regex], max_length=15, unique=True) # validators should be a list
	is_active = models.BooleanField(default=False, null=True)
	def __str__(self):
		return u'%s' % (self.phone_number)

class Institution(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=200)
	business_number = models.CharField(max_length=8, unique=True, help_text="This is a business uniqe identifier within the switch, not a business registration number")
	background_image = models.CharField(max_length=200)
	description = models.CharField(max_length=100)	
	status = models.ForeignKey(InstitutionStatus, on_delete=models.CASCADE)
	tagline = models.CharField(max_length=140)
	logo = models.ImageField(upload_to='upc_institution_logo/', max_length=200, blank=True, null=True)
	icon_image = models.ImageField(upload_to='upc_institution_icon_image/', max_length=200, blank=True, null=True)
	documents = models.FileField(upload_to='upc_institution_documents/', max_length=200, blank=True, null=True)
	details = models.JSONField(max_length=1920, null=True, blank=True)
	industries = models.ManyToManyField(IndustryClass,related_name='industries',blank=True)
	default_color = models.CharField(max_length=100)
	website = models.CharField(max_length=200, blank=True, null=True)
	physical_address = models.CharField(max_length=200, blank=True, null=True) #HQ
	address = models.CharField(max_length=200, blank=True,null=True,help_text='Post Office Box')
	gateway = models.ManyToManyField(Gateway)
	currency = models.ManyToManyField(Currency, blank=True) #Allowed Currencies
	country = models.ForeignKey(Country, on_delete=models.CASCADE)
	geometry = PointField(srid=4326)
	objects = GeoManager()
	design = models.ForeignKey(DesignSystem, on_delete=models.CASCADE)
	primary_color = models.CharField(max_length=100, blank=True, null=True)
	secondary_color = models.CharField(max_length=100, blank=True, null=True)
	accent_color = models.CharField(max_length=100, blank=True, null=True)
	registration_number = models.CharField(max_length=200, blank=True, null=True)
	tax_pin = models.CharField(max_length=100, blank=True, null=True)
	template = models.ForeignKey(Template, blank=True, null=True, on_delete=models.CASCADE)
	def __str__(self):
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
	def __str__(self):
		return u'%s' % (self.name)
		
class Profile(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	middle_name = models.CharField(max_length=30, null=True, blank=True)
	api_key = models.CharField(max_length=200)
	timezone = models.CharField(max_length=50)
	language = models.ForeignKey(Language, on_delete=models.CASCADE)
	geometry = PointField(srid=4326)
	objects = GeoManager()
	country = models.ForeignKey(Country, null=True, blank=True, on_delete=models.CASCADE)
	dob = models.DateField(null=True, blank=True)
	gender = models.ForeignKey(Gender, null=True, blank=True, on_delete=models.CASCADE)
	physical_address = models.CharField(max_length=200, blank=True, null=True, help_text="Physical Address/Street/Location")
	photo = models.ImageField(upload_to='upc_profile_photo/', max_length=200, blank=True, null=True)
	user = 	models.OneToOneField(User, on_delete=models.CASCADE)
	national_id = models.CharField(max_length=45, blank=True, null=True)
	city = models.CharField(max_length=200, blank=True, null=True, help_text="City/Town")
	region = models.CharField(max_length=200, blank=True, null=True, help_text="Region/State/County")
	address = models.CharField(max_length=200, blank=True, null=True, help_text="Address 2/Postal Address")
	postal_code = models.CharField(max_length=200, blank=True, null=True)
	passport_number = models.CharField(max_length=45, blank=True, null=True)
	passport_expiry_date = models.DateField(blank=True, null=True)
	postal_address = models.CharField(max_length=200, blank=True, null=True)
	tax_pin = models.CharField(max_length=100, blank=True, null=True)
	pn = models.BooleanField('Push Notification', default=False, help_text="Push Notification")
	pn_ack = models.BooleanField('Push Notification Acknowledged', default=False, help_text="Push Notification Acknowledged")
	def __str__(self):
		return '%s %s %s %s %s' % (self.user.username, self.user.first_name, self.user.last_name, self.national_id, self.user.email)  
     
    
class GatewayProfile(models.Model):#Enforce one gateway profile per gateway per user
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	user = 	models.ForeignKey(User, on_delete=models.CASCADE)
	gateway = models.ForeignKey(Gateway, on_delete=models.CASCADE)
	pin = models.CharField(max_length=200, null=True, blank=True)
	msisdn = models.ForeignKey(MSISDN, null=True, blank=True, on_delete=models.CASCADE)
	status = models.ForeignKey(ProfileStatus, on_delete=models.CASCADE)
	access_level = models.ForeignKey(AccessLevel, on_delete=models.CASCADE)
	role = models.ForeignKey(Role, null=True, blank=True, on_delete=models.CASCADE)
	institution = models.ForeignKey(Institution, blank=True, null=True, on_delete=models.CASCADE) #(enforce one profile institution only per gateway)
	pin_retries = models.SmallIntegerField(default=0, help_text="Max PIN retries=3 then locks profile")
	activation_code = models.CharField(max_length=45, blank=True, null=True)
	device_id = models.CharField(max_length=200, blank=True, null=True)
	activation_device_id = models.CharField(max_length=200, blank=True, null=True)
	email_activation_code = models.CharField(max_length=45, blank=True, null=True)
	allowed_host = models.ManyToManyField(Host, blank=True)
	def __str__(self):
		return u'%s %s %s %s %s %s' % (self.id, self.user.first_name, self.user.last_name, self.msisdn,self.gateway, self.access_level)
	def allowed_host_list(self):
		return "\n".join([a.host for a in self.allowed_host.all()])


class GatewayProfileDevice(models.Model):#Enforce one gateway profile per gateway per user
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	gateway_profile = models.ForeignKey(GatewayProfile, on_delete=models.CASCADE)
	channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
	activation_code = models.CharField(max_length=45, blank=True, null=True)
	device_id = models.CharField(max_length=200, blank=True, null=True)
	activation_device_id = models.CharField(max_length=200, blank=True, null=True)
	email_activation_code = models.CharField(max_length=45, blank=True, null=True)
	def __str__(self):
		return u'%s %s %s %s' % (self.id, self.gateway_profile, self.channel, self.device_id)

class ChangeProfileMSISDNStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)


class ChangeProfileMSISDN(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	gateway_profile = models.OneToOneField(GatewayProfile, on_delete=models.CASCADE)
	msisdn = models.ForeignKey(MSISDN, on_delete=models.CASCADE)
	expiry = models.DateTimeField()
	change_pin = models.CharField(max_length=200, null=True, blank=True)
	status = models.ForeignKey(ChangeProfileMSISDNStatus, on_delete=models.CASCADE)
	def __str__(self):
		return u'%s %s %s' % (self.gateway_profile, self.msisdn, self.expiry)

class SessionStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)

class Session(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True) #order by date created
	session_id = models.CharField(max_length=500) 
	channel = models.ForeignKey(Channel, on_delete=models.CASCADE) #For unique field with session id which is external
	gateway_profile = models.ForeignKey(GatewayProfile, null=True, blank=True, on_delete=models.CASCADE) #Blank For unexisting/first time profiles which is external
	reference = models.CharField(max_length=100, null=True, blank=True) #For tracking sends and recording unregistered users
	num_of_tries = models.IntegerField(null=True, blank=True)
	num_of_sends = models.IntegerField(null=True, blank=True)
	status = models.ForeignKey(SessionStatus, on_delete=models.CASCADE)
	last_access = models.DateTimeField(default=timezone.now)
	def __str__(self):
		return u'%s %s %s' % (self.session_id, self.gateway_profile, self.reference)


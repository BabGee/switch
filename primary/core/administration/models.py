from django.contrib.gis.db import models
from django.db.models import Manager as GeoManager
from django.contrib.auth.models import User
from datetime import date
from django.utils import timezone

from django.core.validators import RegexValidator
from django.core.paginator import Paginator
from django.db import connection, transaction, OperationalError
from django.utils.functional import cached_property

class TimeLimitedPaginator(Paginator):
   """
   Paginator that enforces a timeout on the count operation.
   If the operations times out, a fake bogus value is 
   returned instead.
   """
   @cached_property
   def count(self):
       # We set the timeout in a db transaction to prevent it from
       # affecting other transactions.
       with transaction.atomic(), connection.cursor() as cursor:
           cursor.execute('SET LOCAL statement_timeout TO 1000;')
           try:
               return super().count
           except OperationalError:
               return 9999999999


#User._meta.get_field('email')._unique = False
User._meta.get_field("username").max_length = 100
User._meta.get_field("first_name").max_length = 100


class UserPasswordHistory(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	password = models.CharField(max_length=200)
	def __str__(self):
		return u'%s %s' % (self.user, self.date_created.isoformat())


class CountryStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)

class Country(models.Model):
	name = models.CharField(max_length=50)
	area = models.IntegerField()
	pop2005 = models.IntegerField('Population 2005')
	fips = models.CharField('FIPS Code', max_length=2)
	iso2 = models.CharField('2 Digit ISO', max_length=2)
	iso3 = models.CharField('3 Digit ISO', max_length=3)
	un = models.IntegerField('United Nations Code')
	region = models.IntegerField('Region Code')
	subregion = models.IntegerField('Sub-Region Code')
	lon = models.FloatField()
	lat = models.FloatField()
	mpoly = models.MultiPolygonField()
	objects = GeoManager()
	ccode = models.CharField('3 Digit Country Code', max_length=3, blank=True, null=True)
	def __str__(self):
		return u'%s' % (self.name)

class Currency(models.Model):
	code = models.CharField(max_length=3, unique=True)
	num = models.CharField(max_length=4)
	exponent = models.CharField(max_length=3)
	currency = models.CharField(max_length=200, unique=True)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.code)

class Language(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)

class IndustrySection(models.Model):
	isic_code = models.CharField(max_length=5, unique=True)
	description = models.CharField(max_length=512)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.isic_code)

class IndustryDivision(models.Model):
	isic_code = models.CharField(max_length=5, unique=True)
	description = models.CharField(max_length=512)
	section = models.ForeignKey(IndustrySection, blank=True, null=True, on_delete=models.CASCADE)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.isic_code)

class IndustryGroup(models.Model):
	isic_code = models.CharField(max_length=5, unique=True)
	description = models.CharField(max_length=512)
	division = models.ForeignKey(IndustryDivision, blank=True, null=True, on_delete=models.CASCADE)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.isic_code)

class IndustryClass(models.Model):
	isic_code = models.CharField(max_length=5, unique=True)
	description = models.CharField(max_length=512)
	group = models.ForeignKey(IndustryGroup, blank=True, null=True, on_delete=models.CASCADE)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s%s' % (self.group.division.section.isic_code,self.isic_code)

class Industry(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)

class HostStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)

class Host(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	host = models.CharField(max_length=50) #Not GenericIPAddress as hostnames are allowed|not unique to allow diff descriptions
	status = models.ForeignKey(HostStatus, on_delete=models.CASCADE)
	description =  models.CharField(max_length=100)
	api_token = models.CharField(max_length=256, blank=True, null=True)
	def __str__(self):
		return u'%s' % (self.host)

class Structure(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class DesignSystem(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)

class Gateway(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	logo = models.ImageField(upload_to='administration_gateway_logo/', max_length=200, blank=True, null=True)
	icon_image = models.ImageField(upload_to='administration_gateway_icon_image/', max_length=200, blank=True, null=True)
	description = models.CharField(max_length=100)
	background_image = models.CharField(max_length=200)
	default_color = models.CharField(max_length=100)
	default_host = models.ManyToManyField(Host,blank=True)
	design = models.ForeignKey(DesignSystem, on_delete=models.CASCADE)
	primary_color = models.CharField(max_length=100, blank=True, null=True)
	secondary_color = models.CharField(max_length=100, blank=True, null=True)
	accent_color = models.CharField(max_length=100, blank=True, null=True)
	max_pin_retries = models.SmallIntegerField(default=3)
	session_expiry = models.IntegerField(blank=True, null=True, help_text='In Minutes')
	structure = models.ForeignKey(Structure, blank=True, null=True, on_delete=models.CASCADE)
	details = models.JSONField(max_length=1920, null=True, blank=True)
	allow_institution_details = models.BooleanField(default=False) 
	def __str__(self):
		return u'%s' % (self.name)
	def default_host_list(self):
		return "\n".join([a.host for a in self.default_host.all()])

class PasswordComplexity(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	regex = models.CharField(max_length=100)
	validation_response = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class PasswordPolicy(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	gateway = models.OneToOneField(Gateway, on_delete=models.CASCADE)
	password_complexity = models.ManyToManyField(PasswordComplexity, blank=True)
	old_password_count = models.PositiveSmallIntegerField(default=0, help_text='0 allows old password. Else denies old password to count')
	min_characters = models.PositiveSmallIntegerField(default=1)
	max_characters = models.PositiveSmallIntegerField(default=16)
	expiration_days = models.PositiveSmallIntegerField(default=900)
	def __str__(self):
		return u'%s' % (self.gateway)
	def password_complexity_list(self):
		return "\n".join([p.name for p in self.password_complexity.all()])

class Template(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	gateway = models.ForeignKey(Gateway, on_delete=models.CASCADE)
	def __str__(self):
		return u'%s' % (self.name)

class AccessLevelStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)

class AccessLevel(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	status = models.ForeignKey(AccessLevelStatus, on_delete=models.CASCADE)
	description = models.CharField(max_length=100)
	hierarchy = models.IntegerField()
	def __str__(self):
		return u'%s' % (self.name)  
       
class Role(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45)
	status = models.ForeignKey(AccessLevelStatus, on_delete=models.CASCADE)
	description = models.CharField(max_length=100)
	access_level = models.ForeignKey(AccessLevel, on_delete=models.CASCADE)
	gateway = models.ForeignKey(Gateway, on_delete=models.CASCADE)
	session_expiry = models.IntegerField(blank=True, null=True, help_text='In Minutes')
	def __str__(self):
		return u'%s %s' % (self.name, self.gateway)
       
class Channel(models.Model):
	name = models.CharField(max_length=50, unique=True)	
	description = models.CharField(max_length=200)	
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)	
	def __str__(self):
		return u'%s' % (self.name)        

class Gender(models.Model):
	code = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.code)

class Uploading(models.Model):
	name = models.CharField(max_length=45)
	processing_path = models.CharField(max_length=45) 
	file_format = models.CharField(max_length=450) 
	access_level = models.ForeignKey(AccessLevel, on_delete=models.CASCADE)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.name)  

class AuditTrails(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	action = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s %s' % (self.action, self.user)   

#This gives a response status on whether a transactions was succesful failed aborted rejected etc
class ResponseStatus(models.Model):
	response = models.CharField(max_length=10, unique=True)
	description = models.CharField(max_length=100)
	action = models.CharField(max_length=10)
	action_description = models.CharField(max_length=50)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s' % (self.description)

class MNO(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	country = models.ForeignKey(Country, on_delete=models.CASCADE)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s %s' % (self.name, self.country.ccode)

class MNOPrefix(models.Model):
	mno = models.ForeignKey(MNO, on_delete=models.CASCADE)
	prefix_regex = RegexValidator(regex=r'^\+\d{4,6}$', message="Prefix must be entered in the format: '+99999'. Up to 7 (Max 3 for country code)(3 digits for area code) digits allowed.")
	prefix = models.CharField(validators=[prefix_regex], max_length=8, unique=True) # validators should be a list
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return u'%s %s' % (self.mno, self.prefix)

class Forex(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	base_currency = models.ForeignKey(Currency, related_name='from_currency', on_delete=models.CASCADE)
	quote_currency = models.ForeignKey(Currency, related_name='to_currency', on_delete=models.CASCADE)
	exchange_rate = models.DecimalField(max_digits=19, decimal_places=2)
	trading_date = models.DateField(default=date.today)
	description = models.CharField(max_length=200, null=True, blank=True)
	def __str__(self):
		return u'%s %s %s %s' % (self.base_currency.code, self.quote_currency.code, self.exchange_rate, self.trading_date)

class IconGroup(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __str__(self):
		return u'%s' % (self.name)

class Icon(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)	
	icon = models.CharField(max_length=50, unique=True)	
	description = models.CharField(max_length=200,null=True,blank=True)
	group = models.ForeignKey(IconGroup, blank=True, null=True, on_delete=models.CASCADE)
	def __str__(self):
		return u'%s' % (self.icon)

class TradingBox(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=200,null=True,blank=True)
	open_time = models.TimeField()
	close_time = models.TimeField()
	def __str__(self):
		return u'%s' % (self.name)


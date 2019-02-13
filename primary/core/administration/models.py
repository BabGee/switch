from django.contrib.gis.db import models
from django.contrib.auth.models import User
from datetime import date
from django.utils import timezone

#User._meta.get_field('email')._unique = False
User._meta.get_field("username").max_length = 100
User._meta.get_field("first_name").max_length = 100

class UserPasswordHistory(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	user = models.ForeignKey(User)
	password = models.CharField(max_length=200)
	def __unicode__(self):
		return u'%s %s' % (self.user, self.date_created.isoformat())


class CountryStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
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
	objects = models.GeoManager()
	ccode = models.CharField('3 Digit Country Code', max_length=3, blank=True, null=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class Currency(models.Model):
	code = models.CharField(max_length=3, unique=True)
	num = models.CharField(max_length=4)
	exponent = models.CharField(max_length=3)
	currency = models.CharField(max_length=200, unique=True)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.code)

class Language(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class IndustrySection(models.Model):
	isic_code = models.CharField(max_length=5, unique=True)
	description = models.CharField(max_length=512)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.isic_code)

class IndustryDivision(models.Model):
	isic_code = models.CharField(max_length=5, unique=True)
	description = models.CharField(max_length=512)
	section = models.ForeignKey(IndustrySection, blank=True, null=True)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.isic_code)

class IndustryGroup(models.Model):
	isic_code = models.CharField(max_length=5, unique=True)
	description = models.CharField(max_length=512)
	division = models.ForeignKey(IndustryDivision, blank=True, null=True)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.isic_code)

class IndustryClass(models.Model):
	isic_code = models.CharField(max_length=5, unique=True)
	description = models.CharField(max_length=512)
	group = models.ForeignKey(IndustryGroup, blank=True, null=True)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s%s' % (self.group.division.section.isic_code,self.isic_code)

class Industry(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class HostStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class Host(models.Model):
	host = models.CharField(max_length=50) #Not GenericIPAddress as hostnames are allowed|not unique to allow diff descriptions
	status = models.ForeignKey(HostStatus)
	description =  models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.host)

class Structure(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class Theme(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
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
        default_host = models.ManyToManyField(Host, blank=True)
	theme = models.ForeignKey(Theme)
	primary_color = models.CharField(max_length=100, blank=True, null=True)
	secondary_color = models.CharField(max_length=100, blank=True, null=True)
	accent_color = models.CharField(max_length=100, blank=True, null=True)
	max_pin_retries = models.SmallIntegerField(default=3)
	session_expiry = models.IntegerField(blank=True, null=True, help_text='In Minutes')
	structure = models.ForeignKey(Structure, blank=True, null=True)
	def __unicode__(self):
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
	def __unicode__(self):
		return u'%s' % (self.name)
	
	
class PasswordPolicy(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	gateway = models.OneToOneField(Gateway)
	password_complexity = models.ManyToManyField(PasswordComplexity, blank=True)
	old_password_count = models.PositiveSmallIntegerField(default=0, help_text='0 allows old password. Else denies old password to count')
	def __unicode__(self):
		return u'%s' % (self.name)
	def password_complexity_list(self):
		return "\n".join([p.name for p in self.password_complexity.all()])


class Template(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	gateway = models.ForeignKey(Gateway)
	def __unicode__(self):
		return u'%s' % (self.name)

class AccessLevelStatus(models.Model):
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)

class AccessLevel(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	status = models.ForeignKey(AccessLevelStatus)
	description = models.CharField(max_length=100)
	hierarchy = models.IntegerField()
	def __unicode__(self):
		return u'%s' % (self.name)  
       
class Role(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45)
	status = models.ForeignKey(AccessLevelStatus)
	description = models.CharField(max_length=100)
	access_level = models.ForeignKey(AccessLevel)
	gateway = models.ForeignKey(Gateway)
	session_expiry = models.IntegerField(blank=True, null=True, help_text='In Minutes')
	def __unicode__(self):
		return u'%s %s' % (self.name, self.gateway)
       
class Channel(models.Model):
	name = models.CharField(max_length=50, unique=True)	
	description = models.CharField(max_length=200)	
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)	
 	def __unicode__(self):
		return u'%s' % (self.name)        

class Gender(models.Model):
	code = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.code)

class Uploading(models.Model):
	name = models.CharField(max_length=45)
	processing_path = models.CharField(max_length=45) 
	file_format = models.CharField(max_length=450) 
	access_level = models.ForeignKey(AccessLevel)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.name)  

class AuditTrails(models.Model):
	user = models.ForeignKey(User)
	action = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s %s' % (self.action, self.user)   

#This gives a response status on whether a transactions was succesful failed aborted rejected etc
class ResponseStatus(models.Model):
	response = models.CharField(max_length=10, unique=True)
	description = models.CharField(max_length=100)
	action = models.CharField(max_length=10)
	action_description = models.CharField(max_length=50)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s' % (self.description)

class MNO(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	country = models.ForeignKey(Country)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s %s' % (self.name, self.country.ccode)

class MNOPrefix(models.Model):
	mno = models.ForeignKey(MNO)
	prefix = models.CharField(max_length=8)
	description = models.CharField(max_length=100)
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	def __unicode__(self):
		return u'%s %s' % (self.mno, self.prefix)

class Forex(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	base_currency = models.ForeignKey(Currency, related_name='from_currency')
	quote_currency = models.ForeignKey(Currency, related_name='to_currency')
	exchange_rate = models.DecimalField(max_digits=19, decimal_places=2)
	trading_date = models.DateField(default=date.today)
	description = models.CharField(max_length=200, null=True, blank=True)
	def __unicode__(self):
		return u'%s %s %s %s' % (self.base_currency.code, self.quote_currency.code, self.exchange_rate, self.trading_date)

class IconGroup(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class Icon(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)	
	icon = models.CharField(max_length=50, unique=True)	
	description = models.CharField(max_length=200,null=True,blank=True)
	group = models.ForeignKey(IconGroup, blank=True, null=True)
 	def __unicode__(self):
		return u'%s' % (self.icon)



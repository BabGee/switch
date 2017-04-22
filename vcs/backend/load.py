# -*- uncoding:utf-8 -*-
import os
from models import CountryCode
from administration.models import Country

item = os.path.abspath('/tmp/vcs_countrycode.csv')

def run(verbose=True):
	#lm = LayerMapping(Country, world_shp, world_mapping,
	#                      transform=False, encoding='iso-8859-1')

	#lm.save(strict=False, verbose=verbose)
	for l in open(item, 'r'):
		try:	
			line = l.split(',')
			name = u'%s' % line[0]
			code = line[1].replace('\n','')
			print name
			country = ''		
			country = Country.objects.filter(name__icontains=name.encode('utf-8'))
		
			if len(country)>0:
				print 'Country %s' % country
				country_code = CountryCode(country=country[0],code=code, description=country[0].name)
				country_code.save()
			if len(country)>1:
				print '\n\n#####\n\tMultiple Match\n\n'
		except Exception, e:
			print '\n\n#####\n\tError: %s\n\n' % e

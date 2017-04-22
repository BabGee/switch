from models import Country
import csv

def run():
	with open('/srv/applications/switch/administration/country_code.csv', 'rb') as f:
	    reader = csv.reader(f)
	    your_list = map(tuple, reader)

	for c in your_list:
		if len(c)==2:
			print "Country", c[0], " Code", c[1]
			countries = Country.objects.filter(name__icontains=c[0])
			if len(countries)>0:
				print countries[0].name
				countries[0].ccode = c[1]
				countries[0].save()
			else:
				print "No Country Found"


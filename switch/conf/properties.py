import ConfigParser

cf = ConfigParser.ConfigParser()
print cf
cf.read("switch.properties")

#print cf._sections


conf_products = cf.get('INSTALLED_APPS','products')
products=conf_products.split(",")

conf_thirdparty = cf.get('INSTALLED_APPS','thirdparty')
thirdparty=conf_thirdparty.split(",")


dbengine = cf.get('DATABASES','default_dbengine')
dbname = cf.get('DATABASES','default_dbname')
dbuser = cf.get('DATABASES','default_dbuser')
dbhost = cf.get('DATABASES','default_dbhost')
dbport = cf.get('DATABASES','default_dbport')

conf_hosts = cf.get('ALLOWED_HOSTS','hosts')
hosts = conf_hosts.split(",")

installed_apps = products+thirdparty

print installed_apps

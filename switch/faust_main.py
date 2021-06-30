import os, sys

print(__name__)
path = os.path.abspath(os.path.join(__file__, '..', '..'))
if path not in sys.path:
    sys.path.append(path)
print(path)

from django.conf import settings
from django.utils.module_loading import import_module

#Discover agents modules only
module_name = 'agents'

#app.discover('secondary.channels.notify')
def autodiscover(django_apps):
	for django_app in django_apps:
		# Attempt to import the app's ``module_name``.
		try:
			import_module('{0}.{1}'.format(django_app, module_name))
			print('found: %s' % django_app)
		except Exception as e:
			print('%s: :%s' % (e,django_app))
			pass

autodiscover(settings.INSTALLED_APPS)

from switch.faust_app import app

#def main():
#    app.main()
#
#if __name__ == '__main__':
#    main()
app.main()

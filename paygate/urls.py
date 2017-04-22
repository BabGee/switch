from django.conf.urls import patterns, include, url
from paygate.views import *

urlpatterns = patterns('',
     #url(r'^ussd_menu/',  USSD().ussd_menu),
	url(r'^RPC2', mpesaxmlrpc().mpesaxmlrpc),
     	url(r'^mpesac2b/',  mpesa().mpesac2b),

)




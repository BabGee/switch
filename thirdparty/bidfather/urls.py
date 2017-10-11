from django.conf.urls import url, include
from django.contrib.auth import views as auth_views
#import notifications.urls
#from forms import LoginForm
from  views import *

urlpatterns = [
    url(r'^$', HomeView.as_view(), name='index'),
    url(r'^login/$', LoginView.as_view(),  name='login'),
    url(r'^logout/$', LogoutView.as_view(),name='logout'),
]

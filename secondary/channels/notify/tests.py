#from django.test import TestCase

# Create your tests here.

from django.test import TestCase
from django.utils import timezone

from .models import *


class InboundTests(TestCase):

	def test_inserts_to_inbound(self):
		"""
		"""
		#time = timezone.now() + datetime.timedelta(days=30)
		#future_question = Question(pub_date=time)
		#self.assertIs(future_question.was_published_recently(), False)
		contact = Contact.objects.filter(gateway_profile__id=2247, product__name='TEST NOTIFICATION').first()
		#Append by adding
		_recipient = ['254717103598']*3
		obj_list = [Outbound(contact=contact, message='Test', scheduled_send=timezone.now(),state=OutBoundState.objects.get(name='CREATED'), recipient=r, sends=0) for r in _recipient]
		if obj_list:
			outbound_log = Outbound.objects.bulk_create(obj_list)


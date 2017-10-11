from notify.models import *
from django.utils import timezone

contact = Contact.objects.get(id=623310)
print contact
#<Contact: 10   +254717103598 MAMTAG ADMINISTRATOR 73 TEST Bulk SMS Account 0.00 TEST Bulk SMS Account TEST>
state=OutBoundState.objects.get(name='CREATED')
#Outbound(contact=contact,message='Test',scheduled_send=timezone.now(),state=state,sends=0).save()
def outbound(size):
    outbound_list = []
    for x in range(0, size):
        outbound_list.append(Outbound(contact=contact,message='Test',scheduled_send=timezone.now(),state=state,sends=0))
    Outbound.objects.bulk_create(outbound_list)

outbound(9900)

#To Clear Queue
#Outbound.objects.filter(contact=contact).update(state=OutBoundState.objects.get(name='SENT'))
#Outbound.objects.filter(contact=contact,state__name='SENT').update(state=OutBoundState.objects.get(name='CREATED'),sends=0)
#Outbound.objects.filter(contact=contact).delete()

                                                

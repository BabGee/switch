from __future__ import unicode_literals

import logging
import pytz
from django.utils import timezone
import json
from administration.models import *
from crm.models import *

lgr = logging.getLogger('bidfather')


class BidStatus(models.Model):
    date_modified = models.DateTimeField(auto_now=True)
    date_created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=45, unique=True)
    description = models.CharField(max_length=3840)

    def __unicode__(self):
        return u'{0:s}'.format(self.name)


class Bid(models.Model):
    date_modified = models.DateTimeField(auto_now=True)
    date_created = models.DateTimeField(auto_now_add=True)
    institution = models.ForeignKey(Institution)
    name = models.CharField(max_length=45)
    description = models.CharField(max_length=3840)
    image = models.ImageField(upload_to='bidfather__bid__image/', max_length=200, blank=True, null=True)
    attachment = models.FileField(upload_to='bidfather__bid__attachment/', max_length=200, null=True, blank=True)
    bid_min_points = models.IntegerField(blank=True, null=True)
    bid_max_points = models.IntegerField(blank=True, null=True)
    bid_open = models.DateTimeField()
    bid_close = models.DateTimeField()
    invoiced = models.BooleanField(default=False)
    show_leading = models.BooleanField(default=False)
    industry_section = models.ForeignKey(IndustrySection)

    def requirements(self, gateway_profile):
        profile_tz = pytz.timezone(gateway_profile.user.profile.timezone)
        bid_requirement_list = BidRequirement.objects.filter(bid__id=self.id)

        rows = []
        '''
        # query filters
        if "q" in payload.keys() and payload['q'] not in ["", None]:
            bid_requirement_list = bid_requirement_list.filter(name__icontains=payload['q'].strip())

        # filter last_id
        if 'max_id' in payload.keys() and payload['max_id'] > 0:
            bid_requirement_list = bid_requirement_list.filter(id__lt=payload['max_id'])
        if 'min_id' in payload.keys() and payload['min_id'] > 0:
            bid_requirement_list = bid_requirement_list.filter(id__gt=payload['min_id'])


        # get last_id
        trans = bid_requirement_list.aggregate(max_id=Max('id'), min_id=Min('id'))
        max_id = trans.get('max_id')
        min_id = trans.get('min_id')
        '''

        bid_requirement_list = bid_requirement_list.order_by('-date_created')[:50]

        for i in bid_requirement_list:
            itype = i.bid.name
            name = '%s' % i.name
            desc = '%s | %s' % (i.bid.institution, i.bid.description)

            item = {"index": i.id,
                    "name": name,
                    "type": itype,
                    "count": i.quantity,
                    "description": desc,
                    "image": i.image.name,

                    "date_time": profile_tz.normalize(i.date_modified.astimezone(profile_tz)).strftime(
                        "%d %b %Y %I:%M:%S %p %Z %z")}

            try:
                current_application = BidRequirementApplication.objects.get(
                    bid_application__institution=gateway_profile.institution,
                    bid_requirement=i
                )
                item['amount'] = current_application.unit_price

                edit_apply = {
                    "Edit Unit Price": {
                        "params": {"bid_requirement_id": str(i.id)},
                        "service": "VIEW REQUIREMENT APPLICATION"
                    }

                }

            except BidRequirementApplication.DoesNotExist:
                item['amount'] = 'Not set'
                edit_apply = {
                    "Set Initial Unit Price": {
                        "params": {"bid_requirement_id": str(i.id)},
                        "service": "REQUIREMENT APPLICATION"
                    }

                }
            item["href"] = edit_apply

            rows.append(item)

        return rows

    def application_complete_from(self, institution):
        docs = BidDocument.objects.filter(bid=self).count()
        doc_apps = BidDocumentApplication.objects.filter(
            bid_application=BidApplication.objects.get(institution=institution,bid=self)
        ).count()
        return docs == doc_apps

    def application_started_by(self, institution):
        return BidApplication.objects.filter(bid=self, institution=institution).count()

    def open(self):
        return self.bid_open <= timezone.now() and self.bid_close >= timezone.now()

    def closed(self):

        return self.bid_open <= timezone.now() and self.bid_close <= timezone.now()

    def upcoming(self):

        return self.bid_open >= timezone.now() and self.bid_close >= timezone.now()

    def get_dsc_item(self, gateway_profile):
        profile_tz = pytz.timezone(gateway_profile.user.profile.timezone)

        itype = self.industry_section.description
        name = '%s' % self.name
        desc = '%s | %s' % (self.institution.name, self.description)

        return {
            "index": self.id,
            "name": name,
            "type": itype,
            "description": desc,
            "image": self.image.name,
            "attachment": self.attachment.url if self.attachment else '',
            "href": self.get_links(gateway_profile.institution),
            "bid_open": profile_tz.normalize(self.bid_open.astimezone(profile_tz)).strftime(
                "%d %b %Y %I:%M:%S %p"),
            "closing": profile_tz.normalize(self.bid_close.astimezone(profile_tz)).strftime(
                "%d %b %Y %I:%M:%S %p")
        }

    def get_links(self, institution):

        links = {}

        # for open bids /apply/ /view/
        if self.open():
            if self.application_started_by(institution):
                links['Finish Application'] = {
                    "url": "/bid_application/?bid_id=" + str(self.id),
                    "params": {"bid_id": str(self.id)},
                    "service": "BID APPLICATION"
                }

            else:
                links['Start Application'] = {
                    "url": "/bid_application/?bid_id=" + str(self.id),
                    "params": {"bid_id": str(self.id)},
                    "service": "BID APPLICATION"
                }

            links['View'] = {
                "url": "/view_open_bid/?bid_id=" + str(self.id),
                "params": {"bid_id": str(self.id)},
                "service": "OPEN BID DETAILS"
            }

        if self.upcoming():
            pass

        if self.closed():
            pass
            '''
            links['View'] = {
                "url": "/view_closed_bid/?bid_id=" + str(self.id),
                "params": {"bid_id": str(self.id)},
                "service": "CLOSED BID DETAILS"
            }
            '''

        return links

    def rankings_order(self):
        query = 'WITH start_tie as (select case when current_total_price = lead(current_total_price) over (order by current_total_price asc) ' \
                'THEN 1 else 0 end as tie_offset from bidfather_bidapplication WHERE bid_id = %s AND current_total_price IS NOT NULL ' \
                'ORDER BY current_total_price ASC  LIMIT 1)' \
                ' SELECT *, dense_rank() over (order by current_total_price asc) + (select tie_offset from start_tie) ' \
                'cost_rank from bidfather_bidapplication where bid_id = %s AND current_total_price IS NOT NULL '

        bid_application_list = BidApplication.objects.raw(query, [self.id, self.id])

        return bid_application_list

    def app_rankings(self, institution, gateway_profile):
        lgr.info('Institution rankings: ' + str(institution))
        # profile_tz = pytz.timezone('Africa/Nairobi')
        rows = []
        bid_application_list = self.rankings_order()

        if self.institution == institution:
            for i in bid_application_list:
                itype = i.current_total_price
                name = '%s' % i.institution.name

                item = {
                    "index": i.id,
                    "position": i.cost_rank if self.open() else "Not Ranked Yet",
                    "name": name,
                    "type": itype ,
                }

                rows.append([item])

        else:

            for i in bid_application_list:
                if i.institution == institution:
                    itype = i.current_total_price
                    name = '%s' % i.institution.name

                    item = {
                        "index": i.id,
                        "position": i.cost_rank if self.open() else "Not Ranked",
                        "name": name,
                        "type": itype,
                        "requirements": self.requirements(gateway_profile)
                    }

                    rows.append([item])
                    break

            if len(rows):
                pass
            else:
                itype = "Not Set"
                name = institution.name

                item = {
                    "index": 1,
                    "position": "Not Ranked",
                    "name": name,
                    "type": itype,
                    "requirements": self.requirements(gateway_profile)
                }

                rows.append([item])


        return rows

    def __unicode__(self):
        return u'%s %s' % (self.name, self.institution)


class BidRequirement(models.Model):
    date_modified = models.DateTimeField(auto_now=True)
    date_created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=45)
    description = models.CharField(max_length=1200)
    bid = models.ForeignKey(Bid)
    image = models.ImageField(upload_to='bidfather__bid__image/', max_length=200, blank=True, null=True)
    attachment = models.FileField(upload_to='bidfather__bid__attachment/', max_length=200, null=True, blank=True)
    requirement_min_points = models.IntegerField(blank=True, null=True)
    requirement_max_points = models.IntegerField(blank=True, null=True)

    quantity = models.IntegerField(default=1)

    def __unicode__(self):
        return u'%s %s' % (self.name, self.bid)


class BidApplicationStatus(models.Model):
    name = models.CharField(max_length=45, unique=True)
    description = models.CharField(max_length=100)
    date_modified = models.DateTimeField(auto_now=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return u'%s' % self.name


class BidApplication(models.Model):
    date_modified = models.DateTimeField(auto_now=True)
    date_created = models.DateTimeField(auto_now_add=True)
    institution = models.ForeignKey(Institution)
    bid = models.ForeignKey(Bid)
    # description = models.CharField(max_length=1200)
    # attachment = models.FileField(upload_to='bidfather__bid__attachment/', max_length=200, null=True, blank=True)
    # quantity = models.DecimalField(max_digits=19, decimal_places=2)
    current_total_price = models.DecimalField(max_digits=19, decimal_places=2, null=True)
    # bid_rank = models.IntegerField(blank=True, null=True)
    completed = models.BooleanField(default=False)
    status = models.ForeignKey(BidApplicationStatus)

    def __unicode__(self):
        return u'%s %s' % (self.institution, self.bid)


class BidRequirementApplication(models.Model):
    date_modified = models.DateTimeField(auto_now=True)
    date_created = models.DateTimeField(auto_now_add=True)
    bid_application = models.ForeignKey(BidApplication)
    bid_requirement = models.ForeignKey(BidRequirement)
    description = models.CharField(max_length=1200)
    attachment = models.FileField(upload_to='bidfather__bid__attachment/', max_length=200, null=True, blank=True)

    unit_price = models.DecimalField(max_digits=19, decimal_places=2)

    def __unicode__(self):
        return u'%s %s' % (self.bid_application, self.bid_requirement)


class BidApplicationChangeType(models.Model):
    name = models.CharField(max_length=50)
    access_level = models.ManyToManyField(AccessLevel)

    date_modified = models.DateTimeField(auto_now=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return u'%s' % self.name


class BidAmountActivity(models.Model):
    date_modified = models.DateTimeField(auto_now=True)
    date_created = models.DateTimeField(auto_now_add=True)
    application = models.ForeignKey(BidApplication)
    price = models.DecimalField(max_digits=19, decimal_places=2)

    def __unicode__(self):
        return u'%s %s' % (self.application.bid.institution, self.price)


class BidApplicationChange(models.Model):
    date_modified = models.DateTimeField(auto_now=True)
    date_created = models.DateTimeField(auto_now_add=True)
    type = models.ForeignKey(BidApplicationChangeType)
    application = models.ForeignKey(BidApplication)
    processed = models.BooleanField(default=False)

    def __unicode__(self):
        return u'Change %s' % self.type.name


class BidInvoiceType(models.Model):
    date_modified = models.DateTimeField(auto_now=True)
    date_created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=45, unique=True)
    description = models.CharField(max_length=200)
    invoicing_rate = models.DecimalField(max_digits=19, decimal_places=2)
    product_item = models.OneToOneField(ProductItem)

    def __unicode__(self):
        return u'%s %s %s' % (self.name, self.invoicing_rate, self.product_item.currency)


class BidInvoice(models.Model):
    date_modified = models.DateTimeField(auto_now=True)
    date_created = models.DateTimeField(auto_now_add=True)
    bid_invoice_type = models.ForeignKey(BidInvoiceType)
    bid = models.ForeignKey(Bid)
    max_price = models.DecimalField(max_digits=19, decimal_places=2)
    min_price = models.DecimalField(max_digits=19, decimal_places=2)
    amount = models.DecimalField(max_digits=19, decimal_places=2)
    processed = models.BooleanField(default=False)

    def __unicode__(self):
        return u'%s %s %s' % (self.bid_invoice_type, self.bid, self.amount)


class BidDocument(models.Model):
    date_modified = models.DateTimeField(auto_now=True)
    date_created = models.DateTimeField(auto_now_add=True)
    bid = models.ForeignKey(Bid)
    name = models.CharField(max_length=45)

    def __unicode__(self):
        return u'{0:s}'.format(self.name)


class BidDocumentApplication(models.Model):
    date_modified = models.DateTimeField(auto_now=True)
    date_created = models.DateTimeField(auto_now_add=True)
    bid_application = models.ForeignKey(BidApplication)
    bid_document = models.ForeignKey(BidDocument)
    attachment = models.FileField(
        upload_to='bidfather__bid_document/',
        max_length=200
    )

    def __unicode__(self):
        return u'{0:s}'.format(self.bid_application.institution)

class BidNotificationTypeStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class BidNotificationType(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	status = models.ForeignKey(BidNotificationTypeStatus)
	notification_details = models.CharField(max_length=1920) #JSON Payload, to be complemented by Notification Template
	service = models.ForeignKey(Service)
	product_item = models.ForeignKey(ProductItem, null=True, blank=True) #Captures the institution
	def __unicode__(self):
		return u'%s' % (self.name)

class BidNotificationStatus(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=45, unique=True)
	description = models.CharField(max_length=100)
	def __unicode__(self):
		return u'%s' % (self.name)

class BidNotification(models.Model):
	date_modified  = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	bid = models.ForeignKey(Bid)
	status = models.ForeignKey(BidNotificationStatus)
	notification_details = models.CharField(max_length=1920, default=json.dumps({}))
	def __unicode__(self):
		return u'%s' % (self.bid)




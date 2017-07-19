from __future__ import absolute_import

from celery import shared_task
from celery import task
#from celery.contrib.methods import task_method
from celery.utils.log import get_task_logger
from django.contrib.auth.models import User
from django.shortcuts import render
from switch.celery import app
from switch.celery import single_instance_task
from django.db import transaction

# from upc.backend.wrappers import *
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
import time, os, random, string, json
from django.core.validators import validate_email
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.contrib.auth import authenticate
from django.db import IntegrityError
from django.contrib.gis.geos import Point
from django.conf import settings
from django.core.files import File
import base64, re
from decimal import Decimal, ROUND_UP, ROUND_DOWN
from django.db.models import Max, Min, Count, Sum
from thirdparty.bidfather.models import *
import pytz, time, json, pycurl

from django.core.serializers.json import DjangoJSONEncoder
import paho.mqtt.client as mqtt
from django.db.models import Sum, F

import logging

lgr = logging.getLogger('bidfather')


class Wrappers:
    pass


def publish_notifications(bid, gateway_profile):
    client = mqtt.Client()
    client.username_pw_set("Super@User", "apps")
    client.connect("127.0.0.1", 1883, 60)

    #   get new rankings
    rankings = bid.app_rankings(bid.institution, gateway_profile)
    bid_change = {"type": "ranking", "data": rankings}
    #   send the new rankings to each bid application creator
    client.publish('rankings_for_owner/' + str(bid.pk), json.dumps(bid_change, cls=DjangoJSONEncoder))

    for bid_app in bid.bidapplication_set.all():
        rankings = bid.app_rankings(bid_app.institution, gateway_profile)
        bid_change = {"type": "ranking", "data": rankings}
        client.publish('rankings_for_bidder/' + str(bid_app.institution.pk) + '/' + str(bid.pk),
                       json.dumps(bid_change, cls=DjangoJSONEncoder))

    client.disconnect()


class System(Wrappers):
    def get_open_bid_details(self, payload, node_info):
        try:

            bid = Bid.objects.get(id=payload['bid_id'])
            payload['bid_name'] = bid.name
            payload['bid_description'] = bid.description
            payload['bid_image'] = bid.image.url if bid.image else ''
            payload['bid_closing'] = bid.bid_open.isoformat()

            payload['response'] = 'Bid Details Updated'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error on Getting Bid Details: %s" % e)

        return payload

    def get_selected_bid_details(self, payload, node_info):
        try:
            gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
            profile_tz = pytz.timezone(gateway_profile.user.profile.timezone)

            if 'institution_id' in payload.keys():
                institution = Institution.objects.get(id=payload['institution_id'])
            elif gateway_profile.institution not in ['', None]:
                institution = gateway_profile.institution

            bid = Bid.objects.get(id=payload['bid_id'])

            if bid.open():
                payload['trigger'] = 'opened%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
            else:
                payload['trigger'] = 'closed%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')

            bid_app = BidApplication.objects.get(bid=bid, institution=institution)
            if bid_app.current_total_price:
                payload['trigger'] = 'unit_prices_set%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
            else:
                payload['trigger'] = 'unit_prices_not_set%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')

            payload['institution_id'] = str(institution.id)
            payload['institution'] = institution.name
            payload['owner_institution'] = bid.institution.name
            payload['start_time'] = profile_tz.normalize(bid.bid_open.astimezone(profile_tz)).strftime(
                "%d %b %Y %I:%M:%S %p")
            payload['end_time'] = profile_tz.normalize(bid.bid_close.astimezone(profile_tz)).strftime(
                "%d %b %Y %I:%M:%S %p")

            payload['bid_name'] = bid.name
            payload['bid_description'] = bid.description
            payload['bid_closing'] = bid.bid_close.isoformat()

            payload['bid_image'] = bid.image.url if bid.image else ''

            payload['response'] = 'Bid Details Updated'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error on Getting Bid Details: %s" % e)

        return payload

    def get_live_selected_bid_details(self, payload, node_info):
        try:
            gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

            if 'institution_id' in payload.keys():
                institution = Institution.objects.get(id=payload['institution_id'])
            elif gateway_profile.institution not in ['', None]:
                institution = gateway_profile.institution

            bid = Bid.objects.get(id=payload['bid_id'])

            if bid.open():
                payload['trigger'] = 'opened%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
            else:
                payload['trigger'] = 'closed%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')

            payload['institution_id'] = str(institution.id)
            payload['bid_name'] = bid.name
            payload['bid_description'] = bid.description
            payload['bid_closing'] = bid.bid_close.isoformat()
            payload['bid_image'] = bid.image.url if bid.image else ''
            payload['bid_app_id'] = bid.bidapplication_set.get(institution=institution).pk

            payload['response'] = 'Bid Details Updated'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error on Getting Bid Details: %s" % e)

        return payload

    def view_bid_application(self, payload, node_info):
        try:
            lgr.info("View Bid Application")
            gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

            # if 'institution_id' in payload.keys():
            #    institution = Institution.objects.get(id=payload['institution_id'])
            # elif gateway_profile.institution not in ['', None]:

            institution = gateway_profile.institution

            bid = Bid.objects.get(id=payload['bid_id'])
            bid_application = bid.bidapplication_set.get(institution=institution)

            total_price = BidRequirementApplication.objects.filter(
                bid_requirement__bid=bid,
                bid_application=bid_application
            ).annotate(
                total=Sum(F('bid_requirement__quantity') * F('unit_price'), output_field=models.DecimalField())
            ).aggregate(Sum('total'))

            # bid_application = BidApplication.objects.get(id=payload['bid_app_id'],institution=institution)

            # payload['bid_app_id'] = bid_application.pk
            payload['bid_app_price'] = str(total_price.get('total__sum'))

            payload['response'] = 'Got Bid Application Details'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error on Getting Bid Application Details: %s" % e)

        return payload

    def deny_bid_application(self, payload, node_info):
        try:
            lgr.info("Deny Bid Application")
            gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

            # if 'institution_id' in payload.keys():
            #    institution = Institution.objects.get(id=payload['institution_id'])
            # elif gateway_profile.institution not in ['', None]:

            institution = gateway_profile.institution
            bid_application = BidApplication.objects.get(id=payload['bid_app_id'])
            if bid_application.bid.institution.pk == institution.pk:
                new_status = BidApplicationStatus.objects.get(name="Denied")
                bid_application.status = new_status
                bid_application.save()
                payload['bid_app_status'] = new_status.name

            payload['response'] = 'Bid Application Denied'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error Denying Bid Application: %s" % e)

        return payload

    def approve_bid_application(self, payload, node_info):
        try:
            lgr.info("Deny Bid Application")
            gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

            # if 'institution_id' in payload.keys():
            #    institution = Institution.objects.get(id=payload['institution_id'])
            # elif gateway_profile.institution not in ['', None]:

            institution = gateway_profile.institution
            bid_application = BidApplication.objects.get(id=payload['bid_app_id'])
            if bid_application.bid.institution.pk == institution.pk:
                new_status = BidApplicationStatus.objects.get(name="Approved")
                bid_application.status = new_status
                bid_application.save()
                payload['bid_app_status'] = new_status.name

            payload['response'] = 'Bid Application Denied'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error Denying Bid Application: %s" % e)

        return payload

    def view_bid_requirement(self, payload, node_info):
        try:
            lgr.info("View Bid Requirement")
            gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

            # if 'institution_id' in payload.keys():
            #    institution = Institution.objects.get(id=payload['institution_id'])
            # elif gateway_profile.institution not in ['', None]:

            institution = gateway_profile.institution

            try:
                bid_requirement = BidRequirementApplication.objects.get(
                    bid_requirement_id=payload['bid_requirement_id'],
                    bid_application__institution=institution
                )

                payload['bid_requirement_price'] = str(bid_requirement.unit_price)
            except ObjectDoesNotExist:
                payload['bid_requirement_price'] = 'Not Set'

            # bid_application = bid.bidapplication_set.get(institution=institution)
            # bid_application = BidApplication.objects.get(id=payload['bid_app_id'],institution=institution)

            # payload['bid_requirement_id'] = bid_application.pk

            payload['response'] = 'Got Bid Requirement Details'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error Getting Bid Requirement Details: %s" % e)

        return payload

    def edit_requirement_application(self, payload, node_info):
        try:
            lgr.info("Edit Requirement Application")
            gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

            # if 'institution_id' in payload.keys():
            #    institution = Institution.objects.get(id=payload['institution_id'])
            # elif gateway_profile.institution not in ['', None]:

            institution = gateway_profile.institution

            bid_requirement = BidRequirement.objects.get(id=payload['bid_requirement_id'])
            if bid_requirement.bid.closed():
                payload['response'] = "This Bid is Close"
                payload['response_status'] = '00'
                return payload

            bid_requirement_applications_qs = BidRequirementApplication.objects.filter(
                bid_requirement_id=payload['bid_requirement_id'],
                bid_application__institution=institution
            )

            if len(bid_requirement_applications_qs) == 1:
                requirement_application = bid_requirement_applications_qs[0]

            else:
                if len(bid_requirement_applications_qs) > 1: bid_requirement_applications_qs.delete()

                bid_requirement = BidRequirement.objects.get(id=payload['bid_requirement_id']),

                bid_application = BidApplication.objects.get(bid=bid_requirement.bid, institution=institution)
                requirement_application = BidRequirementApplication(
                    bid_requirement=bid_requirement,
                    bid_application=bid_application,
                    unit_price=Decimal(payload['unit_price'])
                )
                requirement_application.save()

            bid_app = requirement_application.bid_application

            new_unit_price = Decimal(payload['unit_price'])
            if requirement_application.unit_price >= new_unit_price:
                requirement_application.unit_price = new_unit_price
                requirement_application.save()

                req_app_count = BidRequirementApplication.objects.filter(bid_application=bid_app).count()
                req_count = requirement_application.bid_application.bid.bidrequirement_set.count()

                if req_app_count == req_count:
                    total_price = BidRequirementApplication.objects.filter(
                        bid_application=bid_app
                    ).annotate(
                        total=Sum(F('bid_requirement__quantity') * F('unit_price'), output_field=models.DecimalField())
                    ).aggregate(Sum('total'))

                    bid_app.current_total_price = total_price.get('total__sum')
                    bid_app.save()

                    application_change = BidAmountActivity(application=bid_app, price=Decimal(payload['unit_price']))
                    application_change.save()

                # publish new application
                publish_notifications(bid_app.bid, gateway_profile)
                # end publish new application

                result = 'New Unit Price is ' + payload['unit_price'] + ' .'

            elif requirement_application.unit_price != new_unit_price:
                result = 'The price can only go down'
            else:
                result = "There wasn't a price change"

            payload['result'] = result
            payload['response'] = result
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error Updating Requirement Application: %s" % e)

        return payload

    def get_live_created_bid_details(self, payload, node_info):
        try:
            bid = Bid.objects.get(id=payload['bid_id'])
            payload['bid_name'] = bid.name
            payload['bid_description'] = bid.description
            payload['bid_closing'] = bid.bid_close.isoformat()
            payload['bid_image'] = bid.image.url if bid.image else ''

            payload['response'] = 'Bid Details Updated'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error on Getting Bid Details: %s" % e)

        return payload

    def get_created_bid_details(self, payload, node_info):
        try:

            bid = Bid.objects.get(id=payload['bid_id'])
            payload['bid_name'] = bid.name
            payload['bid_description'] = bid.description
            payload['bid_image'] = bid.image.url if bid.image else ''

            if bid.open():
                payload['trigger'] = 'opened%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
            else:
                payload['trigger'] = 'closed%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')

            payload['response'] = 'Bid Details Updated'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error on Getting Bid Details: %s" % e)

        return payload

    def bid_application(self, payload, node_info):
        try:
            gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
            institution = gateway_profile.institution
            bid = Bid.objects.get(id=payload['bid_id'])
            created_bid_app_status = BidApplicationStatus.objects.get(name='Created')

            try:
                bid_application = BidApplication.objects.get(bid=bid, institution=institution)
            except ObjectDoesNotExist:
                bid_application = BidApplication(bid=bid, institution=institution)
                bid_application.status = created_bid_app_status
                if not bid.biddocument_set.count():# todo remove dup
                    bid_application.completed = True
                bid_application.save()

            if 'pending_bid_documents' in payload.keys() and 'attachment' in payload.keys():
                bid_document = BidDocument.objects.get(id=payload['pending_bid_documents'])
                bid_document_application, created = BidDocumentApplication.objects.get_or_create(
                    bid_application=bid_application,
                    bid_document=bid_document
                )
                #  bid_document_application.save()
                ##########################
                media_temp = settings.MEDIA_ROOT + '/tmp/uploads/'

                if payload['attachment'] not in [None, '']:
                    #lgr.info('saving bid document app attachment')
                    filename = payload['attachment']
                    tmp_file = media_temp + str(filename)
                    with open(tmp_file, 'r') as f:
                        bid_document_application.attachment.save(filename, File(f), save=False)
                    f.close()
                    bid_document_application.save()
                #######################

            if bid.application_complete_from(institution):
                bid_application.completed = True
                bid_application.save()

            if bid_application.completed:
                payload['trigger'] = 'application_completed%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')
                payload['application_status'] = 'Application Created, Waiting for Approval from ' + bid.institution.name
            else:
                payload['trigger'] = 'application_not_completed%s' % (','+payload['trigger'] if 'trigger' in payload.keys() else '')

            payload['response'] = 'Bid Application Details'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error on Getting Bid Application Details: %s" % e)

        return payload

    def create_bid_application(self, payload, node_info):
        try:
            gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

            # if 'institution_id' in payload.keys():
            #    institution = Institution.objects.get(id=payload['institution_id'])
            # elif gateway_profile.institution not in ['', None]:

            institution = gateway_profile.institution

            bid = Bid.objects.get(id=payload['bid_id'])
            bid_application_status = BidApplicationStatus.objects.get(name='Created')

            try:
                bid_application = BidApplication.objects.get(bid=bid, institution=institution)
            except ObjectDoesNotExist:
                bid_application = BidApplication(bid=bid, institution=institution)
                bid_application.status = bid_application_status
                bid_application.save()

            bid_document = BidDocument.objects.get(id=payload['pending_bid_documents'])
            bid_document_application, created = BidDocumentApplication.objects.get_or_create(
                bid_application=bid_application,
                bid_document=bid_document
            )
            #  bid_document_application.save()
            ##########################
            media_temp = settings.MEDIA_ROOT + '/tmp/uploads/'

            if 'attachment' in payload.keys() and payload['attachment'] not in [None, '']:
                filename = payload['attachment']
                tmp_file = media_temp + str(filename)
                with open(tmp_file, 'r') as f:
                    bid_document_application.attachment.save(filename, File(f), save=False)
                f.close()
            #######################

            if bid.application_complete_from(institution):
                bid_application.completed = True
                bid_application.save()

            payload['bid_application'] = "Bid Document Application on " + bid.name + \
                                         " submitted Succefully."

            # publish new application
            # publish_notifications(bid_application.bid, gateway_profile)
            # end publish new application

            payload['response'] = 'Bid Document Submitted'
            payload['response_status'] = '00'

        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error on Submitted Bid Document: %s" % e)

        return payload

    def edit_bid_application(self, payload, node_info):
        lgr.info("Edit Bid Application")  # todo unused
        try:
            gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
            institution = gateway_profile.institution

            # lgr.info("New BidApplication Price: " + payload['unit_price'])
            # lgr.info("Payload: %s "%json.dumps(payload))

            lgr.info("BidApplication ID to update: %s " % payload['bid_app_id'])

            bid_application = BidApplication.objects.get(id=payload['bid_app_id'])
            # lgr.info("Current BidApplication Price: " + str(bid_application.unit_price))

            # new_unit_price = Decimal(payload['unit_price'])

            payload['response'] = 'Bid Application Updated'
            lgr.info("Bid Application Updated")
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error Updating Bid Application: %s" % e)
        return payload

    def edit_bid(self, payload, node_info):
        lgr.info("Edit Bid")
        try:
            gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
            lgr.info("Bid ID to update: %s " % payload['bid_id'])

            date_string = payload['open_date'] + ' ' + payload['open_time']
            date_obj = datetime.strptime(date_string, '%d/%m/%Y %I:%M %p')
            bid_open = pytz.timezone(gateway_profile.user.profile.timezone).localize(date_obj)

            date_string = payload['close_date'] + ' ' + payload['close_time']
            date_obj = datetime.strptime(date_string, '%d/%m/%Y %I:%M %p')
            bid_close = pytz.timezone(gateway_profile.user.profile.timezone).localize(date_obj)

            if 'institution_id' in payload.keys():
                institution = Institution.objects.get(id=payload['institution_id'])
            elif gateway_profile.institution not in ['', None]:
                institution = gateway_profile.institution

            industry_section = IndustrySection.objects.get(id=payload['industry_section_id'])

            bid = Bid.objects.get(id=payload['bid_id'], institution=institution)
            bid.institution = institution
            bid.name = payload['name']
            bid.description = payload['description']
            bid.bid_open = bid_open
            bid.bid_close = bid_close
            bid.industry_section = industry_section

            ##########################
            '''
            media_temp = settings.MEDIA_ROOT + '/tmp/uploads/'

            if 'image' in payload.keys() and payload['image'] not in [None, '']:
                imagename = payload['image']
                tmp_image = media_temp + str(imagename)
                with open(tmp_image, 'r') as f:
                    bid.image.save(imagename, File(f), save=False)
                f.close()

            if 'file' in payload.keys() and payload['file'] not in [None, '']:
                filename = payload['file']
                tmp_file = media_temp + str(filename)
                with open(tmp_file, 'r') as f:
                    bid.attachment.save(filename, File(f), save=False)
                f.close()
            '''
            if bid.open():
                bid.invoiced = False

            #######################
            bid.save()

            payload['bid_name'] = bid.name

            lgr.info(json.dumps(payload))
            payload['response'] = 'Bid Updated'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error Updating Bid Application: %s" % e)
        return payload

    def view_edit_bid(self, payload, node_info):
        lgr.info("View Edit Bid")
        try:
            gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
            profile_tz = pytz.timezone(gateway_profile.user.profile.timezone)

            lgr.info("Bid ID to update: %s " % payload['bid_id'])
            bid = Bid.objects.get(id=payload['bid_id'])

            payload['bid_name'] = bid.name
            payload['bid_description'] = bid.description
            payload['bid_image'] = bid.image.url if bid.image else ''
            payload['bid_attachment'] = bid.attachment.url if bid.attachment else ''

            payload['bid_open_date'] = profile_tz.normalize(bid.bid_open.astimezone(profile_tz)).strftime('%d/%m/%Y')
            payload['bid_open_time'] = profile_tz.normalize(bid.bid_open.astimezone(profile_tz)).strftime('%I:%M %p')

            payload['bid_close_date'] = profile_tz.normalize(bid.bid_close.astimezone(profile_tz)).strftime('%d/%m/%Y')
            payload['bid_close_time'] = profile_tz.normalize(bid.bid_close.astimezone(profile_tz)).strftime('%I:%M %p')

            payload['bid_institution'] = bid.institution.id
            payload['bid_industry_section'] = bid.industry_section.id

            lgr.info(json.dumps(payload))
            payload['response'] = 'Bid Update'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error Updating Bid Application: %s" % e)
        return payload

    def view_delete_bid(self, payload, node_info):
        lgr.info("View Delete Bid")
        try:
            gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
            profile_tz = pytz.timezone(gateway_profile.user.profile.timezone)

            lgr.info("Bid ID to delete: %s " % payload['bid_id'])
            bid = Bid.objects.get(id=payload['bid_id'])

            payload['bid_name'] = bid.name
            payload['bid_description'] = bid.description
            payload['bid_image'] = bid.image.url if bid.image else ''
            payload['bid_attachment'] = bid.attachment.url if bid.attachment else ''

            payload['bid_open_date'] = profile_tz.normalize(bid.bid_open.astimezone(profile_tz)).strftime('%d/%m/%Y')
            payload['bid_open_time'] = profile_tz.normalize(bid.bid_open.astimezone(profile_tz)).strftime('%I:%M %p')

            payload['bid_close_date'] = profile_tz.normalize(bid.bid_close.astimezone(profile_tz)).strftime('%d/%m/%Y')
            payload['bid_close_time'] = profile_tz.normalize(bid.bid_close.astimezone(profile_tz)).strftime('%I:%M %p')

            payload['bid_institution'] = bid.institution.id
            payload['bid_industry_section'] = bid.industry_section.id

            lgr.info(json.dumps(payload))
            payload['response'] = 'Bid Delete'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error Getting Bid to Delete: %s" % e)
        return payload

    def delete_bid(self, payload, node_info):
        lgr.info("Delete Bid")
        try:
            # gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
            lgr.info("Bid ID to delete: %s " % payload['bid_id'])
            bid = Bid.objects.get(id=payload['bid_id'])

            payload['bid_name'] = bid.name
            payload['bid_description'] = bid.description
            payload['bid_image'] = bid.image.url if bid.image else ''
            payload['bid_attachment'] = bid.attachment.url if bid.attachment else ''

            payload['bid_open_date'] = bid.bid_open.date().strftime('%d/%m/%Y')
            payload['bid_open_time'] = bid.bid_open.time().strftime('%I:%M %p')

            payload['bid_close_date'] = bid.bid_close.date().strftime('%d/%m/%Y')
            payload['bid_close_time'] = bid.bid_close.time().strftime('%I:%M %p')

            bid.delete()

            lgr.info(json.dumps(payload))
            payload['response'] = 'Bid Deleted'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error Deleting Bid: %s" % e)
        return payload

    def create_bid_requirement(self, payload, node_info):
        try:

            name = payload['name']
            description = ''#payload['description']
            quantity = int(payload['requirement_quantity'])

            bid = Bid.objects.get(id=payload['bid_id'])

            bid_requirement = BidRequirement(
                bid=bid,
                quantity=quantity,
                description=description,
                name=name
            )
            ##########################
            media_temp = settings.MEDIA_ROOT + '/tmp/uploads/'

            if 'image' in payload.keys() and payload['image'] not in [None, '']:
                imagename = payload['image']
                tmp_image = media_temp + str(imagename)
                with open(tmp_image, 'r') as f:
                    bid_requirement.image.save(imagename, File(f), save=False)
                f.close()

            if 'attachment' in payload.keys() and payload['attachment'] not in [None, '']:
                filename = payload['attachment']
                tmp_file = media_temp + str(filename)
                with open(tmp_file, 'r') as f:
                    bid_requirement.attachment.save(filename, File(f), save=False)
                f.close()
            #######################

            bid_requirement.save()

            for bid_app in bid.bidapplication_set.all():
                bid_app.current_total_price = None
                bid_app.save()

            payload['response'] = 'Bid Requirement Created'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            payload['response']="Error on Create Bid Requirement: %s" % e
            lgr.info("Error on Create Bid Requirement: %s" % e)
        return payload

    def create_bid_document(self, payload, node_info):
        try:
            name = payload['name']
            bid = Bid.objects.get(id=payload['bid_id'])

            bid_document = BidDocument(
                bid=bid,
                name=name
            )

            bid_document.save()

            for bid_app in bid.bidapplication_set.all():
                bid_app.completed = False
                bid_app.save()

            payload['response'] = 'Bid Document Created'
            payload['response_status'] = '00'

        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error on Create Bid Document: %s" % e)
        return payload

    def edit_bid_requirement(self, payload, node_info):
        try:
            gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

            bid_requirement = BidRequirement.objects.get(id=payload['bid_requirement_id'])

            name = payload['name']
            # todo description = payload['description']
            quantity = int(payload['requirement_quantity'])

            bid_requirement.name = name
            bid_requirement.quantity = quantity

            # bid_requirement = BidRequirement(bid=bid, quantity=quantity, description=description, name=name)
            '''
            ##########################
            media_temp = settings.MEDIA_ROOT + '/tmp/uploads/'

            if 'image' in payload.keys() and payload['image'] not in [None, '']:
                imagename = payload['image']
                tmp_image = media_temp + str(imagename)
                with open(tmp_image, 'r') as f:
                    bid_requirement.image.save(imagename, File(f), save=False)
                f.close()

            if 'attachment' in payload.keys() and payload['attachment'] not in [None, '']:
                filename = payload['attachment']
                tmp_file = media_temp + str(filename)
                with open(tmp_file, 'r') as f:
                    bid_requirement.attachment.save(filename, File(f), save=False)
                f.close()
            #######################
            '''

            bid_requirement.save()

            for bid_app in bid_requirement.bid.bidapplication_set.all():
                total_price = BidRequirementApplication.objects.filter(
                    bid_application=bid_app
                ).annotate(
                    total=Sum(F('bid_requirement__quantity') * F('unit_price'), output_field=models.DecimalField())
                ).aggregate(Sum('total'))

                bid_app.current_total_price = total_price.get('total__sum')
                bid_app.save()

                # application_change = BidAmountActivity(application=bid_app, price=Decimal(payload['unit_price']))
                # application_change.save()

                # result = 'New Unit Price is ' + payload['unit_price'] + ' .'
                # publish new application
                publish_notifications(bid_app.bid, gateway_profile)

            payload['response'] = 'Bid Requirement Updated'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error on Create Bid Requirement: %s" % e)
        return payload

    def edit_bid_document(self, payload, node_info):
        try:
            # gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
            bid_document = BidDocument.objects.get(id=payload['bid_document_id'])

            name = payload['document_name']
            bid_document.name = name
            bid_document.save()

            payload['response'] = 'Bid Document Updated'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error on Update Bid Document: %s" % e)
        return payload

    def delete_bid_requirement(self, payload, node_info):
        try:
            gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

            bid_requirement = BidRequirement.objects.get(id=payload['bid_requirement_id'])
            bid = bid_requirement.bid
            bid_requirement.delete()

            for bid_app in bid.bidapplication_set.all():
                total_price = BidRequirementApplication.objects.filter(
                    bid_application=bid_app
                ).annotate(
                    total=Sum(F('bid_requirement__quantity') * F('unit_price'), output_field=models.DecimalField())
                ).aggregate(Sum('total'))

                bid_app.current_total_price = total_price.get('total__sum')
                bid_app.save()

                # application_change = BidAmountActivity(application=bid_app, price=Decimal(payload['unit_price']))
                # application_change.save()

                # result = 'New Unit Price is ' + payload['unit_price'] + ' .'
                # publish new application
                publish_notifications(bid_app.bid, gateway_profile)

            payload['response'] = 'Bid Requirement Deleted'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error on Create Bid Requirement: %s" % e)
        return payload

    def get_bid_requirement_details(self, payload, node_info):
        try:
            # gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
            bid_requirement = BidRequirement.objects.get(id=payload['bid_requirement_id'])
            payload['bid_requirement_name'] = bid_requirement.name
            payload['bid_requirement_quantity'] = bid_requirement.quantity
            # payload['name'] = bid_requirement.name

            payload['response'] = 'Got Bid Requirement Details'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error on Get Bid Requirement: %s" % e)
        return payload

    def get_bid_document_details(self, payload, node_info):
        try:
            # gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
            bid_document = BidDocument.objects.get(id=payload['bid_document_id'])
            payload['bid_document_name'] = bid_document.name

            # payload['name'] = bid_requirement.name

            payload['response'] = 'Got Bid Document Details'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error on Get Bid Document: %s" % e)
        return payload

    def delete_bid_document(self, payload, node_info):
        try:
            # gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
            bid_document = BidDocument.objects.get(id=payload['bid_document_id'])
            bid_document.delete()

            payload['response'] = 'Bid Document Deleted'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error on Delete Bid Document: %s" % e)
        return payload

    def create_bid_requirement_application(self, payload, node_info):
        try:
            gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
            bid_requirement = BidRequirement.objects.get(id=payload['bid_requirement_id'])

            if bid_requirement.bid.closed():
                payload['response'] = "This Bid is Close"
                payload['response_status'] = '00'
                return payload

            unit_price = Decimal(payload['unit_price'])
            description = payload['description'] if 'description' in payload.keys() else ''

            bid_application = BidApplication.objects.get(
                bid=bid_requirement.bid,
                institution=gateway_profile.institution)

            bid_requirement_applications_qs = BidRequirementApplication.objects.filter(
                bid_application=bid_application,
                bid_requirement=bid_requirement
            )

            if len(bid_requirement_applications_qs)==1:
                bid_requirement_application = bid_requirement_applications_qs[0]
                bid_requirement_application.description = description
                bid_requirement_application.unit_price = unit_price

            else:
                if len(bid_requirement_applications_qs) > 1: bid_requirement_applications_qs.delete()

                bid_requirement_application = BidRequirementApplication(
                    bid_application=bid_application,
                    description=description,
                    unit_price=unit_price,
                    bid_requirement=bid_requirement
                )

            bid_requirement_application.save()

            ##########################
            media_temp = settings.MEDIA_ROOT + '/tmp/uploads/'

            if 'attachment' in payload.keys() and payload['attachment'] not in [None, '']:
                filename = payload['attachment']
                tmp_file = media_temp + str(filename)
                with open(tmp_file, 'r') as f:
                    bid_requirement_application.attachment.save(filename, File(f), save=False)
                f.close()
            #######################

            req_app_count = BidRequirementApplication.objects.filter(bid_application=bid_application).count()
            req_count = bid_application.bid.bidrequirement_set.count()

            if req_app_count == req_count:
                total_price = BidRequirementApplication.objects.filter(
                    bid_application=bid_application
                ).annotate(
                    total=Sum(F('bid_requirement__quantity') * F('unit_price'), output_field=models.DecimalField())
                ).aggregate(Sum('total'))

                bid_application.current_total_price = total_price.get('total__sum')
                bid_application.save()

                application_change = BidAmountActivity(application=bid_application, price=Decimal(payload['unit_price']))
                application_change.save()

            # publish new application
            publish_notifications(bid_application.bid, gateway_profile)
            # end publish new application

            payload['response'] = 'Bid Requirement Application Created'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error on Create Bid Requirement Application: %s" % e)
        return payload

    def view_bid_requirement_application_form(self, payload, node_info):
        try:
            payload['response'] = 'Bid Requirement Application Created'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error on Create Bid Requirement Application: %s" % e)
        return payload

    def create_bid(self, payload, node_info):
        try:
            gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

            date_string = payload['open_date'] + ' ' + payload['open_time']
            date_obj = datetime.strptime(date_string, '%d/%m/%Y %I:%M %p')
            bid_open = pytz.timezone(gateway_profile.user.profile.timezone).localize(date_obj)

            date_string = payload['close_date'] + ' ' + payload['close_time']
            date_obj = datetime.strptime(date_string, '%d/%m/%Y %I:%M %p')
            bid_close = pytz.timezone(gateway_profile.user.profile.timezone).localize(date_obj)

            if 'institution_id' in payload.keys():
                institution = Institution.objects.get(id=payload['institution_id'])
            elif gateway_profile.institution not in ['', None]:
                institution = gateway_profile.institution

            else:
                raise Exception('Missing institution')

            industry_section = IndustrySection.objects.get(id=payload['industry_section_id'])
            bid = Bid(
                institution=institution,
                name=payload['name'],
                description=payload['description'],
                bid_open=bid_open,
                bid_close=bid_close,
                industry_section=industry_section
            )

            bid.show_leading = ('show_leading' in payload.keys() and payload['show_leading'] == 'on')

            ##########################
            media_temp = settings.MEDIA_ROOT + '/tmp/uploads/'

            if 'image' in payload.keys() and payload['image'] not in [None, '']:
                imagename = payload['image']
                tmp_image = media_temp + str(imagename)
                with open(tmp_image, 'r') as f:
                    bid.image.save(imagename, File(f), save=False)
                f.close()

            if 'file' in payload.keys() and payload['file'] not in [None, '']:
                filename = payload['file']
                tmp_file = media_temp + str(filename)
                with open(tmp_file, 'r') as f:
                    bid.attachment.save(filename, File(f), save=False)
                f.close()
            #######################

            bid.save()

            payload['create_bid'] = bid.name + ' Created Successfully'
            payload['response'] = 'Bid Created'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error on Create Bid: %s" % e)
        return payload

    def edit_selected_bid(self, payload, node_info):
        try:
            gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])

            date_string = payload['open_date'] + ' ' + payload['open_time']
            date_obj = datetime.strptime(date_string, '%d/%m/%Y %I:%M %p')
            bid_open = pytz.timezone(gateway_profile.user.profile.timezone).localize(date_obj)

            date_string = payload['close_date'] + ' ' + payload['close_time']
            date_obj = datetime.strptime(date_string, '%d/%m/%Y %I:%M %p')
            bid_close = pytz.timezone(gateway_profile.user.profile.timezone).localize(date_obj)

            industry_section = IndustrySection.objects.get(id=payload['industry_section_id'])
            bid = Bid.objects.get(id=payload['bid_id'])
            bid.bid_close = bid_close
            bid.bid_open = bid_open
            bid.industry_section = industry_section

            ##########################
            media_temp = settings.MEDIA_ROOT + '/tmp/uploads/'

            if 'image' in payload.keys() and payload['image'] not in [None, '']:
                imagename = payload['image']
                tmp_image = media_temp + str(imagename)
                with open(tmp_image, 'r') as f:
                    bid.image.save(imagename, File(f), save=False)
                f.close()

            if 'file' in payload.keys() and payload['file'] not in [None, '']:
                filename = payload['file']
                tmp_file = media_temp + str(filename)
                with open(tmp_file, 'r') as f:
                    bid.attachment.save(filename, File(f), save=False)
                f.close()
            #######################

            bid.save()

            payload['response'] = 'Bid Updated'
            payload['response_status'] = '00'
        except Exception, e:
            payload['response_status'] = '96'
            lgr.info("Error on Edit Bid: %s" % e)

        return payload


class Trade(System):
    pass


class Payments(System):
    pass


# Ignore results ensure that no results are saved. Saved results on damons would cause deadlocks and fillup of disk
@app.task(ignore_result=True)
@transaction.atomic
@single_instance_task(60 * 10)
def rankings():
    # query distinct bids with bid applications that rank_changed is True
    changed_bids = Bid.objects.all()  # filter(bidapplication__rank_changed=True).distinct()
    # if changed_bids:
    # import paho.mqtt.client as mqtt
    client = mqtt.Client()
    client.username_pw_set("Super@User", "apps")
    client.connect("127.0.0.1", 1883, 60)
    for bid in changed_bids:
        #   get new rankings
        rankings = bid.app_rankings(None)
        bid_change = {"type": "ranking", "data": rankings}
        #   send the new rankings to each bid application creator
        client.publish('rankings/' + str(bid.pk), json.dumps(bid_change, cls=DjangoJSONEncoder))

    client.disconnect()


@app.task(ignore_result=True)
@transaction.atomic
@single_instance_task(60 * 10)
def closed_bids_invoicing():
    bid_amount_activity = BidAmountActivity.objects.filter(application__bid__bid_close__lte=timezone.now(),
                                                           application__bid__bid_open__lte=timezone.now(),
                                                           application__bid__invoiced=False, price__gt=0). \
        values('application__bid__id'). \
        annotate(max_price=Max('price'), min_price=Min('price'))

    if bid_amount_activity.exists():
        # import paho.mqtt.client as mqtt
        for i in bid_amount_activity:
            lgr.info('Bid %s' % i)
            bid = Bid.objects.get(id=i['application__bid__id'])
            bid_invoice_type = BidInvoiceType.objects.get(id=1)

            amount = (Decimal(bid_invoice_type.invoicing_rate) / Decimal(100)) * Decimal(
                i['max_price'] - i['min_price'])

            bid_invoice = BidInvoice(bid_invoice_type=bid_invoice_type, bid=bid, max_price=i['max_price'],
                                     min_price=i['min_price'], amount=amount)
            bid_invoice.save()

            bid.invoiced = True
            bid.save()

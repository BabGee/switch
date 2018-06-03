import base64
import csv
import json
import logging
import operator
import time
from datetime import datetime
from decimal import Decimal, ROUND_DOWN

import pytz
import re
from django.apps import apps
from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.validators import validate_email
from django.db import IntegrityError
from django.db import transaction
from django.db.models import Count, Sum, Max, Min, Avg, Q, F, Func, Value, CharField, Case, Value, When, TextField
from django.db.models.functions import Cast
from django.db.models.functions import Concat, Substr
from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import localtime
from django.utils.timezone import utc
import numpy as np
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.core.serializers.json import DjangoJSONEncoder
from django.core import serializers

from .models import *

lgr = logging.getLogger('primary.core.administration')

class Data:
    def industries_categories(self,payload,gateway_profile,profile_tz,data):
        r = []
	iss = IndustrySection.objects.all()
	'''
	for i in iss:
	    cl = {
        	'name':i.isic_code,
		'id':i.pk,
	        'description':i.description,
        	'divisions':[
                     {
                	'name':division.isic_code,
			'id':division.pk,
	                'description': division.description,
        	        'groups':[
                	    {
                        	'name':group.isic_code,
				'id':group.pk,
	                        'description': group.description,
        	                'classes':[
                	            {
                        	        'name': industry_class.isic_code,
					'id':industry_class.pk,
                                	'description': industry_class.description,
	                            } for industry_class in group.industryclass_set.all()
                        	]
                    	    } for group in division.industrygroup_set.all()
                	]
            	    } for division in i.industrydivision_set.all()
        	]

    	    }
	    r.append(cl)
	#lgr.info(r)
	params = dict(
		data=r
	)

	'''

	c = [{"label": "name", "type": "string"}, {"label": "id", "type": "number"},
                          {"label": "description", "type": "string"}, {"label": "level", "type": "object"}]

	def _class(industryclass_set):
		return [[industry_class.pk,industry_class.isic_code,industry_class.description] for industry_class in industryclass_set]
	def _group(industrygroup_set): 
		return [[group.pk,group.isic_code,group.description, _class(group.industryclass_set.all())] for group in industrygroup_set]
	def _division(industrydivision_set):	
		return [[division.pk,division.isic_code,division.description, _group(division.industrygroup_set.all())] for division in industrydivision_set]

	for i in iss:
	    r.append([i.pk,i.isic_code,i.description, _division(i.industrydivision_set.all())])

	#lgr.info(r)
	params = dict(
		rows=r,
		cols=c
	)
	return params



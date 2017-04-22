from __future__ import absolute_import
from celery import shared_task
from celery.contrib.methods import task_method
from celery.contrib.methods import task
from switch.celery import app
from celery.utils.log import get_task_logger

from django.shortcuts import render
from django.contrib.auth.models import User
#from upc.backend.wrappers import *
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
import time, os, random, string, json
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from django.db import IntegrityError
from django.contrib.gis.geos import Point
from django.conf import settings
from django.core.files import File
import base64, re

from loyalty.models import *

import logging
lgr = logging.getLogger('loyalty')


class Wrappers:
	pass

class System(Wrappers):
	pass

class Trade(System):
	pass


lgr = get_task_logger(__name__)
#Celery Tasks Here

# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-04-18 04:58
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('upc', '0002_auto_20160226_0509'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='gatewayprofile',
            name='created_by',
        ),
    ]

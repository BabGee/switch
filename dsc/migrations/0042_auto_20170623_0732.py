# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-06-23 04:32
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dsc', '0041_auto_20170620_2143'),
    ]

    operations = [
        migrations.RenameField(
            model_name='datalist',
            old_name='pn',
            new_name='pn_data',
        ),
    ]

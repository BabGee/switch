# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-05-19 12:20
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dsc', '0028_datalistquery_display_data'),
    ]

    operations = [
        migrations.RenameField(
            model_name='datalistquery',
            old_name='display_data',
            new_name='data_response',
        ),
    ]

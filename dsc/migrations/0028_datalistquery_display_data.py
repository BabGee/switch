# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-05-19 12:19
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dsc', '0027_datalistquery_list_filters'),
    ]

    operations = [
        migrations.AddField(
            model_name='datalistquery',
            name='display_data',
            field=models.BooleanField(default=False),
        ),
    ]

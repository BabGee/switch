# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-07-06 10:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vbs', '0022_remove_accounttype_institution'),
    ]

    operations = [
        migrations.AddField(
            model_name='accountmanager',
            name='credit_paid',
            field=models.BooleanField(default=False),
        ),
    ]

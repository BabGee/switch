# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-07-04 18:35
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0006_enrollment_date_of_enrollment'),
    ]

    operations = [
        migrations.RenameField(
            model_name='enrollment',
            old_name='date_of_enrollment',
            new_name='enrollment_date',
        ),
    ]

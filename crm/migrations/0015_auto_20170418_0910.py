# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-04-18 06:10
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0014_enrollment_enrollment_type'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='enrollment',
            name='institution',
        ),
        migrations.RemoveField(
            model_name='enrollment',
            name='product_item',
        ),
    ]

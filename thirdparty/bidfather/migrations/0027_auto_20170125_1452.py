# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-01-25 14:52
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bidfather', '0026_auto_20170125_0817'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bidapplication',
            name='attachment',
        ),
        migrations.RemoveField(
            model_name='bidapplication',
            name='description',
        ),
    ]

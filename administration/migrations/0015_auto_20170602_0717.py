# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-06-02 04:17
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0014_auto_20170602_0712'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='forex',
            name='currency',
        ),
        migrations.DeleteModel(
            name='Forex',
        ),
    ]

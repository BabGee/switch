# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-06-12 04:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paygate', '0010_auto_20160603_0751'),
    ]

    operations = [
        migrations.AlterField(
            model_name='endpoint',
            name='account_id',
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
        migrations.AlterField(
            model_name='endpoint',
            name='password',
            field=models.CharField(blank=True, max_length=1024, null=True),
        ),
    ]

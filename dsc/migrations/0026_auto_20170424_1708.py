# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-04-24 14:08
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dsc', '0025_auto_20170424_1640'),
    ]

    operations = [
        migrations.AddField(
            model_name='datalistquery',
            name='link_params',
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
        migrations.AlterField(
            model_name='datalistquery',
            name='links',
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
    ]

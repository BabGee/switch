# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-04-24 06:16
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0001_initial'),
        ('upc', '0003_remove_gatewayprofile_created_by'),
        ('vbs', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='accounttype',
            name='gateway',
            field=models.ManyToManyField(blank=True, to='administration.Gateway'),
        ),
        migrations.AddField(
            model_name='accounttype',
            name='institution',
            field=models.ManyToManyField(blank=True, to='upc.Institution'),
        ),
    ]

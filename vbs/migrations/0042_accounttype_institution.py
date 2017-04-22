# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-04-05 12:32
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('upc', '0019_auto_20170402_1036'),
        ('vbs', '0041_auto_20170305_1225'),
    ]

    operations = [
        migrations.AddField(
            model_name='accounttype',
            name='institution',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='upc.Institution'),
        ),
    ]

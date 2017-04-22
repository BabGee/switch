# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-01-23 10:20
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vbs', '0027_auto_20170123_1011'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='creditoverdue',
            name='credit_type',
        ),
        migrations.AddField(
            model_name='creditoverdue',
            name='account_type',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='vbs.AccountType'),
            preserve_default=False,
        ),
    ]

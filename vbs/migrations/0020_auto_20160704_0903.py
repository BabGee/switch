# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-07-04 09:03
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vbs', '0019_account_credit_limit_currency'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='accounttype',
            name='currency',
        ),
        migrations.AlterField(
            model_name='accountmanager',
            name='account_type',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='vbs.AccountType'),
            preserve_default=False,
        ),
    ]

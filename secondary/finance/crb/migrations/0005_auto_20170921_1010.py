# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-09-21 07:10
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('crb', '0004_auto_20170921_0958'),
    ]

    operations = [
        migrations.AlterField(
            model_name='referenceactivity',
            name='status',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bridge.TransactionStatus'),
        ),
        migrations.DeleteModel(
            name='ReferenceActivityStatus',
        ),
    ]

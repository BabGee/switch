# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-05-17 20:41
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bridge', '0006_transaction_fingerprint'),
    ]

    operations = [
        migrations.AlterField(
            model_name='service',
            name='access_level',
            field=models.ManyToManyField(blank=True, to='administration.AccessLevel'),
        ),
    ]

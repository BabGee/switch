# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-06-07 07:14
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crc', '0008_cardrecordactivity'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cardtype',
            name='code',
            field=models.CharField(max_length=5, unique=True),
        ),
    ]

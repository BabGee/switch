# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-10-01 20:13
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crb', '0013_auto_20171001_1736'),
    ]

    operations = [
        migrations.AddField(
            model_name='creditgrade',
            name='hierarchy',
            field=models.IntegerField(default=1),
            preserve_default=False,
        ),
    ]

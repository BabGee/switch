# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-10-01 07:10
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crb', '0008_referencerisk'),
    ]

    operations = [
        migrations.AddField(
            model_name='creditgrade',
            name='max_credit_score',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='creditgrade',
            name='min_credit_score',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]

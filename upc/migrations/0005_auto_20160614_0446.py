# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-06-14 04:46
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('upc', '0004_auto_20160528_0459'),
    ]

    operations = [
        migrations.RenameField(
            model_name='profile',
            old_name='postal_addr',
            new_name='postal_address',
        ),
    ]

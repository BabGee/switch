# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-05-19 09:05
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('upc', '0023_gatewayprofile_email_activation_code'),
    ]

    operations = [
        migrations.RenameField(
            model_name='institution',
            old_name='physical_addr',
            new_name='physical_address',
        ),
        migrations.RenameField(
            model_name='institutiontill',
            old_name='physical_addr',
            new_name='physical_address',
        ),
        migrations.RenameField(
            model_name='profile',
            old_name='physical_addr',
            new_name='physical_address',
        ),
        migrations.AlterField(
            model_name='profile',
            name='address',
            field=models.CharField(blank=True, help_text=b'Address 2/Postal Address', max_length=200, null=True),
        ),
    ]

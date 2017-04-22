# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-09-19 11:02
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0006_auto_20160919_1023'),
    ]

    operations = [
        migrations.RenameField(
            model_name='industryclass',
            old_name='code',
            new_name='isic_code',
        ),
        migrations.RenameField(
            model_name='industrydivision',
            old_name='code',
            new_name='isic_code',
        ),
        migrations.RenameField(
            model_name='industrygroup',
            old_name='code',
            new_name='isic_code',
        ),
        migrations.RenameField(
            model_name='industrysection',
            old_name='code',
            new_name='isic_code',
        ),
        migrations.RemoveField(
            model_name='industryclass',
            name='group_code',
        ),
        migrations.RemoveField(
            model_name='industrydivision',
            name='section_code',
        ),
        migrations.RemoveField(
            model_name='industrygroup',
            name='division_code',
        ),
    ]

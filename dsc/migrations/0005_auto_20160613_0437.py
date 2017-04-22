# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-06-13 04:37
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dsc', '0004_auto_20160612_1812'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='fileuploadactivity',
            name='tmp_file_path',
        ),
        migrations.AddField(
            model_name='fileuploadactivity',
            name='processed_file_path',
            field=models.FileField(blank=True, max_length=200, null=True, upload_to=b'dsc_fileuploadactivity/'),
        ),
    ]

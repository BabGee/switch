# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-09-17 09:24
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0003_auto_20160821_0524'),
        ('vcs', '0010_auto_20160917_0758'),
    ]

    operations = [
        migrations.AddField(
            model_name='code',
            name='code_gateway',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='administration.Gateway'),
        ),
        migrations.AlterField(
            model_name='code',
            name='gateway',
            field=models.ManyToManyField(related_name='code__gateway', to='administration.Gateway'),
        ),
    ]

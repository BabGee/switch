# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-08-27 12:47
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dsc', '0010_datalist_title'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataListQuery',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(max_length=50, unique=True)),
                ('description', models.CharField(max_length=200)),
                ('model_name', models.CharField(max_length=100)),
                ('model_values', models.CharField(max_length=2048)),
                ('gateway_profile_filter', models.CharField(blank=True, max_length=100, null=True)),
                ('name_filter', models.CharField(blank=True, max_length=100, null=True)),
            ],
        ),
        migrations.RemoveField(
            model_name='reporting',
            name='access_level',
        ),
        migrations.RemoveField(
            model_name='reporting',
            name='gateway',
        ),
        migrations.RemoveField(
            model_name='reporting',
            name='institution',
        ),
        migrations.RemoveField(
            model_name='reporting',
            name='status',
        ),
        migrations.DeleteModel(
            name='Reporting',
        ),
        migrations.DeleteModel(
            name='ReportingStatus',
        ),
        migrations.AddField(
            model_name='datalist',
            name='query',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dsc.DataListQuery'),
        ),
    ]

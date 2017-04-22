# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-10-13 13:08
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bidfather', '0009_auto_20160926_0632'),
    ]

    operations = [
        migrations.CreateModel(
            name='BidApplicationChange',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bidfather.BidApplication')),
            ],
        ),
        migrations.CreateModel(
            name='BidApplicationChangeType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AddField(
            model_name='bidapplicationchange',
            name='type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bidfather.BidApplicationChangeType'),
        ),
    ]

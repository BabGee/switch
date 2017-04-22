# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-02-18 15:29
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0008_productcharge_payment_method'),
        ('bridge', '0005_paymentmethod_channel'),
        ('bidfather', '0027_auto_20170125_1452'),
    ]

    operations = [
        migrations.CreateModel(
            name='BidNotification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('bid', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bidfather.Bid')),
            ],
        ),
        migrations.CreateModel(
            name='BidNotificationStatus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(max_length=45, unique=True)),
                ('description', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='BidNotificationType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(max_length=45, unique=True)),
                ('description', models.CharField(max_length=100)),
                ('notification_details', models.CharField(max_length=1920)),
                ('product_item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='crm.ProductItem')),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bridge.Service')),
            ],
        ),
        migrations.CreateModel(
            name='BidNotificationTypeStatus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(max_length=45, unique=True)),
                ('description', models.CharField(max_length=100)),
            ],
        ),
        migrations.AddField(
            model_name='bidnotificationtype',
            name='status',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bidfather.BidNotificationTypeStatus'),
        ),
        migrations.AddField(
            model_name='bidnotification',
            name='status',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bidfather.BidNotificationStatus'),
        ),
    ]

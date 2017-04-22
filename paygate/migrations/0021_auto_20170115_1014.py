# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-01-15 10:14
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('upc', '0013_auto_20170101_1749'),
        ('paygate', '0020_floatcharge_product_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='InstitutionNotification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('description', models.CharField(max_length=100)),
                ('request', models.CharField(blank=True, max_length=1920, null=True)),
                ('url', models.CharField(max_length=640)),
                ('account_id', models.CharField(blank=True, max_length=512, null=True)),
                ('username', models.CharField(blank=True, max_length=128, null=True)),
                ('password', models.CharField(blank=True, max_length=1024, null=True)),
                ('institution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='upc.Institution')),
                ('remittance_product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='paygate.RemittanceProduct')),
            ],
        ),
        migrations.AddField(
            model_name='outgoing',
            name='institution_notification',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='paygate.InstitutionNotification'),
        ),
    ]

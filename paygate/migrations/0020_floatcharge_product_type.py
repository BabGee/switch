# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-01-09 03:05
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0008_productcharge_payment_method'),
        ('paygate', '0019_remittanceproduct_show_message'),
    ]

    operations = [
        migrations.AddField(
            model_name='floatcharge',
            name='product_type',
            field=models.ManyToManyField(blank=True, to='crm.ProductType'),
        ),
    ]

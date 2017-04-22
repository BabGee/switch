# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-01-27 10:45
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0008_productcharge_payment_method'),
        ('vbs', '0032_remove_creditoverdue_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='creditoverdue',
            name='product_item',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='crm.ProductItem'),
        ),
    ]

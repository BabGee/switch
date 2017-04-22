# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-12-29 05:34
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0008_productcharge_payment_method'),
        ('bidfather', '0018_auto_20161228_0934'),
    ]

    operations = [
        migrations.CreateModel(
            name='BidInvoice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('max_price', models.DecimalField(decimal_places=2, max_digits=19)),
                ('min_price', models.DecimalField(decimal_places=2, max_digits=19)),
                ('processed', models.BooleanField(default=False)),
                ('bid', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bidfather.Bid')),
            ],
        ),
        migrations.CreateModel(
            name='BidInvoiceType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(max_length=45, unique=True)),
                ('description', models.CharField(max_length=200)),
                ('invoicing_rate', models.DecimalField(decimal_places=2, max_digits=19)),
                ('product_item', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='crm.ProductItem')),
            ],
        ),
        migrations.AddField(
            model_name='bidinvoice',
            name='bid_invoice_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bidfather.BidInvoiceType'),
        ),
    ]

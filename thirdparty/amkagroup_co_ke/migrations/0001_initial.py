# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-07-20 04:24
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('crm', '0008_productcharge_payment_method'),
    ]

    operations = [
        migrations.CreateModel(
            name='Investment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=19)),
                ('pie', models.DecimalField(decimal_places=2, max_digits=19)),
                ('balance_bf', models.DecimalField(decimal_places=2, max_digits=19)),
                ('processed', models.BooleanField(default=False)),
                ('enrollment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crm.Enrollment')),
            ],
        ),
        migrations.CreateModel(
            name='InvestmentType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(max_length=45)),
                ('description', models.CharField(max_length=100)),
                ('value', models.DecimalField(decimal_places=2, max_digits=19)),
                ('limit_review_rate', models.DecimalField(decimal_places=2, max_digits=19)),
                ('product_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crm.ProductItem')),
            ],
        ),
        migrations.AddField(
            model_name='investment',
            name='investment_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='amkagroup_co_ke.InvestmentType'),
        ),
    ]

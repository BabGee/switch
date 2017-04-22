# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-02-26 05:01
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('upc', '0001_initial'),
        ('crm', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Survey',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(max_length=45)),
                ('description', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='SurveyGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(max_length=45)),
                ('description', models.CharField(max_length=100)),
                ('data_name', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='SurveyItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(max_length=45)),
                ('description', models.CharField(max_length=100)),
                ('expiry', models.DateTimeField(blank=True, null=True)),
                ('code', models.CharField(blank=True, max_length=45, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='SurveyItemStatus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(max_length=45, unique=True)),
                ('description', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='SurveyResponse',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('transaction_reference', models.CharField(blank=True, max_length=45, null=True)),
                ('gateway_profile', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='upc.GatewayProfile')),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='survey.SurveyItem')),
            ],
        ),
        migrations.CreateModel(
            name='SurveyResponseStatus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(max_length=45, unique=True)),
                ('description', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='SurveyStatus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(max_length=45, unique=True)),
                ('description', models.CharField(max_length=100)),
            ],
        ),
        migrations.AddField(
            model_name='surveyresponse',
            name='status',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='survey.SurveyResponseStatus'),
        ),
        migrations.AddField(
            model_name='surveyitem',
            name='status',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='survey.SurveyItemStatus'),
        ),
        migrations.AddField(
            model_name='surveyitem',
            name='survey',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='survey.Survey'),
        ),
        migrations.AddField(
            model_name='survey',
            name='group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='survey.SurveyGroup'),
        ),
        migrations.AddField(
            model_name='survey',
            name='institution',
            field=models.ManyToManyField(blank=True, to='upc.Institution'),
        ),
        migrations.AddField(
            model_name='survey',
            name='product_item',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='crm.ProductItem'),
        ),
        migrations.AddField(
            model_name='survey',
            name='product_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crm.ProductType'),
        ),
        migrations.AddField(
            model_name='survey',
            name='status',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='survey.SurveyStatus'),
        ),
    ]

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
            name='Beneficiary',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('full_names', models.CharField(max_length=200)),
                ('passport_id_no', models.CharField(blank=True, max_length=45, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='CodeRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('full_names', models.CharField(blank=True, max_length=200, null=True)),
                ('phone_number', models.CharField(blank=True, max_length=20, null=True)),
                ('passport_id_no', models.CharField(blank=True, max_length=45, null=True)),
                ('code_allocation', models.IntegerField(unique=True)),
                ('code_preview', models.CharField(blank=True, max_length=320, null=True)),
                ('details_match', models.CharField(blank=True, help_text=b'Name:MemberNumber', max_length=5, null=True)),
                ('approved', models.BooleanField(default=False)),
                ('gateway_profile', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='upc.GatewayProfile')),
            ],
        ),
        migrations.CreateModel(
            name='CodeRequestType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(max_length=45, unique=True)),
                ('description', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Member',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('full_names', models.CharField(max_length=200)),
                ('address', models.CharField(blank=True, max_length=100, null=True)),
                ('town', models.CharField(blank=True, max_length=100, null=True)),
                ('email', models.CharField(blank=True, max_length=100, null=True)),
                ('member_number', models.CharField(max_length=100)),
                ('phone_number', models.CharField(blank=True, max_length=100, null=True)),
                ('alt_phone_number', models.CharField(blank=True, max_length=100, null=True)),
                ('bank_name', models.CharField(blank=True, max_length=100, null=True)),
                ('bank_branch', models.CharField(blank=True, max_length=100, null=True)),
                ('bank_account_no', models.CharField(blank=True, max_length=100, null=True)),
                ('ipi_number', models.CharField(blank=True, max_length=100, null=True)),
                ('details', models.CharField(blank=True, max_length=1280, null=True)),
                ('enrollment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crm.Enrollment')),
            ],
        ),
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(max_length=45, unique=True)),
                ('description', models.CharField(max_length=100)),
            ],
        ),
        migrations.AddField(
            model_name='coderequest',
            name='region',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='mcsk.Region'),
        ),
        migrations.AddField(
            model_name='coderequest',
            name='request_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mcsk.CodeRequestType'),
        ),
        migrations.AddField(
            model_name='beneficiary',
            name='member',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mcsk.Member'),
        ),
    ]

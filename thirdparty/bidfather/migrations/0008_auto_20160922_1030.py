# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-09-22 10:30
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bidfather', '0007_auto_20160922_0140'),
    ]

    operations = [
        migrations.RenameField(
            model_name='bidapplication',
            old_name='awarded_points',
            new_name='bid_rank',
        ),
        migrations.RemoveField(
            model_name='bidapplication',
            name='self_assesed_points',
        ),
        migrations.RemoveField(
            model_name='bidrequirementapplication',
            name='awarded_points',
        ),
        migrations.RemoveField(
            model_name='bidrequirementapplication',
            name='self_assesed_points',
        ),
        migrations.AddField(
            model_name='bidapplication',
            name='quantity',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=19),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='bidapplication',
            name='unit_price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=19),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='bidrequirementapplication',
            name='quantity',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=19),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='bidrequirementapplication',
            name='unit_price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=19),
            preserve_default=False,
        ),
    ]

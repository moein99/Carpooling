# Generated by Django 2.2.2 on 2019-07-30 11:19

import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('group', '0002_auto_20190728_0907'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='group',
            name='source_lat',
        ),
        migrations.RemoveField(
            model_name='group',
            name='source_lon',
        ),
        migrations.AddField(
            model_name='group',
            name='source',
            field=django.contrib.gis.db.models.fields.PointField(null=True, srid=4326),
        ),
    ]

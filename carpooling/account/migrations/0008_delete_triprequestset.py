# Generated by Django 2.2.2 on 2019-08-07 13:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('trip', '0009_auto_20190807_1325'),
        ('account', '0007_triprequestset_title'),
    ]

    operations = [
        migrations.DeleteModel(
            name='TripRequestSet',
        ),
    ]
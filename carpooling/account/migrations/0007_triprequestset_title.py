# Generated by Django 2.2.2 on 2019-08-07 06:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0006_auto_20190806_1126'),
    ]

    operations = [
        migrations.AddField(
            model_name='triprequestset',
            name='title',
            field=models.CharField(max_length=50, null=True),
        ),
    ]

# Generated by Django 2.2.2 on 2019-08-12 07:33

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('trip', '0009_auto_20190807_1325'),
    ]

    operations = [
        migrations.AddField(
            model_name='triprequestset',
            name='creation_time',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]

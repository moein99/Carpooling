# Generated by Django 2.2.2 on 2019-08-18 14:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trip', '0013_vote'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trip',
            name='playlist_id',
            field=models.CharField(max_length=22, null=True),
        ),
        migrations.AlterField(
            model_name='trip',
            name='status',
            field=models.CharField(choices=[('wa', 'waiting'), ('cl', 'closed'), ('in', 'in route'), ('dn', 'done'), ('ca', 'canceled')], max_length=2),
        ),
    ]

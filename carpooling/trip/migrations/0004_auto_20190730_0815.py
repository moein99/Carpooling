# Generated by Django 2.2.2 on 2019-07-30 08:15

from django.conf import settings
import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('group', '0002_auto_20190728_0907'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('trip', '0003_auto_20190728_0916'),
    ]

    operations = [
        migrations.RenameField(
            model_name='trip',
            old_name='driver',
            new_name='car_provider',
        ),
        migrations.RemoveField(
            model_name='trip',
            name='destination_lat',
        ),
        migrations.RemoveField(
            model_name='trip',
            name='destination_lon',
        ),
        migrations.RemoveField(
            model_name='trip',
            name='source_lat',
        ),
        migrations.RemoveField(
            model_name='trip',
            name='source_lon',
        ),
        migrations.AddField(
            model_name='companionship',
            name='destination',
            field=django.contrib.gis.db.models.fields.PointField(default=None, srid=4326),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='companionship',
            name='source',
            field=django.contrib.gis.db.models.fields.PointField(default=None, srid=4326),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='trip',
            name='destination',
            field=django.contrib.gis.db.models.fields.PointField(default=None, srid=4326),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='trip',
            name='end_estimation',
            field=models.DateTimeField(default=None),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='trip',
            name='source',
            field=django.contrib.gis.db.models.fields.PointField(default=None, srid=4326),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='trip',
            name='start_estimation',
            field=models.DateTimeField(default=None),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='trip',
            name='status',
            field=models.CharField(choices=[('wa', 'waiting'), ('cl', 'closed'), ('in', 'in route'), ('dn', 'done')], max_length=2),
        ),
        migrations.CreateModel(
            name='TripRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('destination', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('applicant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('trip', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='trip.Trip')),
            ],
        ),
        migrations.CreateModel(
            name='TripGroups',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='group.Group')),
                ('trip', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='trip.Trip')),
            ],
        ),
        migrations.AddField(
            model_name='trip',
            name='groups',
            field=models.ManyToManyField(through='trip.TripGroups', to='group.Group'),
        ),
        migrations.AddField(
            model_name='trip',
            name='requests',
            field=models.ManyToManyField(related_name='requests', through='trip.TripRequest', to=settings.AUTH_USER_MODEL),
        ),
    ]

# Generated by Django 2.2.2 on 2019-07-28 09:07

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('trip', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='trip',
            name='capacity',
            field=models.PositiveSmallIntegerField(default=None, validators=[django.core.validators.MaxValueValidator(20)]),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='trip',
            name='driver',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='trip',
            name='status',
            field=models.CharField(choices=[('wa', 'waiting'), ('in', 'in route'), ('dn', 'done')], default=None, max_length=2),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name='Companionship',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('trip', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='trip.Trip')),
            ],
        ),
    ]

# Generated by Django 2.0.6 on 2018-07-27 16:03

import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('medications', '0028_state_geometry'),
    ]

    operations = [
        migrations.AlterField(
            model_name='state',
            name='geometry',
            field=django.contrib.gis.db.models.fields.GeometryField(null=True, srid=4326, verbose_name='geometry'),
        ),
    ]

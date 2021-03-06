# Generated by Django 2.0.6 on 2018-09-12 13:22

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('medications', '0047_auto_20180828_1258'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='providermedicationthrough',
            name='date',
        ),
        migrations.AddField(
            model_name='providermedicationthrough',
            name='creation_date',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, help_text='Creation date', verbose_name='creation date'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='providermedicationthrough',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, help_text='Last modification date', verbose_name='last modified date'),
        ),
    ]

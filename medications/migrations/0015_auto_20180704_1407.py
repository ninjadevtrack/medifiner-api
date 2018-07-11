# Generated by Django 2.0.6 on 2018-07-04 14:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('medications', '0014_auto_20180704_0953'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='existingmedication',
            name='name',
        ),
        migrations.AddField(
            model_name='existingmedication',
            name='description',
            field=models.TextField(blank=True, verbose_name='medication description'),
        ),
    ]
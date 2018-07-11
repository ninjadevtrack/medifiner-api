# Generated by Django 2.0.6 on 2018-07-09 13:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('medications', '0017_merge_20180706_1312'),
    ]

    operations = [
        migrations.AddField(
            model_name='provider',
            name='type',
            field=models.CharField(choices=[('re', 'Community/Retail'), ('cl', 'Clinic'), ('co', 'Compounding')], default='re', max_length=2, verbose_name='provider type'),
        ),
    ]

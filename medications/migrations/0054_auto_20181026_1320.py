# Generated by Django 2.0.6 on 2018-10-26 13:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('medications', '0053_remove_organization_user'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='providermedicationndcthrough',
            index=models.Index(fields=['provider_id', 'medication_ndc_id', 'latest'], name='medications_provide_051c7f_idx'),
        ),
    ]
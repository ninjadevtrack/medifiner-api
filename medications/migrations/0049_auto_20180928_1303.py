# Generated by Django 2.0.6 on 2018-09-28 13:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('medications', '0048_auto_20180912_1322'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ProviderMedicationThrough',
            new_name='ProviderMedicationNdcThrough',
        ),
        migrations.CreateModel(
            name='MedicationNdc',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ndc', models.CharField(max_length=32, unique=True, verbose_name='national drug code')),
            ],
            options={
                'verbose_name': 'medication NDC',
                'verbose_name_plural': 'medication NDCs',
            },
        ),
        migrations.RemoveField(
            model_name='medication',
            name='ndc',
        ),
        migrations.RemoveField(
            model_name='providermedicationndcthrough',
            name='medication',
        ),
        migrations.AddField(
            model_name='medicationndc',
            name='medication',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ndc_codes', to='medications.Medication'),
        ),
        migrations.AddField(
            model_name='providermedicationndcthrough',
            name='medication_ndc',
            field=models.ForeignKey(null=True, default=None, on_delete=django.db.models.deletion.CASCADE, related_name='provider_medication', to='medications.MedicationNdc'),
            preserve_default=False,
        ),
    ]

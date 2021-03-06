# Generated by Django 2.0.6 on 2018-08-09 09:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('medications', '0039_remove_provider_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='provider',
            name='type',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='providers', to='medications.ProviderType'),
        ),
    ]

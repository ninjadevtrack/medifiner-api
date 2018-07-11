# Generated by Django 2.0.6 on 2018-06-25 13:16

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contact_name', models.CharField(blank=True, max_length=255, verbose_name='contact name')),
                ('organization_name', models.CharField(max_length=255, verbose_name='organization name')),
                ('phone', phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, verbose_name='phone')),
                ('website', models.URLField(blank=True, max_length=255, verbose_name='website')),
                ('registration_date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='registration_date')),
                ('user', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='organization', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'organization',
                'verbose_name_plural': 'organizations',
            },
        ),
    ]
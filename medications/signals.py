from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ProviderMedicationThrough
from .tasks import handle_provider_medication_through_post_save_signal


@receiver(post_save, sender=ProviderMedicationThrough)
def provider_medication_through_post_save(sender, instance, **kwargs):
    # Signal that catches the object created by the celery task
    # generate medications. The task that handles the post_save process
    # has to be triggered on_commit because we have to wait until the object
    # is created.
    transaction.on_commit(
        lambda:
        handle_provider_medication_through_post_save_signal.apply_async(
            args=(instance.pk, instance.provider.pk, instance.medication.pk),
            queue='signals',
        )
    )

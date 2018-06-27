from celery import shared_task
from django.db import transaction


@shared_task
@transaction.atomic
def generate_medications(organization_id):
	pass
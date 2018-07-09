import factory
from .models import (
    Organization,
    Provider,
    Medication,
    ExistingMedication,
    ProviderMedicationThrough,
)


class OrganizationFactory(factory.DjangoModelFactory):
    """
        Define Organization Factory
    """
    class Meta:
        model = Organization


class ProviderFactory(factory.DjangoModelFactory):
    """
        Define Provider Factory
    """
    class Meta:
        model = Provider


class MedicationFactory(factory.DjangoModelFactory):
    """
        Define Medication Factory
    """
    class Meta:
        model = Medication


class ExistingMedicationFactory(factory.DjangoModelFactory):
    """
        Define ExistingMedication Factory
    """
    class Meta:
        model = ExistingMedication


class ProviderMedicationThroughFactory(factory.DjangoModelFactory):
    """
        Define ProviderMedicationThrough Factory
    """
    class Meta:
        model = ProviderMedicationThrough

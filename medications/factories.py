import factory
from .models import (
    Organization,
    Provider,
    Medication,
    ExistingMedication,
    ProviderMedicationThrough,
    State,
    ZipCode,
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


class StateFactory(factory.DjangoModelFactory):
    """
        Define State Factory
    """
    class Meta:
        model = State


class ZipCodeFactory(factory.DjangoModelFactory):
    """
        Define ZipCode Factory
    """
    class Meta:
        model = ZipCode

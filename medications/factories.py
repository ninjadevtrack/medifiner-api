import factory
from .models import (
    County,
    ExistingMedication,
    Medication,
    MedicationName,
    MedicationNdc,
    Organization,
    Provider,
    ProviderMedicationNdcThrough,
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
        Define ProviderMedicationNdcThrough Factory
    """
    class Meta:
        model = ProviderMedicationNdcThrough


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


class CountyFactory(factory.DjangoModelFactory):
    """
        Define County Factory
    """
    class Meta:
        model = County


class MedicationNameFactory(factory.DjangoModelFactory):
    """
        Define MedicationName Factory
    """
    class Meta:
        model = MedicationName


class MedicationNDCFactory(factory.DjangoModelFactory):
    """
        Define MedicationNDC Factory
    """
    class Meta:
        model = MedicationNdc

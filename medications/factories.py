import factory
from .models import Organization, Provider


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

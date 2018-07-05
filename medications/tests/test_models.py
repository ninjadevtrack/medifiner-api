import pytest
from medications.factories import OrganizationFactory


@pytest.mark.django_db
def test_organization_model(django_user_model):
    """ Test organization model """
    user = django_user_model.objects.create(
        email='example@example.com',
        password='secretkey',
    )
    organization_name = 'Test Organization'
    organization = OrganizationFactory(
        user=user,
        organization_name=organization_name,

    )
    assert organization.organization_name == organization_name
    assert str(organization) == organization_name

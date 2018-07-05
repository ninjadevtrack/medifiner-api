import pytest

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from medications.factories import OrganizationFactory

pytestmark = pytest.mark.django_db()
ORGANIZATION_NAME = 'Test Organization'


class TestOrganization: 
    """ Test organization model """

    def test_str(self):
        organization = OrganizationFactory(
            organization_name=ORGANIZATION_NAME,

        )
        assert organization.organization_name == ORGANIZATION_NAME
        assert str(organization) == ORGANIZATION_NAME

    def test_user(self, django_user_model):
        user = django_user_model.objects.create(
            email='example@example.com',
            password='secretkey',
        )
        organization = OrganizationFactory(
            user=user,
            organization_name=ORGANIZATION_NAME,
        )
        assert isinstance(organization.user, get_user_model())

    def test_phone(self):
        # Test that only US phone are valid
        organization_incorrect_phone = OrganizationFactory(
            organization_name=ORGANIZATION_NAME,
            phone='666-666-666'
        )
        organization_correct_phone = OrganizationFactory(
            organization_name=ORGANIZATION_NAME,
            phone='202-555-0178'
        )
        assert not organization_incorrect_phone.phone.is_valid()
        assert organization_correct_phone.phone.is_valid()

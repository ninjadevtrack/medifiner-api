import pytest
import factory

from django.utils import timezone
from django.db.utils import DataError, IntegrityError
from django.contrib.auth import get_user_model
from medications.factories import OrganizationFactory

pytestmark = pytest.mark.django_db()
ORGANIZATION_NAME = 'Test organization'


@pytest.fixture()
def long_str():
    return factory.Faker(
        'pystr',
        min_chars=256,
        max_chars=256,
    )


class TestOrganization: 
    """ Test organization model """

    def test_str(self):
        organization = OrganizationFactory(
            organization_name=ORGANIZATION_NAME,

        )
        assert organization.organization_name == ORGANIZATION_NAME
        assert str(organization) == ORGANIZATION_NAME

    def test_no_organization_name(self):
        with pytest.raises(IntegrityError):
            OrganizationFactory()

    def test_user(self, django_user_model):
        user = django_user_model.objects.create(
            email=factory.Faker('email'),
            password=factory.Faker('password'),
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

    def test_registration_date(self):
        now = timezone.now()
        organization = OrganizationFactory(
            organization_name=ORGANIZATION_NAME,
        )
        assert now <= organization.registration_date

    def test_organization_name_max_lenght(self, long_str):
        with pytest.raises(DataError):
            OrganizationFactory(
                organization_name=long_str,
            )

    def test_contact_name_max_lenght(self, long_str):
        with pytest.raises(DataError):
            OrganizationFactory(
                contact_name=long_str,
            )

    def test_website_name_max_lenght(self, long_str):
        with pytest.raises(DataError):
            OrganizationFactory(
                website=long_str,
            )

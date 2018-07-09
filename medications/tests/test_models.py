import pytest
import factory

from random import randint, randrange

from django.utils import timezone
from django.db.utils import DataError, IntegrityError
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from localflavor.us.us_states import STATE_CHOICES

from medications.factories import (
    OrganizationFactory,
    ProviderFactory,
    MedicationFactory,
    ExistingMedicationFactory,
    ProviderMedicationThroughFactory,
)
from medications.models import (
    Organization,
    ExistingMedication,
    ProviderMedicationThrough,
)

pytestmark = pytest.mark.django_db()
ORGANIZATION_NAME = 'Test organization'
TEST_NDC = '0002-1433-80'
# Real address information to generate lat and lng, cannot trust in Faker
# cause sometimes it generates addresses that googlemap api cannot convert
# to real coordinates.
REAL_STREET = '833  School Street'
REAL_CITY = 'New Haven'
REAL_STATE = 'CT'


@pytest.fixture()
def long_str():
    return factory.Faker(
        'pystr',
        min_chars=256,
        max_chars=256,
    ).generate({})


@pytest.fixture()
def short_str():
    return factory.Faker(
        'pystr',
        min_chars=30,
        max_chars=30,
    ).generate({})


@pytest.fixture()
def medication():
    return MedicationFactory(
        name=factory.Faker('word'),
    )


@pytest.fixture()
def provider():
    return ProviderFactory(
        name=factory.Faker('word'),
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


class TestProvider:
    """ Test provider model """

    def test_str_with_provider_name(self):
        name = 'test provider'
        store_number = randint(1, 100)
        provider = ProviderFactory(
            name=name,
            store_number=store_number,
        )
        obj_str = '{} - store number: {}'.format(
            name,
            store_number,
        )
        assert provider.name == name
        assert provider.store_number == store_number
        assert str(provider) == obj_str

    def test_str_with_no_provider_name(self):
        name = ''  # This is the DB default if not supplied
        store_number = randint(1, 100)
        provider = ProviderFactory(
            store_number=store_number,
        )
        obj_str = '{} - store number: {}'.format(
            name if name else 'provider',
            store_number,
        )
        assert provider.name == name
        assert provider.store_number == store_number
        assert str(provider) == obj_str

    def test_coordinates_being_generated(self):
        provider = ProviderFactory(
            address=REAL_STREET,
            city=REAL_CITY,
            state=REAL_STATE,
        )
        assert provider.lng and provider.lat

    def test_name_max_lenght(self, long_str):
        with pytest.raises(DataError):
            ProviderFactory(
                name=long_str,
            )

    def test_address_max_lenght(self, long_str):
        with pytest.raises(DataError):
            ProviderFactory(
                address=long_str,
            )

    def test_website_max_lenght(self, long_str):
        with pytest.raises(DataError):
            ProviderFactory(
                website=long_str,
            )

    def test_operating_hours_max_lenght(self, long_str):
        with pytest.raises(DataError):
            ProviderFactory(
                operating_hours=long_str,
            )

    def test_unique_provider_email(self):
        email = 'example@example.com'
        with pytest.raises(IntegrityError):
            for _ in range(2):
                ProviderFactory(
                    email=email,
                )

    def test_coordenates_change_in_new_address(self):
        #  Create the provider and get its coordinates
        provider = ProviderFactory(
            address=REAL_STREET,
            city=REAL_CITY,
            state=REAL_STATE,
        )
        lat, lng = provider.lat, provider.lng
        #  Change the provider address and check the change coordinates bool
        provider.address = '2802  West Fork Street'
        provider.change_coordinates = True
        provider.save()
        lat_2, lng_2 = provider.lat, provider.lng

        #  Now assert that coordinates are different and check that the flag
        # 'change_coordinates' is back to False (it should)
        assert lat != lat_2 and lng != lng_2
        assert not provider.change_coordinates

    def test_phone(self):
        # Test that only US phone are valid
        provider_incorrect_phone = ProviderFactory(
            phone='666-666-666'
        )
        provider_correct_phone = ProviderFactory(
            phone='202-555-0178'
        )
        assert not provider_incorrect_phone.phone.is_valid()
        assert provider_correct_phone.phone.is_valid()

    def test_US_wrong_state(self):
        states_list = [code[0] for code in STATE_CHOICES]
        fake_state = factory.Faker(
            'pystr'
        ).generate({'min_chars': 2, 'max_chars': 2})
        while fake_state in states_list:
            fake_state = factory.Faker(
                'pystr'
            ).generate({'min_chars': 2, 'max_chars': 2})
        # with pytest.raises(ValidationError):
        organization = OrganizationFactory(
            organization_name=ORGANIZATION_NAME,
        )
        with pytest.raises(ValidationError):
            provider = ProviderFactory(
                organization=organization,
                name=factory.Faker('name'),
                address=factory.Faker('address'),
                city=factory.Faker('city'),
                state=fake_state,
                zip=randint(10000, 99999),
                phone='202-555-0178',
                email=factory.Faker('email'),
            )
            provider.full_clean()

    def test_state_lenght(self):
        with pytest.raises(DataError):
            ProviderFactory(
                state=factory.Faker('pystr', min_chars=3),
            )

    def test_zip_code_invalid(self):
        organization = OrganizationFactory(
            organization_name=ORGANIZATION_NAME,
        )
        with pytest.raises(ValidationError):
            provider = ProviderFactory(
                organization=organization,
                name=factory.Faker('name'),
                address=REAL_STREET,
                city=REAL_CITY,
                state=REAL_STATE,
                zip=f'{randrange(1, 10**4):04}',
                phone='202-555-0178',
                email=factory.Faker('email'),
            )
            provider.full_clean()

    def test_zip_code_valid(self):
        organization = OrganizationFactory(
            organization_name=ORGANIZATION_NAME,
        )
        provider = ProviderFactory(
            organization=organization,
            name=factory.Faker('name'),
            address=REAL_STREET,
            city=REAL_CITY,
            state=REAL_STATE,
            zip=f'{randrange(1, 10**5):05}',
            phone='202-555-0178',
            email=factory.Faker('email'),
        )
        provider.full_clean()


class TestMedication:
    """ Test medication model """

    def test_str(self):
        medication_name = factory.Faker('word').generate({})
        medication = MedicationFactory(
            name=medication_name,
        )
        assert medication.name == medication_name
        assert str(medication) == medication_name

    def test_name_max_lenght(self, long_str):
        with pytest.raises(DataError):
            MedicationFactory(
                name=long_str,
            )

    def test_ndc_max_lenght(self, long_str):
        with pytest.raises(DataError):
            MedicationFactory(
                ndc=long_str,
            )

    def test_name_exists(self):
        medication = MedicationFactory(
            ndc=TEST_NDC,
        )
        with pytest.raises(ValidationError):
            medication.full_clean()

    def test_ndc_exists(self):
        medication = MedicationFactory(
            name=factory.Faker('word'),
        )
        with pytest.raises(ValidationError):
            medication.full_clean()

    def test_ndc_unique(self):
        with pytest.raises(IntegrityError):
            for _ in range(2):
                MedicationFactory(
                    ndc=TEST_NDC,
                )

    def test_ndc_exists(self):
        ExistingMedicationFactory(ndc=TEST_NDC)
        medication = MedicationFactory(
            ndc=TEST_NDC,
        )
        existing_ndcs = ExistingMedication.objects.values_list(
            'ndc',
            flat=True,
        )
        assert medication.ndc in existing_ndcs


class TestExistingMedication:
    """ Test existing medication model """

    def test_str(self):
        medication = ExistingMedicationFactory(
            ndc=TEST_NDC,
        )
        assert medication.ndc == TEST_NDC
        assert str(medication) == TEST_NDC

    def test_ndc_max_lenght(self, long_str):
        with pytest.raises(DataError):
            ExistingMedicationFactory(
                ndc=long_str,
            )

    def test_ndc_exists(self):
        medication = ExistingMedicationFactory()
        with pytest.raises(ValidationError):
            medication.full_clean()

    def test_import_date(self):
        now = timezone.now()
        medication = ExistingMedicationFactory(
            ndc=TEST_NDC,
        )
        assert now <= medication.import_date


class TestProviderMedicationThrough:
    """
    Test ProviderMedicationThrough model.
    While testing provider_medication_through == pmt for short.
    """

    def test_str(self):
        medication_name = factory.Faker('word').generate({})
        provider_name = factory.Faker('word').generate({})

        medication = MedicationFactory(
            name=medication_name,
        )
        provider = ProviderFactory(
            name=provider_name,
        )
        pmt = ProviderMedicationThroughFactory(
            provider=provider,
            medication=medication,
        )
        provider_medication_str = '{} - store number: {} - {}'.format(
            provider_name,
            provider.store_number,
            medication_name,
        )
        assert str(pmt) == provider_medication_str

    def test_level_not_editable_after_save(self, medication, provider):
        pmt = ProviderMedicationThrough.objects.create(
            level=randint(1, 100),
            medication=medication,
            provider=provider,
        )
        assert pmt.level == 0

    def test_supply_level_mapping(self, medication, provider):
        supply_to_level_map = {
            '<24': 1,
            '24': 2,
            '24-48': 3,
            '>48': 4,
        }
        for supply, level in supply_to_level_map.items():
            pmt = ProviderMedicationThrough.objects.create(
                supply=supply,
                medication=medication,
                provider=provider,
            )
            assert pmt.level == level

    def test_incorrect_supply_string_makes_level_0(
        self,
        medication,
        provider,
        short_str,
    ):
        pmt = ProviderMedicationThrough.objects.create(
            supply=short_str,
            medication=medication,
            provider=provider,
        )
        assert pmt.level == 0

    def test_supply_max_lenght(self, provider, medication, long_str):
        with pytest.raises(DataError):
            ProviderMedicationThroughFactory(
                supply=long_str,
                provider=provider,
                medication=medication,
            )

    def test_date(self, provider, medication):
        now = timezone.now()
        pmt = ProviderMedicationThroughFactory(
            provider=provider,
            medication=medication,
        )
        assert now <= pmt.date

    def test_provider_exists(self, medication):
        with pytest.raises(IntegrityError):
            ProviderMedicationThroughFactory(
                medication=medication,
            )

    def test_medication_exists(self, provider):
        with pytest.raises(IntegrityError):
            ProviderMedicationThroughFactory(
                provider=provider,
            )

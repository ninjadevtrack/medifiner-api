import os
import pytest
import csv
import json

from random import randint, randrange

from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from django.utils.translation import ugettext_lazy as _

from celery.task.control import inspect
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from medications.models import Organization, MedicationName, State
from medications.constants import field_rows
from medications.factories import (
    OrganizationFactory,
    ProviderFactory,
    MedicationFactory,
    ExistingMedicationFactory,
    ProviderMedicationNdcThroughFactory,
    StateFactory,
    ZipCodeFactory,
    CountyFactory,
    MedicationNameFactory,
)

pytestmark = pytest.mark.django_db()
User = get_user_model()


@pytest.fixture()
def organization():
    return Organization.objects.create(
        organization_name='test organization',
    )


@pytest.fixture()
def testuser(organization):
    email = 'mattpike@sleep.com'
    password = 'password'
    user = User.objects.create_user(
        email,
        password,
    )
    organization.user = user
    organization.save()
    return user


@pytest.fixture()
def user_no_organization():
    email = 'alciseneros@sleep.com'
    password = 'password'
    user = User.objects.create_user(
        email,
        password,
    )
    return user


@pytest.fixture()
def geographic_object():
    return GEOSGeometry(
        json.dumps(
            settings.GEOJSON_GEOGRAPHIC_CONTINENTAL_CENTER_US
        )
    )


class TestTokenAuth:
    """Token authentication"""
    token_model = Token
    path = '/api/v1/medications/csv_import'
    header_prefix = 'Token '

    @pytest.fixture(autouse=True)
    def setup_stuff(self, db, testuser):
        self.factory = APIClient()
        self.user = testuser

        self.key = 'abcd1234'
        self.token = self.token_model.objects.create(
            key=self.key,
            user=self.user,
        )

    def test_post_form_passing_token_auth(self):
        """
        Ensure POSTing json over token auth with correct
        credentials passes
        """
        with open('temporal.csv', 'w+', newline='') as csv_file:
            filewriter = csv.writer(
                csv_file,
                delimiter=',',
                quotechar='|',
                quoting=csv.QUOTE_MINIMAL,
            )
            filewriter.writerow(field_rows)
            csv_file.seek(0)
            auth = self.header_prefix + self.key
            response = self.factory.post(
                self.path, {'csv_file': csv_file}, HTTP_AUTHORIZATION=auth
            )
            assert response.status_code == status.HTTP_200_OK

    def test_fail_authentication_if_user_is_not_active(
        self,
    ):
        user = User.objects.create_user('bar', 'baz')
        user.is_active = False
        user.save()
        self.token_model.objects.create(key='foobar_token', user=user)
        response = self.factory.post(
            self.path, {'example': 'example'},
            HTTP_AUTHORIZATION=self.header_prefix + 'foobar_token'
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_fail_post_form_passing_nonexistent_token_auth(self):
        # use a nonexistent token key
        auth = self.header_prefix + 'wxyz6789'
        response = self.factory.post(
            self.path, {'example': 'example'}, HTTP_AUTHORIZATION=auth
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_fail_post_if_token_is_missing(self):
        response = self.factory.post(
            self.path, {'example': 'example'},
            HTTP_AUTHORIZATION=self.header_prefix)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_fail_post_if_token_contains_spaces(self):
        response = self.factory.post(
            self.path, {'example': 'example'},
            HTTP_AUTHORIZATION=self.header_prefix + 'foo bar'
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_fail_post_form_passing_invalid_token_auth(self):
        # add an 'invalid' unicode character
        auth = self.header_prefix + self.key + "¸"
        response = self.factory.post(
            self.path, {'example': 'example'}, HTTP_AUTHORIZATION=auth
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_post_form_failing_token_auth(self):
        """
        Ensure POSTing form over token auth without correct credentials fails
        """
        response = self.factory.post(self.path, {'example': 'example'})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_post_json_failing_token_auth(self):
        """
        Ensure POSTing json over token auth without correct credentials fails
        """
        response = self.factory.post(
            self.path, {'example': 'example'}, format='json'
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @classmethod
    def teardown_class(cls):
        os.remove('temporal.csv')


class TestMedicationsPOSTView:
    token_model = Token
    path = '/api/v1/medications/csv_import'
    header_prefix = 'Token '

    @pytest.fixture(autouse=True)
    def setup_stuff(self, db, testuser):
        self.factory = APIClient()
        self.user = testuser

        self.key = 'abcd1234'
        self.token = self.token_model.objects.create(
            key=self.key,
            user=self.user,
        )

    def test_post_with_correct_data(self):
        """
        Ensure POSTing correct csv file returns status 200
        """
        with open('temporal.csv', 'w+', newline='') as csv_file:
            filewriter = csv.writer(
                csv_file,
                delimiter=',',
                quotechar='|',
                quoting=csv.QUOTE_MINIMAL,
            )
            filewriter.writerow(field_rows)
            csv_file.seek(0)
            auth = self.header_prefix + self.key
            response = self.factory.post(
                self.path, {'csv_file': csv_file}, HTTP_AUTHORIZATION=auth
            )
            assert response.status_code == status.HTTP_200_OK

    def test_post_with_user_without_organization(self, user_no_organization):
        """
        Ensure POSTing with user without organization is bad request
        """
        msg = _('This user has not organization related.')
        key = 'atyd5678'
        self.token_model.objects.create(
            key=key,
            user=user_no_organization,
        )
        with open('temporal.csv', 'w+', newline='') as csv_file:
            filewriter = csv.writer(
                csv_file,
                delimiter=',',
                quotechar='|',
                quoting=csv.QUOTE_MINIMAL,
            )
            filewriter.writerow(field_rows)
            csv_file.seek(0)
            auth = self.header_prefix + key
            response = self.factory.post(
                self.path, {'csv_file': csv_file}, HTTP_AUTHORIZATION=auth
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert len(response.data['csv_file']) == 1
            assert response.data['csv_file'][0] == msg

    def test_post_wrong_file_extension(self):
        """
        Ensure POSTing with wrong file extension is bad request
        """
        msg = _('Unknown CSV format')
        with open('temporal_2.txt', 'w+', newline='') as csv_file:
            filewriter = csv.writer(
                csv_file,
                delimiter=',',
                quotechar='|',
                quoting=csv.QUOTE_MINIMAL,
            )
            filewriter.writerow(field_rows)
            csv_file.seek(0)
            auth = self.header_prefix + self.key
            response = self.factory.post(
                self.path, {'csv_file': csv_file}, HTTP_AUTHORIZATION=auth
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert len(response.data['csv_file']) == 1
            assert response.data['csv_file'][0] == msg

    def test_post_with_wrong_headers_csv(self):
        """
        Ensure POSTing csv with wrong headers is bad request
        """
        msg = _(
            'Wrong headers in CSV file, headers must be: {}.'
        ). format(
            ', '.join(field_rows)
        )
        with open('temporal.csv', 'w+', newline='') as csv_file:
            filewriter = csv.writer(
                csv_file,
                delimiter=',',
                quotechar='|',
                quoting=csv.QUOTE_MINIMAL,
            )
            filewriter.writerow(['Spam'] * 5 + ['Baked Beans'])
            csv_file.seek(0)
            auth = self.header_prefix + self.key
            response = self.factory.post(
                self.path, {'csv_file': csv_file}, HTTP_AUTHORIZATION=auth
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert len(response.data['csv_file']) == 1
            assert response.data['csv_file'][0] == msg

    @classmethod
    def teardown_class(cls):
        os.remove('temporal.csv')
        os.remove('temporal_2.txt')


class TestMedicationNamesGETView:
    token_model = Token
    path = '/api/v1/medications/names/'
    header_prefix = 'Token '

    @pytest.fixture(autouse=True)
    def setup_stuff(self, db, testuser):
        self.factory = APIClient()
        self.user = testuser

        self.key = 'abcd1234'
        self.token = self.token_model.objects.create(
            key=self.key,
            user=self.user,
        )

    def test_get_medications_with_token_success(self):
        auth = self.header_prefix + self.key
        response = self.factory.get(
            self.path, HTTP_AUTHORIZATION=auth
        )
        assert response.status_code == status.HTTP_200_OK

    def test_get_medications_without_token_unsuccess(self):
        response = self.factory.get(
            self.path
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_correct_number_medications(self):
        MedicationName.objects.create()
        medication_names_number = MedicationName.objects.all().count()
        auth = self.header_prefix + self.key
        response = self.factory.get(
            self.path, HTTP_AUTHORIZATION=auth
        )
        assert medication_names_number == len(response.json())


class TestStatesGETView:
    token_model = Token
    path = '/api/v1/medications/states/'
    header_prefix = 'Token '

    @pytest.fixture(autouse=True)
    def setup_stuff(self, db, testuser):
        self.factory = APIClient()
        self.user = testuser

        self.key = 'abcd1234'
        self.token = self.token_model.objects.create(
            key=self.key,
            user=self.user,
        )

    def test_get_states_with_token_success(self):
        auth = self.header_prefix + self.key
        response = self.factory.get(
            self.path, HTTP_AUTHORIZATION=auth
        )
        assert response.status_code == status.HTTP_200_OK

    def test_get_states_without_token_unsuccess(self):
        response = self.factory.get(
            self.path
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_correct_number_states(self):
        State.objects.create()
        states_number = State.objects.all().count()
        auth = self.header_prefix + self.key
        response = self.factory.get(
            self.path, HTTP_AUTHORIZATION=auth
        )
        assert states_number == len(response.json())


class TestGenerateMedicationTaskTriggered:
    token_model = Token
    path = '/api/v1/medications/csv_import'
    header_prefix = 'Token '

    @pytest.fixture(autouse=True)
    def setup_stuff(self, db, testuser):
        self.factory = APIClient()
        self.user = testuser

        self.key = 'abcd1234'
        self.token = self.token_model.objects.create(
            key=self.key,
            user=self.user,
        )

    def test_post_triggers_generate_medications_task(self):
        """
        Ensure POSTing correct csv file triggers generate_medications task.
        This test has a workaround due to I was unable to find a easier way
        to check if the pertinent task was triggerd. First I check in the
        celery queue the task that it is supossed to be triggered and get
        how many times it has been run. After making a request to a view
        that triggers the task I search again for the total of runs of this
        task. If every works as it should there should be 1 run more.
        TODO: Search a better way to do this.
        """
        pre_celery_stats = inspect().stats()
        pre_celery_key = [key for key in pre_celery_stats.keys()][0]
        pre_task_count = pre_celery_stats.get(
            pre_celery_key
        ).get(
            'total'
        ).get(
            'medications.tasks.generate_medications'
        )
        with open('temporal.csv', 'w+', newline='') as csv_file:
            filewriter = csv.writer(
                csv_file,
                delimiter=',',
                quotechar='|',
                quoting=csv.QUOTE_MINIMAL,
            )
            filewriter.writerow(field_rows)
            csv_file.seek(0)
            auth = self.header_prefix + self.key
            self.factory.post(
                self.path, {'csv_file': csv_file}, HTTP_AUTHORIZATION=auth
            )
            post_celery_stats = inspect().stats()
            post_celery_key = [key for key in post_celery_stats.keys()][0]
            post_task_count = post_celery_stats.get(
                post_celery_key
            ).get(
                'total'
            ).get(
                'medications.tasks.generate_medications'
            )
            assert pre_task_count + 1 == post_task_count

    @classmethod
    def teardown_class(cls):
        os.remove('temporal.csv')


class TestGeoStatsStateGETView:
    token_model = Token
    path = '/api/v1/medications/geo_stats'
    header_prefix = 'Token '

    @pytest.fixture(autouse=True)
    def setup_stuff(self, db, testuser):
        self.factory = APIClient()
        self.user = testuser

        self.key = 'abcd1234'
        self.token = self.token_model.objects.create(
            key=self.key,
            user=self.user,
        )

    def test_get_states_with_token_success(self):
        auth = self.header_prefix + self.key
        response = self.factory.get(
            self.path, HTTP_AUTHORIZATION=auth
        )
        assert response.status_code == status.HTTP_200_OK

    def test_get_states_without_token_unsuccess(self):
        response = self.factory.get(
            self.path
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_center_coordinates_USA_and_correct_zoom_in_response(self):
        auth = self.header_prefix + self.key
        response = self.factory.get(
            self.path, HTTP_AUTHORIZATION=auth
        )
        assert response.json().get('center').get('coordinates')
        assert response.json().get('zoom') == settings.ZOOM_US

    def test_response_with_medication_and_state_should_return_1_position(
        self,
        geographic_object,
    ):
        medication_name = MedicationNameFactory()
        StateFactory(geometry=geographic_object)
        number_states = State.objects.all().count()
        auth = self.header_prefix + self.key
        path_with_medication = '?med_id={}'.format(medication_name.id)
        response = self.factory.get(
            self.path + path_with_medication, HTTP_AUTHORIZATION=auth
        )
        assert len(response.json().get('features')) == number_states

    def test_response_without_med_id_returns_0_positions(
        self,
        geographic_object,
    ):
        StateFactory(geometry=geographic_object)
        auth = self.header_prefix + self.key
        path_with_medication = '?med_id='
        response = self.factory.get(
            self.path + path_with_medication, HTTP_AUTHORIZATION=auth
        )
        assert len(response.json().get('features')) == 0

    def test_response_with_non_existing_med_id_returns_0_positions(
        self,
        geographic_object,
    ):
        medication_name = MedicationNameFactory()
        StateFactory(geometry=geographic_object)
        auth = self.header_prefix + self.key
        path_with_medication = '?med_id={}'.format(
            randint(medication_name.id + 1, medication_name.id + 19)
        )
        response = self.factory.get(
            self.path + path_with_medication, HTTP_AUTHORIZATION=auth
        )
        assert len(response.json().get('features')) == 0


class TestGeoStatsCountyGETView:
    token_model = Token
    path = '/api/v1/medications/geo_stats/state/{}'
    header_prefix = 'Token '

    @pytest.fixture(autouse=True)
    def setup_stuff(self, db, testuser):
        self.factory = APIClient()
        self.user = testuser

        self.key = 'abcd1234'
        self.token = self.token_model.objects.create(
            key=self.key,
            user=self.user,
        )

    def test_get_counties_with_token_success(self, geographic_object):
        state = StateFactory(geometry=geographic_object)
        path = self.path.format(state.id)
        auth = self.header_prefix + self.key
        response = self.factory.get(
            path, HTTP_AUTHORIZATION=auth
        )
        assert response.status_code == status.HTTP_200_OK

    def test_get_counties_without_token_unsuccess(self, geographic_object):
        state = StateFactory(geometry=geographic_object)
        path = self.path.format(state.id)
        response = self.factory.get(
            path
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_404_if_not_state_id_in_url(self):
        auth = self.header_prefix + self.key
        response = self.factory.get(
            self.path, HTTP_AUTHORIZATION=auth
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_empty_list_features_wrong_non_existing_state_id(
        self,
        geographic_object,
    ):
        state = StateFactory(geometry=geographic_object)
        path = self.path.format(state.id + 1)
        auth = self.header_prefix + self.key
        response = self.factory.get(
            path, HTTP_AUTHORIZATION=auth
        )
        assert len(response.json().get('features')) == 0

    def test_1_feature_when_state_has_county(self, geographic_object):
        medication_name = MedicationNameFactory()
        state = StateFactory(geometry=geographic_object)
        CountyFactory(state=state, geometry=geographic_object)
        path = self.path.format(state.id) + '?med_id={}'.format(
            medication_name.id
        )
        auth = self.header_prefix + self.key
        response = self.factory.get(
            path, HTTP_AUTHORIZATION=auth
        )
        assert len(response.json().get(
            'features')
        ) == state.counties.all().count()

    def test_center_and_zoom_are_correct(self, geographic_object):
        medication_name = MedicationNameFactory()
        state = StateFactory(geometry=geographic_object)
        CountyFactory(state=state, geometry=geographic_object)
        path = self.path.format(state.id) + '?med_id={}'.format(
            medication_name.id
        )
        auth = self.header_prefix + self.key
        response = self.factory.get(
            path, HTTP_AUTHORIZATION=auth
        )
        assert response.json().get('zoom') == settings.ZOOM_STATE
        assert response.json().get(
            'center'
        ) == json.loads(geographic_object.json)

    def test_response_without_med_id_returns_0_positions(
        self,
        geographic_object,
    ):
        state = StateFactory(geometry=geographic_object)
        CountyFactory(state=state, geometry=geographic_object)
        auth = self.header_prefix + self.key
        path = self.path.format(state.id) + '?med_id='
        response = self.factory.get(
            path, HTTP_AUTHORIZATION=auth
        )
        assert len(response.json().get('features')) == 0


class TestGeoStatsZipCodeGETView:
    token_model = Token
    path = '/api/v1/medications/geo_stats/zipcode/{}'
    header_prefix = 'Token '

    @pytest.fixture(autouse=True)
    def setup_stuff(self, db, testuser):
        self.factory = APIClient()
        self.user = testuser

        self.key = 'abcd1234'
        self.token = self.token_model.objects.create(
            key=self.key,
            user=self.user,
        )

    def test_get_zipcode_with_token_success(self, geographic_object):
        zip_code = f'{randrange(1, 10**5):05}'
        medication_name = MedicationNameFactory()
        state = StateFactory(geometry=geographic_object)
        zipcode = ZipCodeFactory(
            state=state,
            geometry=geographic_object,
            zipcode=zip_code,
        )
        path = self.path.format(zipcode.zipcode) + '?med_id={}'.format(
            medication_name.id
        )
        auth = self.header_prefix + self.key
        response = self.factory.get(
            path, HTTP_AUTHORIZATION=auth
        )
        assert response.status_code == status.HTTP_200_OK

    def test_get_zipcode_without_token_unsuccess(self, geographic_object):
        zip_code = f'{randrange(1, 10**5):05}'
        medication_name = MedicationNameFactory()
        state = StateFactory(geometry=geographic_object)
        zipcode = ZipCodeFactory(
            state=state,
            geometry=geographic_object,
            zipcode=zip_code,
        )
        path = self.path.format(zipcode.zipcode) + '?med_id={}'.format(
            medication_name.id
        )
        response = self.factory.get(
            path
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_404_if_not_zipcode_in_url(self):
        auth = self.header_prefix + self.key
        response = self.factory.get(
            self.path, HTTP_AUTHORIZATION=auth
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_information_returned_is_correct(self, geographic_object):
        zip_code = f'{randrange(1, 10**5):05}'
        medication_name = MedicationNameFactory()
        state = StateFactory(geometry=geographic_object)
        zipcode = ZipCodeFactory(
            state=state,
            geometry=geographic_object,
            zipcode=zip_code,
        )
        path = self.path.format(zipcode.zipcode) + '?med_id={}'.format(
            medication_name.id
        )
        auth = self.header_prefix + self.key
        response = self.factory.get(
            path, HTTP_AUTHORIZATION=auth
        )
        assert response.json().get('zoom') == settings.ZOOM_ZIPCODE
        assert response.json().get(
            'geometry'
        ) == json.loads(geographic_object.json)
        assert response.json().get(
            'center'
        ) == json.loads(geographic_object.json)

    def test_response_without_med_id_returns_404(
        self,
        geographic_object,
    ):
        zip_code = f'{randrange(1, 10**5):05}'
        state = StateFactory(geometry=geographic_object)
        zipcode = ZipCodeFactory(
            state=state,
            geometry=geographic_object,
            zipcode=zip_code,
        )
        path = self.path.format(zipcode.zipcode) + '?med_id='
        auth = self.header_prefix + self.key
        response = self.factory.get(
            path, HTTP_AUTHORIZATION=auth
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_response_with_wrong_med_id_returns_404(
        self,
        geographic_object,
    ):
        medication_name = MedicationNameFactory()
        zip_code = f'{randrange(1, 10**5):05}'
        state = StateFactory(geometry=geographic_object)
        zipcode = ZipCodeFactory(
            state=state,
            geometry=geographic_object,
            zipcode=zip_code,
        )
        path = self.path.format(zipcode.zipcode) + '?med_id={}'.format(
            medication_name.id + 1
        )
        auth = self.header_prefix + self.key
        response = self.factory.get(
            path, HTTP_AUTHORIZATION=auth
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

import os
import pytest
import csv

from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _

from celery.task.control import inspect
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from medications.models import Organization
from medications.constants import field_rows


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
        organization=organization,
        is_test=True,
    )
    return user


@pytest.fixture()
def user_no_organization():
    email = 'alciseneros@sleep.com'
    password = 'password'
    user = User.objects.create_user(
        email,
        password,
        is_test=False,
    )
    return user


class TestTokenAuth:
    """Token authentication"""
    token_model = Token
    path = '/api/v1/medications/'
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
    path = '/api/v1/medications/'
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


class TestGenerateMedicationTaskTriggered:
    token_model = Token
    path = '/api/v1/medications/'
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

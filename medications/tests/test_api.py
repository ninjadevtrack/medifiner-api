import os
import pytest
import csv

from django.contrib.auth import get_user_model

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
        is_test=True,
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

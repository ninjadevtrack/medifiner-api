import jwt

from django.contrib import auth
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import login as auth_login
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

from rest_framework.authtoken.models import Token
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from rest_registration.exceptions import BadRequest

from rest_framework_jwt.serializers import (
    jwt_payload_handler,
    jwt_encode_handler,
)
from rest_framework_jwt.views import jwt_response_payload_handler
from rest_framework_jwt.utils import jwt_decode_handler

from .forms import UserAuthenticationForm
from .models import User
from .serializers import SignInSerializer


@sensitive_post_parameters()
@csrf_protect
@never_cache
def login(request, template_name='auth_ex/user/login.html',
          redirect_field_name=REDIRECT_FIELD_NAME,
          authentication_form=UserAuthenticationForm,
          extra_context=None):
    return auth_login(request, template_name, redirect_field_name,
                      authentication_form, extra_context)


class SignInView(RetrieveUpdateAPIView):
    serializer_class = SignInSerializer
    permission_classes = (AllowAny,)

    def get_object(self):
        secret = self.request.query_params.get('s')

        try:
            decoded_token = jwt_decode_handler(secret)
        except jwt.ExpiredSignature:
            decoded_token = jwt.decode(secret, None, False)
        except jwt.DecodeError:
            msg = 'Error decoding signature.'
            raise BadRequest(msg)

        user_id = decoded_token.get('user_id')
        invitation_code = decoded_token.get('invitation_code')

        if User.objects.filter(used_invitation_code=invitation_code):
            msg = 'This invitation link has been already used'
            raise BadRequest(msg)

        try:
            user = User.objects.filter(
                invitation_mail_sent=True,
            ).get(id=user_id)
        except User.DoesNotExist:
            raise BadRequest('No user found')

        self.request.user = user
        self.request.user.used_invitation_code = invitation_code
        return user

    def perform_update(self, serializer):
        user = self.request.user
        user.set_password(serializer.validated_data['password'])
        user.organization = serializer.validated_data['organization']
        user.role = serializer.validated_data['role']
        user.save()
        auth.login(self.request, user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        payload = jwt_payload_handler(request.user)
        token = jwt_encode_handler(payload)
        response_data = jwt_response_payload_handler(
            token, request.user, self.request
        )
        return Response(response_data)

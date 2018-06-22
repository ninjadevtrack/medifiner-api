from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import login as auth_login
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

from .forms import UserAuthenticationForm


@sensitive_post_parameters()
@csrf_protect
@never_cache
def login(request, template_name='auth_ex/user/login.html',
          redirect_field_name=REDIRECT_FIELD_NAME,
          authentication_form=UserAuthenticationForm,
          extra_context=None):
    return auth_login(request, template_name, redirect_field_name,
                      authentication_form, extra_context)

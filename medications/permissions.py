from rest_framework import permissions

from .models import ZipCode


class NationalLevel(permissions.BasePermission):
    message = 'National level permission required'

    def has_permission(self, request, view):
        return (
            request.method in permissions.SAFE_METHODS and (
                request.user and
                request.user.is_authenticated and
                request.user.permission_level == request.user.NATIONAL_LEVEL
            )
        )


class SelfStatePermissionLevel(permissions.BasePermission):
    message = 'State level permission required for state'

    def has_permission(self, request, view):
        super_permission = (
            request.method in permissions.SAFE_METHODS and (
                request.user and
                request.user.is_authenticated and
                request.user.permission_level == request.user.NATIONAL_LEVEL
            )
        )
        user_state_id = getattr(request.user, 'state_id', None)
        view_state = view.kwargs.get('state_id')
        state_permission = False
        if user_state_id:
            state_permission = user_state_id == view_state
        return super_permission or state_permission


class SelfZipCodePermissionLevel(permissions.BasePermission):
    message = 'State level permission required for zipcode'

    def has_permission(self, request, view):
        super_permission = (
            request.method in permissions.SAFE_METHODS and (
                request.user and
                request.user.is_authenticated and
                request.user.permission_level == request.user.NATIONAL_LEVEL
            )
        )
        user_state_id = getattr(request.user, 'state_id', None)
        user_zipcodes = []
        if user_state_id:
            user_zipcodes = ZipCode.objects.filter(state_id=user_state_id).values_list(
                'zipcode',
                flat=True,
            )
        view_zipcode = view.kwargs.get('zipcode')
        zipcode_permission = view_zipcode in user_zipcodes
        return super_permission or zipcode_permission

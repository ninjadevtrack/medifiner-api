from rest_framework import permissions


class NationalLevel(permissions.BasePermission):
    message = 'This user has not national level permission'

    def has_permission(self, request, view):
        return (
            request.method in permissions.SAFE_METHODS and (
                request.user and
                request.user.is_authenticated and
                request.user.permission_level == request.user.NATIONAL_LEVEL
            )
        )

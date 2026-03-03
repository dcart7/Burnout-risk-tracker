from rest_framework.permissions import BasePermission


class HasRBACPermissions(BasePermission):
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        required_permissions = getattr(view, "required_permissions", ())
        if not required_permissions:
            return True

        user = request.user
        return bool(user and user.is_authenticated and user.has_perms(required_permissions))

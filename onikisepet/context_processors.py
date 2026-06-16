from .permissions import (
    can_create_transactions,
    can_manage_accounts,
    can_manage_categories,
)


def navigation_permissions(request):
    user = request.user
    if not user.is_authenticated:
        return {}

    return {
        "can_manage_categories": can_manage_categories(user),
        "can_manage_accounts": can_manage_accounts(user),
        "can_create_transactions": can_create_transactions(user),
        "role_display_name": _role_display_name(user),
    }


def _role_display_name(user):
    if user.is_superuser:
        return "Yönetici"
    if user.groups.filter(name="Data Entry").exists():
        return "Finans Görevlisi"
    if user.groups.filter(name="Viewer").exists():
        return "Liderlik"
    return ""

def can_manage_categories(user):
    return user.is_superuser


def can_manage_accounts(user):
    return user.is_superuser


def can_create_transactions(user):
    return user.is_superuser or user.groups.filter(name="Data Entry").exists()

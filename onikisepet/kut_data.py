"""KUT church's chart of accounts and categories.

These are the congregation's real account and category names, carried over from
the collaborator's branch. They are data rather than interface text, so they
are deliberately not translated: renaming a real bank account by switching
language would make the books unreadable.
"""

from onikisepet.models import Account, Category

KUT_ACCOUNTS = [
    {
        "name": "Kasa (Defter)",
        "account_type": Account.AccountType.CASH,
        "account_purpose": Account.AccountPurpose.CASH,
        "currency": Account.Currency.TRY,
    },
    {
        "name": "Garanti - Online Bağış",
        "account_type": Account.AccountType.BANK,
        "account_purpose": Account.AccountPurpose.ONLINE_DONATION,
        "currency": Account.Currency.TRY,
    },
    {
        "name": "Garanti - Ana Gider",
        "account_type": Account.AccountType.BANK,
        "account_purpose": Account.AccountPurpose.MAIN_EXPENSE,
        "currency": Account.Currency.TRY,
    },
    {
        "name": "Omega (USD)",
        "account_type": Account.AccountType.BANK,
        "account_purpose": Account.AccountPurpose.FOREIGN_CURRENCY,
        "currency": Account.Currency.USD,
    },
    {
        "name": "Merhamet (EUR)",
        "account_type": Account.AccountType.BANK,
        "account_purpose": Account.AccountPurpose.FOREIGN_CURRENCY,
        "currency": Account.Currency.EUR,
    },
    {
        "name": "Deprem Fonu (TRY)",
        "account_type": Account.AccountType.SAVINGS,
        "account_purpose": Account.AccountPurpose.SAVINGS,
        "currency": Account.Currency.TRY,
    },
    {
        "name": "Deprem Fonu (USD)",
        "account_type": Account.AccountType.SAVINGS,
        "account_purpose": Account.AccountPurpose.FOREIGN_CURRENCY,
        "currency": Account.Currency.USD,
    },
    {
        "name": "Deprem Fonu (EUR)",
        "account_type": Account.AccountType.SAVINGS,
        "account_purpose": Account.AccountPurpose.FOREIGN_CURRENCY,
        "currency": Account.Currency.EUR,
    },
]

KUT_CATEGORIES = [
    {"name": "Bağış", "category_type": Category.CategoryType.INCOME},
    {"name": "Online Bağış", "category_type": Category.CategoryType.INCOME},
    {"name": "Özel Destek", "category_type": Category.CategoryType.INCOME},
    {"name": "Kira", "category_type": Category.CategoryType.EXPENSE},
    {"name": "Faturalar", "category_type": Category.CategoryType.EXPENSE},
    {"name": "Personel", "category_type": Category.CategoryType.EXPENSE},
    {"name": "Yardım", "category_type": Category.CategoryType.EXPENSE},
    {"name": "Ofis ve Malzeme", "category_type": Category.CategoryType.EXPENSE},
]


def seed_kut_data():
    """Create the accounts and categories, leaving existing rows untouched.

    Matching is by name (and type, for categories) so that re-running never
    duplicates a row, and never overwrites an opening balance or a rename the
    treasurer has since made by hand.
    """
    created_accounts = 0
    for spec in KUT_ACCOUNTS:
        _account, created = Account.objects.get_or_create(
            name=spec["name"],
            defaults={
                "account_type": spec["account_type"],
                "account_purpose": spec["account_purpose"],
                "currency": spec["currency"],
            },
        )
        created_accounts += int(created)

    created_categories = 0
    for spec in KUT_CATEGORIES:
        _category, created = Category.objects.get_or_create(
            name=spec["name"],
            category_type=spec["category_type"],
        )
        created_categories += int(created)

    return {"accounts": created_accounts, "categories": created_categories}

from decimal import Decimal

from onikisepet.models import Account

KUT_ACCOUNTS = [
    {
        "name": "Kasa",
        "account_type": Account.AccountType.CASH,
        "account_purpose": Account.AccountPurpose.CASH,
        "currency": Account.Currency.TRY,
    },
    {
        "name": "Gelir Hesabı (Vahan) - Garanti",
        "account_type": Account.AccountType.BANK,
        "account_purpose": Account.AccountPurpose.ONLINE_DONATION,
        "currency": Account.Currency.TRY,
    },
    {
        "name": "Gider Hesabı (Mike, Vahan) - Garanti",
        "account_type": Account.AccountType.BANK,
        "account_purpose": Account.AccountPurpose.MAIN_EXPENSE,
        "currency": Account.Currency.TRY,
    },
    {
        "name": "Omega 1 USD",
        "account_type": Account.AccountType.SAVINGS,
        "account_purpose": Account.AccountPurpose.FOREIGN_CURRENCY,
        "currency": Account.Currency.USD,
    },
    {
        "name": "Omega 2 USD",
        "account_type": Account.AccountType.SAVINGS,
        "account_purpose": Account.AccountPurpose.FOREIGN_CURRENCY,
        "currency": Account.Currency.USD,
    },
    {
        "name": "Omega 3 USD",
        "account_type": Account.AccountType.SAVINGS,
        "account_purpose": Account.AccountPurpose.FOREIGN_CURRENCY,
        "currency": Account.Currency.USD,
    },
    {
        "name": "Merhamet EUR",
        "account_type": Account.AccountType.SAVINGS,
        "account_purpose": Account.AccountPurpose.FOREIGN_CURRENCY,
        "currency": Account.Currency.EUR,
    },
    {
        "name": "Deprem TL",
        "account_type": Account.AccountType.SAVINGS,
        "account_purpose": Account.AccountPurpose.SAVINGS,
        "currency": Account.Currency.TRY,
    },
    {
        "name": "Deprem USD",
        "account_type": Account.AccountType.SAVINGS,
        "account_purpose": Account.AccountPurpose.FOREIGN_CURRENCY,
        "currency": Account.Currency.USD,
    },
    {
        "name": "Deprem EUR",
        "account_type": Account.AccountType.SAVINGS,
        "account_purpose": Account.AccountPurpose.FOREIGN_CURRENCY,
        "currency": Account.Currency.EUR,
    },
]


def seed_kut_accounts(*, opening_balances=None):
    opening_balances = opening_balances or {}
    created = []
    existing = []

    for spec in KUT_ACCOUNTS:
        defaults = {
            "account_type": spec["account_type"],
            "account_purpose": spec["account_purpose"],
            "currency": spec["currency"],
            "opening_balance": opening_balances.get(spec["name"], Decimal("0")),
            "is_active": True,
        }
        account, was_created = Account.objects.get_or_create(
            name=spec["name"],
            defaults=defaults,
        )
        if was_created:
            created.append(account)
        else:
            existing.append(account)

    return created, existing

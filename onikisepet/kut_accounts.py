from decimal import Decimal

from onikisepet.models import Account

KUT_ACCOUNTS = [
    {
        "name": "Kasa (Defter)",
        "account_type": Account.AccountType.CASH,
        "account_purpose": Account.AccountPurpose.CASH,
        "currency": Account.Currency.TRY,
        "opening_balance": Decimal("0"),
    },
    {
        "name": "Garanti - Online Bağış",
        "account_type": Account.AccountType.BANK,
        "account_purpose": Account.AccountPurpose.ONLINE_DONATION,
        "currency": Account.Currency.TRY,
        "opening_balance": Decimal("0"),
    },
    {
        "name": "Garanti - Ana Gider",
        "account_type": Account.AccountType.BANK,
        "account_purpose": Account.AccountPurpose.MAIN_EXPENSE,
        "currency": Account.Currency.TRY,
        "opening_balance": Decimal("0"),
    },
    {
        "name": "Omega (USD)",
        "account_type": Account.AccountType.BANK,
        "account_purpose": Account.AccountPurpose.FOREIGN_CURRENCY,
        "currency": Account.Currency.USD,
        "opening_balance": Decimal("0"),
    },
    {
        "name": "Merhamet (EUR)",
        "account_type": Account.AccountType.BANK,
        "account_purpose": Account.AccountPurpose.FOREIGN_CURRENCY,
        "currency": Account.Currency.EUR,
        "opening_balance": Decimal("0"),
    },
    {
        "name": "Deprem Fonu (TRY)",
        "account_type": Account.AccountType.SAVINGS,
        "account_purpose": Account.AccountPurpose.SAVINGS,
        "currency": Account.Currency.TRY,
        "opening_balance": Decimal("0"),
    },
    {
        "name": "Deprem Fonu (USD)",
        "account_type": Account.AccountType.SAVINGS,
        "account_purpose": Account.AccountPurpose.FOREIGN_CURRENCY,
        "currency": Account.Currency.USD,
        "opening_balance": Decimal("0"),
    },
    {
        "name": "Deprem Fonu (EUR)",
        "account_type": Account.AccountType.SAVINGS,
        "account_purpose": Account.AccountPurpose.FOREIGN_CURRENCY,
        "currency": Account.Currency.EUR,
        "opening_balance": Decimal("0"),
    },
]


def load_kut_accounts():
    created_count = 0

    for spec in KUT_ACCOUNTS:
        _account, created = Account.objects.get_or_create(
            name=spec["name"],
            defaults={
                "account_type": spec["account_type"],
                "account_purpose": spec["account_purpose"],
                "currency": spec["currency"],
                "opening_balance": spec["opening_balance"],
                "is_active": True,
            },
        )
        if created:
            created_count += 1

    return created_count

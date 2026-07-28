from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction as db_transaction
from django.utils import timezone

from onikisepet.bootstrap import bootstrap_kut
from onikisepet.management.commands.create_demo_users import create_demo_users
from onikisepet.models import Account, Category, Transaction

DEMO_DESCRIPTION_PREFIX = "[Demo]"


def _demo_description(text):
    return f"{DEMO_DESCRIPTION_PREFIX} {text}"


def _account(name):
    return Account.objects.get(name=name)


def _category(name):
    return Category.objects.get(name=name)


def _month_day(base: date, day: int) -> date:
    return base.replace(day=min(day, 28))


def _previous_month(base: date) -> date:
    first = base.replace(day=1)
    return first - timedelta(days=1)


def clear_demo_transactions():
    deleted, _ = Transaction.objects.filter(
        description__startswith=DEMO_DESCRIPTION_PREFIX,
    ).delete()
    return deleted


def _create_approved(
    *,
    user,
    transaction_type,
    amount,
    txn_date,
    description,
    category=None,
    source_account=None,
    target_account=None,
    payee="",
):
    return Transaction.objects.create(
        date=txn_date,
        amount=amount,
        transaction_type=transaction_type,
        description=_demo_description(description),
        category=category,
        source_account=source_account,
        target_account=target_account,
        payee=payee,
        created_by=user,
        approval_status=Transaction.ApprovalStatus.APPROVED,
        approved_by=user,
        approved_at=timezone.now(),
    )


def _create_pending(
    *,
    user,
    transaction_type,
    amount,
    txn_date,
    description,
    category=None,
    source_account=None,
    target_account=None,
    payee="",
):
    return Transaction.objects.create(
        date=txn_date,
        amount=amount,
        transaction_type=transaction_type,
        description=_demo_description(description),
        category=category,
        source_account=source_account,
        target_account=target_account,
        payee=payee,
        created_by=user,
        approval_status=Transaction.ApprovalStatus.PENDING,
    )


def _seed_transactions(user, today: date):
    this_month = today.replace(day=1)
    prev = _previous_month(today)

    cash = _account("Kasa (Defter)")
    online = _account("Garanti - Online Bağış")
    main_expense = _account("Garanti - Ana Gider")
    omega = _account("Omega (USD)")
    merhamet = _account("Merhamet (EUR)")
    deprem_try = _account("Deprem Fonu (TRY)")

    bagis = _category("Bağış")
    online_bagis = _category("Online Bağış")
    ozel = _category("Özel Destek")
    kira = _category("Kira")
    faturalar = _category("Faturalar")
    personel = _category("Personel")
    yardim = _category("Yardım")
    ofis = _category("Ofis ve Malzeme")

    created = []

    # --- This month: TRY income ---
    created.append(
        _create_approved(
            user=user,
            transaction_type=Transaction.TransactionType.INCOME,
            amount=Decimal("18500.00"),
            txn_date=_month_day(this_month, 3),
            description="Pazar nakit bağış",
            category=bagis,
            target_account=cash,
            payee="Pazar koleksiyonu",
        )
    )
    created.append(
        _create_approved(
            user=user,
            transaction_type=Transaction.TransactionType.INCOME,
            amount=Decimal("7200.00"),
            txn_date=_month_day(this_month, 5),
            description="Online bağış — PayTR",
            category=online_bagis,
            target_account=online,
            payee="Online bağışçı",
        )
    )
    created.append(
        _create_approved(
            user=user,
            transaction_type=Transaction.TransactionType.INCOME,
            amount=Decimal("15000.00"),
            txn_date=_month_day(this_month, 8),
            description="Özel destek — proje",
            category=ozel,
            target_account=cash,
            payee="Proje sponsoru",
        )
    )

    # --- This month: TRY expenses ---
    created.append(
        _create_approved(
            user=user,
            transaction_type=Transaction.TransactionType.EXPENSE,
            amount=Decimal("12000.00"),
            txn_date=_month_day(this_month, 2),
            description="Bina kirası",
            category=kira,
            source_account=main_expense,
            payee="Mülk sahibi",
        )
    )
    created.append(
        _create_approved(
            user=user,
            transaction_type=Transaction.TransactionType.EXPENSE,
            amount=Decimal("2850.50"),
            txn_date=_month_day(this_month, 6),
            description="Elektrik ve internet",
            category=faturalar,
            source_account=main_expense,
            payee="Fatura",
        )
    )
    created.append(
        _create_approved(
            user=user,
            transaction_type=Transaction.TransactionType.EXPENSE,
            amount=Decimal("9800.00"),
            txn_date=_month_day(this_month, 10),
            description="Personel ödemeleri",
            category=personel,
            source_account=main_expense,
            payee="Personel",
        )
    )
    created.append(
        _create_approved(
            user=user,
            transaction_type=Transaction.TransactionType.EXPENSE,
            amount=Decimal("3500.00"),
            txn_date=_month_day(this_month, 12),
            description="Aile yardımı",
            category=yardim,
            source_account=cash,
            payee="Yardım alan",
        )
    )
    created.append(
        _create_approved(
            user=user,
            transaction_type=Transaction.TransactionType.EXPENSE,
            amount=Decimal("1425.75"),
            txn_date=_month_day(this_month, 14),
            description="Kırtasiye ve temizlik",
            category=ofis,
            source_account=main_expense,
            payee="Ofis market",
        )
    )

    # --- Transfers (approved for report visibility) ---
    created.append(
        _create_approved(
            user=user,
            transaction_type=Transaction.TransactionType.TRANSFER,
            amount=Decimal("5000.00"),
            txn_date=_month_day(this_month, 7),
            description="Online bağıştan ana hesaba",
            source_account=online,
            target_account=main_expense,
        )
    )
    created.append(
        _create_approved(
            user=user,
            transaction_type=Transaction.TransactionType.TRANSFER,
            amount=Decimal("2000.00"),
            txn_date=_month_day(this_month, 11),
            description="Kasaya nakit aktarım",
            source_account=main_expense,
            target_account=cash,
        )
    )
    created.append(
        _create_approved(
            user=user,
            transaction_type=Transaction.TransactionType.TRANSFER,
            amount=Decimal("3000.00"),
            txn_date=_month_day(this_month, 15),
            description="Deprem fonuna aktarım",
            source_account=main_expense,
            target_account=deprem_try,
        )
    )

    # --- USD / EUR ---
    created.append(
        _create_approved(
            user=user,
            transaction_type=Transaction.TransactionType.INCOME,
            amount=Decimal("1200.00"),
            txn_date=_month_day(this_month, 4),
            description="USD bağış — yurt dışı",
            category=bagis,
            target_account=omega,
            payee="Overseas donor",
        )
    )
    created.append(
        _create_approved(
            user=user,
            transaction_type=Transaction.TransactionType.EXPENSE,
            amount=Decimal("350.00"),
            txn_date=_month_day(this_month, 9),
            description="USD yardım ödemesi",
            category=yardim,
            source_account=omega,
            payee="Aid partner",
        )
    )
    created.append(
        _create_approved(
            user=user,
            transaction_type=Transaction.TransactionType.INCOME,
            amount=Decimal("800.00"),
            txn_date=_month_day(this_month, 5),
            description="EUR bağış",
            category=ozel,
            target_account=merhamet,
            payee="EU supporter",
        )
    )
    created.append(
        _create_approved(
            user=user,
            transaction_type=Transaction.TransactionType.EXPENSE,
            amount=Decimal("120.00"),
            txn_date=_month_day(this_month, 13),
            description="EUR operasyon gideri",
            category=ofis,
            source_account=merhamet,
            payee="Supplier EU",
        )
    )

    # --- Previous month (for period comparison in reports) ---
    created.append(
        _create_approved(
            user=user,
            transaction_type=Transaction.TransactionType.INCOME,
            amount=Decimal("22000.00"),
            txn_date=_month_day(prev, 10),
            description="Önceki ay nakit bağış",
            category=bagis,
            target_account=cash,
        )
    )
    created.append(
        _create_approved(
            user=user,
            transaction_type=Transaction.TransactionType.EXPENSE,
            amount=Decimal("12000.00"),
            txn_date=_month_day(prev, 5),
            description="Önceki ay kira",
            category=kira,
            source_account=main_expense,
        )
    )
    created.append(
        _create_approved(
            user=user,
            transaction_type=Transaction.TransactionType.EXPENSE,
            amount=Decimal("4500.00"),
            txn_date=_month_day(prev, 18),
            description="Önceki ay yardım",
            category=yardim,
            source_account=cash,
        )
    )

    # --- Pending (approval panel) ---
    created.append(
        _create_pending(
            user=user,
            transaction_type=Transaction.TransactionType.EXPENSE,
            amount=Decimal("875.00"),
            txn_date=_month_day(this_month, 16),
            description="Onay bekleyen ofis alımı",
            category=ofis,
            source_account=main_expense,
            payee="Kırtasiye",
        )
    )
    created.append(
        _create_pending(
            user=user,
            transaction_type=Transaction.TransactionType.INCOME,
            amount=Decimal("2500.00"),
            txn_date=_month_day(this_month, 17),
            description="Onay bekleyen nakit bağış",
            category=bagis,
            target_account=cash,
            payee="Bağışçı",
        )
    )

    return created


def seed_demo_data(*, reset=False):
    bootstrap = bootstrap_kut()
    demo_users = create_demo_users(reset_passwords=False)

    existing = Transaction.objects.filter(
        description__startswith=DEMO_DESCRIPTION_PREFIX,
    ).count()
    if existing and not reset:
        return {
            "bootstrap": bootstrap,
            "demo_users": demo_users,
            "cleared": 0,
            "created": 0,
            "skipped": True,
            "existing": existing,
        }

    cleared = 0
    if reset and existing:
        cleared = clear_demo_transactions()

    user_model = get_user_model()
    user = (
        user_model.objects.filter(username="finans").first()
        or user_model.objects.filter(is_superuser=True).first()
        or user_model.objects.order_by("pk").first()
    )
    if user is None:
        raise RuntimeError("Demo veri için en az bir kullanıcı gerekli.")

    with db_transaction.atomic():
        created = _seed_transactions(user, timezone.localdate())

    return {
        "bootstrap": bootstrap,
        "demo_users": demo_users,
        "cleared": cleared,
        "created": len(created),
        "skipped": False,
        "existing": 0,
        "user": user.username,
    }

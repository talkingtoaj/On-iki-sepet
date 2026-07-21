from .models import Account, AccountChangeRequest, BankStatementImport, BankStatementRow, Category, Transaction


def active_accounts(**filters):
    return Account.objects.filter(is_active=True, **filters)


def active_categories(category_type):
    return Category.objects.filter(
        category_type=category_type,
        is_active=True,
    )


def approved_transactions():
    return Transaction.objects.filter(
        approval_status=Transaction.ApprovalStatus.APPROVED,
    )


def pending_transactions():
    return Transaction.objects.filter(
        approval_status=Transaction.ApprovalStatus.PENDING,
    )


def pending_account_change_requests():
    return AccountChangeRequest.objects.filter(
        status=AccountChangeRequest.Status.PENDING,
    ).select_related("account", "requested_by")


def pending_bank_imports():
    from django.db.models import Count, Q

    return (
        BankStatementImport.objects.filter(
            status=BankStatementImport.Status.PREVIEW,
        )
        .annotate(
            importable_row_count=Count(
                "rows",
                filter=Q(
                    rows__is_skipped=False,
                    rows__parse_error="",
                    rows__transaction__isnull=True,
                ),
            ),
        )
        .filter(importable_row_count__gt=0)
        .select_related("uploaded_by")
        .order_by("-uploaded_at")
    )
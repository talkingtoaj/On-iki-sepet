from onikisepet import messages as msg
from onikisepet.models import Account, Transaction


def transfer_source_accounts():
    return Account.objects.filter(
        is_active=True,
        account_purpose__in=[
            Account.AccountPurpose.CASH,
            Account.AccountPurpose.ONLINE_DONATION,
            Account.AccountPurpose.MAIN_EXPENSE,
            Account.AccountPurpose.FOREIGN_CURRENCY,
            Account.AccountPurpose.SAVINGS,
        ],
    )


def transfer_target_accounts():
    return Account.objects.filter(
        is_active=True,
        account_purpose__in=[
            Account.AccountPurpose.CASH,
            Account.AccountPurpose.MAIN_EXPENSE,
            Account.AccountPurpose.FOREIGN_CURRENCY,
            Account.AccountPurpose.SAVINGS,
        ],
    )


def validate_account_purpose_for_transaction(transaction, errors):
    source = transaction.source_account
    target = transaction.target_account
    transaction_type = transaction.transaction_type

    if transaction_type == Transaction.TransactionType.INCOME:
        if target is not None and target.account_purpose == Account.AccountPurpose.MAIN_EXPENSE:
            errors["target_account"] = msg.INCOME_TO_EXPENSE_ACCOUNT_FORBIDDEN
        return

    if transaction_type == Transaction.TransactionType.EXPENSE:
        if source is not None and source.account_purpose == Account.AccountPurpose.ONLINE_DONATION:
            errors["source_account"] = msg.EXPENSE_FROM_ONLINE_DONATION_FORBIDDEN
        return

    if transaction_type == Transaction.TransactionType.TRANSFER:
        if target is not None and target.account_purpose == Account.AccountPurpose.ONLINE_DONATION:
            errors["target_account"] = msg.TRANSFER_TO_ONLINE_DONATION_FORBIDDEN

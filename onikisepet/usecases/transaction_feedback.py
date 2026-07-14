from onikisepet.models import Transaction

TRANSACTION_CREATED_APPROVED = "Kayıt onaylandı ve rapora eklendi."
TRANSACTION_CREATED_PENDING = (
    "Kayıt alındı. Onay bekliyor — rapora henüz yansımaz."
)
TRANSFER_CREATED_PENDING = (
    "Transfer kaydedildi. Onay sonrası hesap bakiyeleri güncellenir."
)
TRANSFER_CREATED_APPROVED = (
    "Transfer onaylandı ve hesap bakiyeleri güncellendi."
)


def transaction_created_message(transaction):
    if transaction.transaction_type == Transaction.TransactionType.TRANSFER:
        if transaction.approval_status == Transaction.ApprovalStatus.APPROVED:
            return TRANSFER_CREATED_APPROVED
        return TRANSFER_CREATED_PENDING
    if transaction.approval_status == Transaction.ApprovalStatus.APPROVED:
        return TRANSACTION_CREATED_APPROVED
    return TRANSACTION_CREATED_PENDING

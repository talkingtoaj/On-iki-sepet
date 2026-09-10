from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from .validators import validate_receipt_file


class Category(models.Model):
    class CategoryType(models.TextChoices):
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"

    name = models.CharField(max_length=100)
    category_type = models.CharField(
        max_length=10,
        choices=CategoryType.choices,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category_type", "name"]
        constraints = [
            # Unique per type, not globally: a church may both receive and
            # spend under the same heading, e.g. "Missions".
            models.UniqueConstraint(
                fields=["name", "category_type"],
                name="unique_category_name_per_type",
            )
        ]

    def __str__(self):
        return self.name


class Account(models.Model):
    class AccountType(models.TextChoices):
        CASH = "cash", "Cash"
        BANK = "bank", "Bank"
        SAVINGS = "savings", "Savings"

    class AccountPurpose(models.TextChoices):
        CASH = "cash", "Cash"
        ONLINE_DONATION = "online_donation", "Online Donation"
        MAIN_EXPENSE = "main_expense", "Main Expense"
        FOREIGN_CURRENCY = "foreign_currency", "Foreign Currency"
        SAVINGS = "savings", "Savings"

    class Currency(models.TextChoices):
        TRY = "TRY", "TRY"
        USD = "USD", "USD"
        EUR = "EUR", "EUR"

    name = models.CharField(max_length=100, unique=True)
    account_type = models.CharField(
        max_length=10,
        choices=AccountType.choices,
    )
    account_purpose = models.CharField(
        max_length=20,
        choices=AccountPurpose.choices,
    )
    currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
    )
    opening_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class TransactionQuerySet(models.QuerySet):
    def active(self):
        """Transactions that count. Voided rows stay in the database for the
        audit trail but must never reach a total or a balance.
        """
        return self.filter(is_void=False)

    def voided(self):
        return self.filter(is_void=True)


class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"
        TRANSFER = "transfer", "Transfer"

    date = models.DateField()
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    currency = models.CharField(
        max_length=3,
        choices=Account.Currency.choices,
        blank=True,
    )
    transaction_type = models.CharField(
        max_length=10,
        choices=TransactionType.choices,
    )
    payee = models.CharField(max_length=150, blank=True)
    source_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="source_transactions",
        null=True,
        blank=True,
    )
    target_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="target_transactions",
        null=True,
        blank=True,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="transactions",
        null=True,
        blank=True,
    )
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_transactions",
    )
    is_void = models.BooleanField(default=False)
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="voided_transactions",
        null=True,
        blank=True,
    )
    void_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TransactionQuerySet.as_manager()

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["-date"], name="transaction_date_idx"),
            models.Index(fields=["transaction_type"], name="transaction_type_idx"),
        ]
        permissions = [
            ("void_transaction", "Can void a transaction"),
        ]

    def get_transaction_type_label(self):
        try:
            return self.TransactionType(self.transaction_type).label
        except ValueError:
            return self.transaction_type

    def __str__(self):
        description = self.description or "No description"
        transaction_type_label = self.get_transaction_type_label()
        return f"{transaction_type_label} - {self.amount} {self.currency} - {description}"

    def clean(self):
        super().clean()
        self._derive_currency()

        errors = {}

        if self.amount is not None and self.amount <= Decimal("0"):
            errors["amount"] = "Amount must be greater than 0."

        if self.transaction_type == self.TransactionType.INCOME:
            self._validate_income(errors)
        elif self.transaction_type == self.TransactionType.EXPENSE:
            self._validate_expense(errors)
        elif self.transaction_type == self.TransactionType.TRANSFER:
            self._validate_transfer(errors)

        if self.is_void and not (self.void_reason or "").strip():
            errors["void_reason"] = "Voiding a transaction requires a reason."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()

        if self.is_void and self.voided_at is None:
            self.voided_at = timezone.now()

        return super().save(*args, **kwargs)

    def _derive_currency(self):
        if (
            self.transaction_type == self.TransactionType.INCOME
            and self.target_account is not None
        ):
            self.currency = self.target_account.currency
        elif (
            self.transaction_type
            in (self.TransactionType.EXPENSE, self.TransactionType.TRANSFER)
            and self.source_account is not None
        ):
            # Money leaves the source account, so that account sets the
            # currency for both expenses and transfers.
            self.currency = self.source_account.currency

    def _validate_income(self, errors):
        if self.target_account is None:
            errors["target_account"] = "Income transactions require a target account."
        if (
            self.category is None
            or self.category.category_type != Category.CategoryType.INCOME
        ):
            errors["category"] = (
                "Income transactions require an income category."
            )

    def _validate_expense(self, errors):
        if self.source_account is None:
            errors["source_account"] = "Expense transactions require a source account."
        if (
            self.category is None
            or self.category.category_type != Category.CategoryType.EXPENSE
        ):
            errors["category"] = (
                "Expense transactions require an expense category."
            )

    def _validate_transfer(self, errors):
        if self.source_account is None:
            errors["source_account"] = "Transfer transactions require a source account."
        if self.target_account is None:
            errors["target_account"] = "Transfer transactions require a target account."
        if (
            self.source_account is not None
            and self.target_account is not None
            and self.source_account == self.target_account
        ):
            errors["target_account"] = "Transfer accounts must be different."
        if (
            self.source_account is not None
            and self.target_account is not None
            and self.source_account.currency != self.target_account.currency
        ):
            errors["target_account"] = (
                "Cross-currency transfers are not supported in the MVP."
            )


class Receipt(models.Model):
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="receipts",
    )
    file = models.FileField(
        upload_to="receipts/",
        validators=[validate_receipt_file],
    )
    original_filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_receipts",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        payee = self.transaction.payee

        if payee:
            return f"Receipt for {payee} - {self.original_filename}"

        return f"Receipt - {self.original_filename}"

    def clean(self):
        super().clean()

        transaction = getattr(self, "transaction", None)
        if transaction is None:
            return

        if transaction.transaction_type != Transaction.TransactionType.EXPENSE:
            raise ValidationError(
                {"transaction": "Receipt must belong to an expense transaction."}
            )

        if (
            transaction.source_account is None
            or transaction.source_account.account_type != Account.AccountType.CASH
        ):
            raise ValidationError(
                {"transaction": "Receipt must belong to a cash expense transaction."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


def get_base_currency():
    return getattr(settings, "BASE_CURRENCY", "TRY")


class ExchangeRate(models.Model):
    """How much one unit of `currency` is worth in the base currency.

    A rate of 34.00 for USD means 1 USD = 34.00 TRY. Rates are dated, and a
    lookup takes the most recent rate on or before the date being reported, so
    that back-dated reports do not silently use today's rate.
    """

    currency = models.CharField(
        max_length=3,
        choices=Account.Currency.choices,
    )
    rate_to_base = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        validators=[MinValueValidator(Decimal("0.000001"))],
    )
    effective_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-effective_date", "currency"]
        constraints = [
            models.UniqueConstraint(
                fields=["currency", "effective_date"],
                name="unique_exchange_rate_per_currency_per_date",
            )
        ]

    def __str__(self):
        return (
            f"1 {self.currency} = {self.rate_to_base} {get_base_currency()} "
            f"({self.effective_date})"
        )

    def clean(self):
        super().clean()

        if self.currency == get_base_currency():
            raise ValidationError(
                {
                    "currency": (
                        f"{get_base_currency()} is the base currency; "
                        "its rate is always 1 and must not be stored."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @classmethod
    def quote_for(cls, currency, on_date):
        """The rate row in force for `currency` on `on_date`, or None."""
        return (
            cls.objects.filter(currency=currency, effective_date__lte=on_date)
            .order_by("-effective_date")
            .first()
        )

    @classmethod
    def rate_for(cls, currency, on_date):
        """The rate as a Decimal, 1 for the base currency, None if unknown."""
        if currency == get_base_currency():
            return Decimal("1")

        quote = cls.quote_for(currency, on_date)
        return quote.rate_to_base if quote else None


class TransactionAuditLogQuerySet(models.QuerySet):
    def delete(self, *args, **kwargs):
        """Bulk delete bypasses Model.delete(), so it is blocked here too."""
        raise ValidationError("Audit log entries cannot be deleted.")


class TransactionAuditLog(models.Model):
    """Append-only record of every change to a transaction.

    Rows cannot be edited or deleted, and the transaction they describe cannot
    be deleted either. Corrections are made by editing the transaction (which
    writes a row here) or by voiding it, never by removing history.
    """

    class Action(models.TextChoices):
        CREATED = "created", "Created"
        CHANGED = "changed", "Changed"
        VOIDED = "voided", "Voided"

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.PROTECT,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=10, choices=Action.choices)
    field_name = models.CharField(max_length=50, blank=True)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    reason = models.TextField(blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="transaction_audit_logs",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TransactionAuditLogQuerySet.as_manager()

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["transaction"], name="audit_transaction_idx"),
        ]

    def __str__(self):
        who = self.performed_by.get_username()

        if self.action == self.Action.CHANGED:
            return f"{who} changed {self.field_name}: {self.old_value} -> {self.new_value}"

        return f"{who} {self.get_action_display().lower()} transaction {self.transaction_id}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("Audit log entries cannot be modified.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit log entries cannot be deleted.")

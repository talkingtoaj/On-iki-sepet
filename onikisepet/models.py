from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class Category(models.Model):
    class CategoryType(models.TextChoices):
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"

    name = models.CharField(max_length=100, unique=True)
    category_type = models.CharField(
        max_length=10,
        choices=CategoryType.choices,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def _derive_currency(self):
        if (
            self.transaction_type == self.TransactionType.INCOME
            and self.target_account is not None
        ):
            self.currency = self.target_account.currency
        elif (
            self.transaction_type == self.TransactionType.EXPENSE
            and self.source_account is not None
        ):
            self.currency = self.source_account.currency
        elif (
            self.transaction_type == self.TransactionType.TRANSFER
            and self.source_account is not None
        ):
            self.currency = self.source_account.currency

    def _validate_income(self, errors):
        if self.target_account is None:
            errors["target_account"] = "Income transactions require a target account."
        if self.category is None:
            errors["category"] = "Income transactions require an income category."
        elif self.category.category_type != Category.CategoryType.INCOME:
            errors["category"] = "Income transactions require an income category."

    def _validate_expense(self, errors):
        if self.source_account is None:
            errors["source_account"] = "Expense transactions require a source account."
        if self.category is None:
            errors["category"] = "Expense transactions require an expense category."
        elif self.category.category_type != Category.CategoryType.EXPENSE:
            errors["category"] = "Expense transactions require an expense category."

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
    file = models.FileField(upload_to="receipts/")
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

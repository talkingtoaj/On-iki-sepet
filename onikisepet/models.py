from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from onikisepet import messages as msg


class Profile(models.Model):
    class Role(models.TextChoices):
        VIEWER = "viewer", "Viewer"
        DATA_ENTRY = "data_entry", "Data Entry"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
    )

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


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

    def clean(self):
        super().clean()
        if self.pk is None:
            return

        original_balance = (
            Account.objects.filter(pk=self.pk)
            .values_list("opening_balance", flat=True)
            .first()
        )
        if (
            original_balance is not None
            and self.opening_balance != original_balance
        ):
            raise ValidationError(
                {"opening_balance": msg.OPENING_BALANCE_IMMUTABLE},
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class AccountChangeRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="change_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="account_change_requests",
    )
    proposed_name = models.CharField(max_length=100)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_account_change_requests",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.account.name} → {self.proposed_name} ({self.status})"


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

    class ApprovalStatus(models.TextChoices):
        PENDING = "pending", "Onay bekliyor"
        APPROVED = "approved", "Onaylandı"
        REJECTED = "rejected", "Reddedildi"

    approval_status = models.CharField(
        max_length=10,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.APPROVED,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_transactions",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
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
            errors["amount"] = msg.AMOUNT_MUST_BE_POSITIVE

        if self.transaction_type == self.TransactionType.INCOME:
            self._validate_income(errors)
        elif self.transaction_type == self.TransactionType.EXPENSE:
            self._validate_expense(errors)
        elif self.transaction_type == self.TransactionType.TRANSFER:
            self._validate_transfer(errors)

        if not errors:
            from onikisepet.account_rules import validate_account_purpose_for_transaction

            validate_account_purpose_for_transaction(self, errors)

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
            errors["target_account"] = msg.INCOME_REQUIRES_TARGET_ACCOUNT
        if self.category is None:
            errors["category"] = msg.INCOME_REQUIRES_INCOME_CATEGORY
        elif self.category.category_type != Category.CategoryType.INCOME:
            errors["category"] = msg.INCOME_REQUIRES_INCOME_CATEGORY

    def _validate_expense(self, errors):
        if self.source_account is None:
            errors["source_account"] = msg.EXPENSE_REQUIRES_SOURCE_ACCOUNT
        if self.category is None:
            errors["category"] = msg.EXPENSE_REQUIRES_EXPENSE_CATEGORY
        elif self.category.category_type != Category.CategoryType.EXPENSE:
            errors["category"] = msg.EXPENSE_REQUIRES_EXPENSE_CATEGORY

    def _validate_transfer(self, errors):
        if self.source_account is None:
            errors["source_account"] = msg.TRANSFER_REQUIRES_SOURCE_ACCOUNT
        if self.target_account is None:
            errors["target_account"] = msg.TRANSFER_REQUIRES_TARGET_ACCOUNT
        if (
            self.source_account is not None
            and self.target_account is not None
            and self.source_account == self.target_account
        ):
            errors["target_account"] = msg.TRANSFER_ACCOUNTS_MUST_DIFFER
        if (
            self.source_account is not None
            and self.target_account is not None
            and self.source_account.currency != self.target_account.currency
        ):
            errors["target_account"] = msg.TRANSFER_CROSS_CURRENCY_NOT_SUPPORTED


class Receipt(models.Model):
    class FileType(models.TextChoices):
        PDF = "pdf", "PDF"
        JPG = "jpg", "JPG"
        PNG = "png", "PNG"

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="receipts",
    )
    file = models.FileField(upload_to="receipts/")
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(
        max_length=10,
        choices=FileType.choices,
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_receipts",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.original_filename

    def save(self, *args, **kwargs):
        if self.original_filename:
            from onikisepet.validators import derive_receipt_file_type

            self.file_type = derive_receipt_file_type(self.original_filename)
        self.full_clean()
        return super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        errors = {}

        if self.transaction_id is None:
            errors["transaction"] = msg.RECEIPT_TRANSACTION_REQUIRED
        else:
            transaction = self.transaction
            if transaction.transaction_type != Transaction.TransactionType.EXPENSE:
                errors["transaction"] = msg.RECEIPTS_EXPENSE_ONLY
            elif transaction.source_account is None or (
                transaction.source_account.account_type
                not in (Account.AccountType.CASH, Account.AccountType.BANK)
            ):
                errors["transaction"] = msg.RECEIPTS_EXPENSE_ACCOUNT_NOT_SUPPORTED

        if errors:
            raise ValidationError(errors)


class BankStatementImport(models.Model):
    class Status(models.TextChoices):
        PREVIEW = "preview", "Preview"
        CONFIRMED = "confirmed", "Confirmed"

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bank_statement_imports",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    original_filename = models.CharField(max_length=255)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PREVIEW,
    )

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.original_filename


class BankStatementRow(models.Model):
    bank_statement_import = models.ForeignKey(
        BankStatementImport,
        on_delete=models.CASCADE,
        related_name="rows",
    )
    row_number = models.PositiveIntegerField()
    date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    currency = models.CharField(
        max_length=3,
        choices=Account.Currency.choices,
        blank=True,
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="bank_statement_rows",
        null=True,
        blank=True,
    )
    transaction_type = models.CharField(
        max_length=10,
        choices=Transaction.TransactionType.choices,
        blank=True,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="bank_statement_rows",
        null=True,
        blank=True,
    )
    target_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="bank_statement_target_rows",
        null=True,
        blank=True,
    )
    payee = models.CharField(max_length=150, blank=True)
    is_skipped = models.BooleanField(default=False)
    parse_error = models.TextField(blank=True)
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.SET_NULL,
        related_name="bank_statement_rows",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["row_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["bank_statement_import", "row_number"],
                name="unique_bank_statement_row_number",
            ),
        ]

    def __str__(self):
        return f"Row {self.row_number} - {self.description or 'No description'}"

    @property
    def is_parse_valid(self):
        return not self.parse_error


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        APPROVE = "approve", "Approve"
        REJECT = "reject", "Reject"

    content_type = models.CharField(max_length=50)
    object_id = models.PositiveIntegerField()
    action = models.CharField(max_length=10, choices=Action.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="audit_logs",
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.action} {self.content_type}#{self.object_id}"

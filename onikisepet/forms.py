from decimal import Decimal

from django import forms

from .models import Account, Category, ExchangeRate, Transaction, get_base_currency
from .validators import validate_receipt_file


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "category_type", "is_active"]

    def clean(self):
        """Surface a duplicate as an error on the name field.

        The uniqueness rule spans two columns, so Django would report it as a
        non-field error. The name is what the user would actually change, so
        the message belongs there.
        """
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        category_type = cleaned_data.get("category_type")

        if name and category_type:
            clash = Category.objects.filter(
                name=name, category_type=category_type
            ).exclude(pk=self.instance.pk)
            if clash.exists():
                self.add_error(
                    "name",
                    f"A {category_type} category named \u201c{name}\u201d already exists.",
                )

        return cleaned_data


class AccountForm(forms.ModelForm):
    opening_balance = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
    )

    class Meta:
        model = Account
        fields = [
            "name",
            "account_type",
            "account_purpose",
            "currency",
            "opening_balance",
            "is_active",
        ]

    def clean_opening_balance(self):
        return self.cleaned_data["opening_balance"] or Decimal("0")


class TransactionForm(forms.ModelForm):
    account = forms.ModelChoiceField(
        queryset=Account.objects.all(),
        required=False,
    )

    class Meta:
        model = Transaction
        fields = [
            "date",
            "amount",
            "transaction_type",
            "payee",
            "account",
            "source_account",
            "target_account",
            "category",
            "description",
        ]

    def clean(self):
        cleaned_data = super().clean()
        transaction_type = cleaned_data.get("transaction_type")
        amount = cleaned_data.get("amount")
        account = cleaned_data.get("account")
        source_account = cleaned_data.get("source_account")
        target_account = cleaned_data.get("target_account")
        category = cleaned_data.get("category")

        if amount is not None and amount <= Decimal("0"):
            self.add_error("amount", "Amount must be greater than 0.")

        if transaction_type == Transaction.TransactionType.INCOME:
            self._clean_income(cleaned_data, account, category)
        elif transaction_type == Transaction.TransactionType.EXPENSE:
            self._clean_expense(cleaned_data, account, category)
        elif transaction_type == Transaction.TransactionType.TRANSFER:
            self._clean_transfer(source_account, target_account)

        return cleaned_data

    def _clean_income(self, cleaned_data, account, category):
        if account is None:
            self.add_error("account", "Income transactions require an account.")
            return

        cleaned_data["target_account"] = account
        cleaned_data["source_account"] = None
        self.instance.target_account = account
        self.instance.source_account = None

        if (
            category is None
            or category.category_type != Category.CategoryType.INCOME
        ):
            self.add_error(
                "category",
                "Income transactions require an income category.",
            )

    def _clean_expense(self, cleaned_data, account, category):
        if account is None:
            self.add_error("account", "Expense transactions require an account.")
            return

        cleaned_data["source_account"] = account
        cleaned_data["target_account"] = None
        self.instance.source_account = account
        self.instance.target_account = None

        if (
            category is None
            or category.category_type != Category.CategoryType.EXPENSE
        ):
            self.add_error(
                "category",
                "Expense transactions require an expense category.",
            )

    def _clean_transfer(self, source_account, target_account):
        if source_account is None:
            self.add_error(
                "source_account",
                "Transfer transactions require a source account.",
            )
        if target_account is None:
            self.add_error(
                "target_account",
                "Transfer transactions require a target account.",
            )
        if source_account is None or target_account is None:
            return

        if source_account == target_account:
            self.add_error("target_account", "Transfer accounts must be different.")
        elif source_account.currency != target_account.currency:
            self.add_error(
                "target_account",
                "Cross-currency transfers are not supported in the MVP.",
            )


class CashExpenseForm(forms.Form):
    date = forms.DateField()
    payee = forms.CharField(max_length=150)
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    cash_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(
            account_type=Account.AccountType.CASH,
            is_active=True,
        )
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(
            category_type=Category.CategoryType.EXPENSE,
            is_active=True,
        )
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea,
    )
    receipt_file = forms.FileField(validators=[validate_receipt_file])

    def get_transaction_data(self):
        cash_account = self.cleaned_data["cash_account"]
        return {
            "date": self.cleaned_data["date"],
            "payee": self.cleaned_data["payee"],
            "amount": self.cleaned_data["amount"],
            "transaction_type": Transaction.TransactionType.EXPENSE,
            "source_account": cash_account,
            "target_account": None,
            "category": self.cleaned_data["category"],
            "currency": cash_account.currency,
            "description": self.cleaned_data.get("description", ""),
        }

    def get_receipt_file(self):
        return self.cleaned_data["receipt_file"]

    def get_original_filename(self):
        return self.cleaned_data["receipt_file"].name


class ExchangeRateForm(forms.ModelForm):
    class Meta:
        model = ExchangeRate
        fields = ["currency", "rate_to_base", "effective_date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_currency = get_base_currency()
        self.fields["currency"].choices = [
            (value, label)
            for value, label in Account.Currency.choices
            if value != base_currency
        ]


class TransactionEditForm(TransactionForm):
    """Editing an existing transaction always requires a stated reason, which
    is stored on the audit row rather than on the transaction itself.
    """

    change_reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Why is this being changed? Recorded in the audit trail.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instance = self.instance
        if instance is not None and instance.pk:
            # TransactionForm collapses source/target into one `account` field
            # for income and expense, so prefill it from whichever side is set.
            self.fields["account"].initial = (
                instance.target_account
                if instance.transaction_type == Transaction.TransactionType.INCOME
                else instance.source_account
            )

    def clean_change_reason(self):
        reason = (self.cleaned_data.get("change_reason") or "").strip()
        if not reason:
            raise forms.ValidationError("A reason is required for every change.")
        return reason


class TransactionVoidForm(forms.Form):
    void_reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Why is this transaction being voided?",
    )

    def clean_void_reason(self):
        reason = (self.cleaned_data.get("void_reason") or "").strip()
        if not reason:
            raise forms.ValidationError("A reason is required to void a transaction.")
        return reason

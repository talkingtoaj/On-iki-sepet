from decimal import Decimal
from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError

from .account_rules import transfer_source_accounts, transfer_target_accounts
from .models import Account, Category, Transaction

ALLOWED_RECEIPT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MONEY_FIELD_KWARGS = {
    "max_digits": 12,
    "decimal_places": 2,
}
POSITIVE_MONEY_FIELD_KWARGS = {
    **MONEY_FIELD_KWARGS,
    "min_value": Decimal("0.01"),
}


def validate_receipt_file_extension(uploaded_file):
    extension = Path(uploaded_file.name).suffix.lower()

    if extension not in ALLOWED_RECEIPT_EXTENSIONS:
        raise ValidationError(
            "Unsupported receipt file type. Please upload a PDF, JPG, JPEG, or PNG file."
        )


def active_accounts(**filters):
    return Account.objects.filter(is_active=True, **filters)


def active_categories(category_type):
    return Category.objects.filter(
        category_type=category_type,
        is_active=True,
    )


def optional_description_field(**kwargs):
    return forms.CharField(
        required=False,
        widget=forms.Textarea,
        **kwargs,
    )


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "category_type", "is_active"]


class AccountForm(forms.ModelForm):
    opening_balance = forms.DecimalField(
        **MONEY_FIELD_KWARGS,
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

        if category is None:
            self.add_error("category", "Income transactions require an income category.")
        elif category.category_type != Category.CategoryType.INCOME:
            self.add_error("category", "Income transactions require an income category.")

    def _clean_expense(self, cleaned_data, account, category):
        if account is None:
            self.add_error("account", "Expense transactions require an account.")
            return

        cleaned_data["source_account"] = account
        cleaned_data["target_account"] = None
        self.instance.source_account = account
        self.instance.target_account = None

        if category is None:
            self.add_error("category", "Expense transactions require an expense category.")
        elif category.category_type != Category.CategoryType.EXPENSE:
            self.add_error("category", "Expense transactions require an expense category.")

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


class TransactionEditForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            "date",
            "amount",
            "payee",
            "source_account",
            "target_account",
            "category",
            "description",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        transaction_type = self.instance.transaction_type
        if transaction_type == Transaction.TransactionType.INCOME:
            self.fields.pop("source_account", None)
        elif transaction_type == Transaction.TransactionType.EXPENSE:
            self.fields.pop("target_account", None)
        elif transaction_type == Transaction.TransactionType.TRANSFER:
            self.fields.pop("category", None)
            self.fields.pop("payee", None)


class CashExpenseForm(forms.Form):
    date = forms.DateField()
    payee = forms.CharField(max_length=150)
    amount = forms.DecimalField(**POSITIVE_MONEY_FIELD_KWARGS)
    cash_account = forms.ModelChoiceField(
        queryset=active_accounts(
            account_type=Account.AccountType.CASH,
        )
    )
    category = forms.ModelChoiceField(
        queryset=active_categories(Category.CategoryType.EXPENSE)
    )
    description = optional_description_field()
    receipt_file = forms.FileField()

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

    def clean_receipt_file(self):
        receipt_file = self.cleaned_data.get("receipt_file")

        if receipt_file:
            validate_receipt_file_extension(receipt_file)

        return receipt_file


class BankExpenseForm(forms.Form):
    date = forms.DateField()
    payee = forms.CharField(max_length=150)
    amount = forms.DecimalField(**POSITIVE_MONEY_FIELD_KWARGS)
    bank_account = forms.ModelChoiceField(
        queryset=active_accounts(
            account_type=Account.AccountType.BANK,
            account_purpose=Account.AccountPurpose.MAIN_EXPENSE,
        )
    )
    category = forms.ModelChoiceField(
        queryset=active_categories(Category.CategoryType.EXPENSE)
    )
    description = optional_description_field()

    def get_transaction_data(self):
        bank_account = self.cleaned_data["bank_account"]
        return {
            "date": self.cleaned_data["date"],
            "payee": self.cleaned_data["payee"],
            "amount": self.cleaned_data["amount"],
            "transaction_type": Transaction.TransactionType.EXPENSE,
            "source_account": bank_account,
            "target_account": None,
            "category": self.cleaned_data["category"],
            "currency": bank_account.currency,
            "description": self.cleaned_data.get("description", ""),
        }


class CashIncomeForm(forms.Form):
    date = forms.DateField(label="Tarih")
    donor_name = forms.CharField(max_length=150, label="Bağışçı adı")
    amount = forms.DecimalField(
        **POSITIVE_MONEY_FIELD_KWARGS,
        label="Tutar",
    )
    cash_account = forms.ModelChoiceField(
        label="Kasa hesabı",
        queryset=active_accounts(
            account_type=Account.AccountType.CASH,
            account_purpose=Account.AccountPurpose.CASH,
        ),
    )
    category = forms.ModelChoiceField(
        label="Kategori",
        queryset=active_categories(Category.CategoryType.INCOME),
    )
    description = optional_description_field(label="Açıklama")

    def get_transaction_data(self):
        cash_account = self.cleaned_data["cash_account"]
        return {
            "date": self.cleaned_data["date"],
            "payee": self.cleaned_data["donor_name"],
            "amount": self.cleaned_data["amount"],
            "transaction_type": Transaction.TransactionType.INCOME,
            "source_account": None,
            "target_account": cash_account,
            "category": self.cleaned_data["category"],
            "currency": cash_account.currency,
            "description": self.cleaned_data.get("description", ""),
        }


class OnlineDonationIncomeForm(forms.Form):
    date = forms.DateField()
    donor_name = forms.CharField(max_length=150)
    amount = forms.DecimalField(**POSITIVE_MONEY_FIELD_KWARGS)
    online_donation_account = forms.ModelChoiceField(
        queryset=active_accounts(
            account_type=Account.AccountType.BANK,
            account_purpose=Account.AccountPurpose.ONLINE_DONATION,
        )
    )
    category = forms.ModelChoiceField(
        queryset=active_categories(Category.CategoryType.INCOME)
    )
    description = optional_description_field()

    def get_transaction_data(self):
        online_donation_account = self.cleaned_data["online_donation_account"]
        return {
            "date": self.cleaned_data["date"],
            "payee": self.cleaned_data["donor_name"],
            "amount": self.cleaned_data["amount"],
            "transaction_type": Transaction.TransactionType.INCOME,
            "source_account": None,
            "target_account": online_donation_account,
            "category": self.cleaned_data["category"],
            "currency": online_donation_account.currency,
            "description": self.cleaned_data.get("description", ""),
        }


class TransferForm(forms.Form):
    date = forms.DateField()
    amount = forms.DecimalField(**POSITIVE_MONEY_FIELD_KWARGS)
    source_account = forms.ModelChoiceField(
        queryset=transfer_source_accounts()
    )
    target_account = forms.ModelChoiceField(
        queryset=transfer_target_accounts()
    )
    description = optional_description_field()

    def clean(self):
        cleaned_data = super().clean()
        source_account = cleaned_data.get("source_account")
        target_account = cleaned_data.get("target_account")

        if source_account is None or target_account is None:
            return cleaned_data

        if source_account == target_account:
            self.add_error("target_account", "Transfer accounts must be different.")
        elif source_account.currency != target_account.currency:
            self.add_error(
                "target_account",
                "Cross-currency transfers are not supported in the MVP.",
            )

        return cleaned_data

    def get_transaction_data(self):
        source_account = self.cleaned_data["source_account"]
        return {
            "date": self.cleaned_data["date"],
            "amount": self.cleaned_data["amount"],
            "transaction_type": Transaction.TransactionType.TRANSFER,
            "source_account": source_account,
            "target_account": self.cleaned_data["target_account"],
            "category": None,
            "payee": "",
            "currency": source_account.currency,
            "description": self.cleaned_data.get("description", ""),
        }

from decimal import Decimal
from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError

from onikisepet import messages as msg

from .account_rules import transfer_source_accounts, transfer_target_accounts
from .constants import MONEY_FIELD_KWARGS, POSITIVE_MONEY_FIELD_KWARGS
from .models import Account, BankStatementRow, Category, Transaction
from .selectors import active_accounts, active_categories
from .validators import validate_bank_import_file_extension, validate_receipt_file_extension


def apply_form_control_styles(form):
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            css_class = "form-check-input"
        elif isinstance(widget, forms.FileInput):
            css_class = "form-control form-control--file"
        elif isinstance(widget, forms.Textarea):
            css_class = "form-control form-control--textarea"
        else:
            css_class = "form-control"
        existing = widget.attrs.get("class", "")
        widget.attrs["class"] = f"{existing} {css_class}".strip()


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_form_control_styles(self)


def optional_description_field(**kwargs):
    return forms.CharField(
        required=False,
        widget=forms.Textarea,
        **kwargs,
    )


def _apply_model_validation_errors(form, instance, field_map=None):
    field_map = field_map or {}
    try:
        instance.clean()
    except ValidationError as exc:
        for field, messages in exc.error_dict.items():
            form_field = field_map.get(field, field)
            for message in messages:
                form.add_error(form_field, message)


class CategoryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "category_type", "is_active"]


class AccountForm(StyledFormMixin, forms.ModelForm):
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields.pop("opening_balance", None)

    def clean_opening_balance(self):
        return self.cleaned_data["opening_balance"] or Decimal("0")


class AccountChangeRequestForm(StyledFormMixin, forms.Form):
    proposed_name = forms.CharField(max_length=100, label="Önerilen hesap adı")


class AccountChangeRequestRejectForm(StyledFormMixin, forms.Form):
    rejection_reason = forms.CharField(
        label="Red nedeni",
        widget=forms.Textarea,
        error_messages={"required": msg.REJECTION_REASON_REQUIRED},
    )


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
        if self.errors:
            return cleaned_data

        transaction_type = cleaned_data.get("transaction_type")
        account = cleaned_data.get("account")

        if transaction_type == Transaction.TransactionType.INCOME:
            self._map_income_account(cleaned_data, account)
        elif transaction_type == Transaction.TransactionType.EXPENSE:
            self._map_expense_account(cleaned_data, account)

        if self.errors:
            return cleaned_data

        field_map = {}
        if transaction_type == Transaction.TransactionType.INCOME:
            field_map["target_account"] = "account"
        elif transaction_type == Transaction.TransactionType.EXPENSE:
            field_map["source_account"] = "account"

        _apply_model_validation_errors(self, self.instance, field_map)
        return cleaned_data

    def _map_income_account(self, cleaned_data, account):
        if account is None:
            self.add_error("account", msg.INCOME_REQUIRES_ACCOUNT)
            return

        cleaned_data["target_account"] = account
        cleaned_data["source_account"] = None
        self.instance.target_account = account
        self.instance.source_account = None

    def _map_expense_account(self, cleaned_data, account):
        if account is None:
            self.add_error("account", msg.EXPENSE_REQUIRES_ACCOUNT)
            return

        cleaned_data["source_account"] = account
        cleaned_data["target_account"] = None
        self.instance.source_account = account
        self.instance.target_account = None


class TransactionEditForm(StyledFormMixin, forms.ModelForm):
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


class TransactionRejectForm(StyledFormMixin, forms.Form):
    rejection_reason = forms.CharField(
        label="Red nedeni",
        widget=forms.Textarea,
        error_messages={"required": msg.REJECTION_REASON_REQUIRED},
    )


class CashExpenseForm(StyledFormMixin, forms.Form):
    date = forms.DateField(label="Tarih")
    payee = forms.CharField(max_length=150, label="Alıcı")
    amount = forms.DecimalField(
        **POSITIVE_MONEY_FIELD_KWARGS,
        label="Tutar",
        help_text="En az 0,01",
    )
    cash_account = forms.ModelChoiceField(
        label="Kasa hesabı",
        queryset=active_accounts(
            account_type=Account.AccountType.CASH,
        ),
    )
    category = forms.ModelChoiceField(
        label="Kategori",
        queryset=active_categories(Category.CategoryType.EXPENSE),
    )
    description = optional_description_field(label="Açıklama")
    receipt_file = forms.FileField(
        label="Makbuz dosyası",
        help_text="PDF, JPG, JPEG veya PNG",
    )

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

    def clean_receipt_file(self):
        receipt_file = self.cleaned_data.get("receipt_file")

        if receipt_file:
            validate_receipt_file_extension(receipt_file)

        return receipt_file


class BankExpenseForm(StyledFormMixin, forms.Form):
    date = forms.DateField(label="Tarih")
    payee = forms.CharField(max_length=150, label="Alıcı")
    amount = forms.DecimalField(
        **POSITIVE_MONEY_FIELD_KWARGS,
        label="Tutar",
        help_text="En az 0,01",
    )
    bank_account = forms.ModelChoiceField(
        label="Banka hesabı",
        queryset=active_accounts(
            account_type=Account.AccountType.BANK,
            account_purpose=Account.AccountPurpose.MAIN_EXPENSE,
        ),
    )
    category = forms.ModelChoiceField(
        label="Kategori",
        queryset=active_categories(Category.CategoryType.EXPENSE),
    )
    description = optional_description_field(label="Açıklama")
    receipt_file = forms.FileField(
        label="Dekont dosyası",
        required=False,
        help_text="PDF, JPG, JPEG veya PNG (isteğe bağlı)",
    )

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

    def clean_receipt_file(self):
        receipt_file = self.cleaned_data.get("receipt_file")

        if receipt_file:
            validate_receipt_file_extension(receipt_file)

        return receipt_file


class CashIncomeForm(StyledFormMixin, forms.Form):
    date = forms.DateField(label="Tarih")
    donor_name = forms.CharField(max_length=150, label="Bağışçı adı")
    amount = forms.DecimalField(
        **POSITIVE_MONEY_FIELD_KWARGS,
        label="Tutar",
        help_text="En az 0,01",
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


class OnlineDonationIncomeForm(StyledFormMixin, forms.Form):
    date = forms.DateField(label="Tarih")
    donor_name = forms.CharField(max_length=150, label="Bağışçı adı")
    amount = forms.DecimalField(
        **POSITIVE_MONEY_FIELD_KWARGS,
        label="Tutar",
        help_text="En az 0,01",
    )
    online_donation_account = forms.ModelChoiceField(
        label="Online bağış hesabı",
        queryset=active_accounts(
            account_type=Account.AccountType.BANK,
            account_purpose=Account.AccountPurpose.ONLINE_DONATION,
        ),
    )
    category = forms.ModelChoiceField(
        label="Kategori",
        queryset=active_categories(Category.CategoryType.INCOME),
    )
    description = optional_description_field(label="Açıklama")

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


class TransferForm(StyledFormMixin, forms.Form):
    date = forms.DateField(label="Tarih")
    amount = forms.DecimalField(
        **POSITIVE_MONEY_FIELD_KWARGS,
        label="Tutar",
        help_text="En az 0,01",
    )
    source_account = forms.ModelChoiceField(
        label="Kaynak hesap",
        queryset=transfer_source_accounts(),
    )
    target_account = forms.ModelChoiceField(
        label="Hedef hesap",
        queryset=transfer_target_accounts(),
        help_text="Kaynak ve hedef farklı hesaplar olmalıdır.",
    )
    description = optional_description_field(label="Açıklama")

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data

        source_account = cleaned_data.get("source_account")
        if source_account is None:
            return cleaned_data

        instance = Transaction(
            date=cleaned_data["date"],
            amount=cleaned_data["amount"],
            transaction_type=Transaction.TransactionType.TRANSFER,
            source_account=source_account,
            target_account=cleaned_data.get("target_account"),
            payee="",
            description=cleaned_data.get("description", ""),
        )
        _apply_model_validation_errors(self, instance)
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


class BankStatementUploadForm(StyledFormMixin, forms.Form):
    file = forms.FileField(label="Ekstre dosyası (CSV, Excel veya PDF)")
    default_account = forms.ModelChoiceField(
        label="Hesap",
        queryset=active_accounts(account_type=Account.AccountType.BANK),
        required=False,
        help_text="PDF ekstreler için zorunludur (ör. Enpara).",
    )

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        validate_bank_import_file_extension(uploaded_file)
        return uploaded_file

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data

        uploaded_file = cleaned_data.get("file")
        default_account = cleaned_data.get("default_account")
        if (
            uploaded_file
            and Path(uploaded_file.name).suffix.lower() == ".pdf"
            and default_account is None
        ):
            self.add_error("default_account", msg.BANK_IMPORT_PDF_REQUIRES_ACCOUNT)

        return cleaned_data


class BankStatementRowClassificationForm(StyledFormMixin, forms.ModelForm):
    skip_row = forms.BooleanField(required=False, label="Satırı atla")

    class Meta:
        model = BankStatementRow
        fields = ["transaction_type", "category", "target_account", "payee"]
        labels = {
            "transaction_type": "İşlem türü",
            "category": "Kategori",
            "target_account": "Hedef hesap",
            "payee": "Muhatap",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["transaction_type"].required = False
        self.fields["category"].required = False
        self.fields["target_account"].required = False
        self.fields["payee"].required = False
        self.fields["category"].queryset = Category.objects.filter(is_active=True)
        self.fields["target_account"].queryset = transfer_target_accounts()

        if self.instance and self.instance.parse_error:
            for field_name in ("transaction_type", "category", "target_account", "payee"):
                self.fields[field_name].disabled = True
            self.fields["skip_row"].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data

        if self.instance and self.instance.parse_error:
            return cleaned_data

        skip_row = cleaned_data.get("skip_row", False)
        transaction_type = cleaned_data.get("transaction_type")

        if skip_row:
            return cleaned_data

        if not transaction_type:
            self.add_error("transaction_type", msg.BANK_IMPORT_ROW_REQUIRES_TYPE.format(
                row_number=self.instance.row_number,
            ))
            return cleaned_data

        if transaction_type in (
            Transaction.TransactionType.INCOME,
            Transaction.TransactionType.EXPENSE,
        ):
            category = cleaned_data.get("category")
            if category is None:
                self.add_error(
                    "category",
                    msg.BANK_IMPORT_ROW_REQUIRES_CATEGORY.format(
                        row_number=self.instance.row_number,
                    ),
                )
            elif transaction_type == Transaction.TransactionType.INCOME and (
                category.category_type != Category.CategoryType.INCOME
            ):
                self.add_error("category", msg.INCOME_REQUIRES_INCOME_CATEGORY)
            elif transaction_type == Transaction.TransactionType.EXPENSE and (
                category.category_type != Category.CategoryType.EXPENSE
            ):
                self.add_error("category", msg.EXPENSE_REQUIRES_EXPENSE_CATEGORY)

        if transaction_type == Transaction.TransactionType.TRANSFER:
            target_account = cleaned_data.get("target_account")
            if target_account is None:
                self.add_error(
                    "target_account",
                    msg.BANK_IMPORT_ROW_REQUIRES_TARGET_ACCOUNT.format(
                        row_number=self.instance.row_number,
                    ),
                )
            elif target_account == self.instance.account:
                self.add_error("target_account", msg.TRANSFER_ACCOUNTS_MUST_DIFFER)

        return cleaned_data

    def save(self, commit=True):
        row = super().save(commit=False)
        row.is_skipped = self.cleaned_data.get("skip_row", False)
        if commit:
            row.save()
        return row

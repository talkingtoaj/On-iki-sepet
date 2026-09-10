from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Account,
    Category,
    ExchangeRate,
    Receipt,
    Transaction,
    TransactionAuditLog,
)
from .usecases import audit


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "category_type", "is_active", "created_at", "updated_at"]
    list_filter = ["category_type", "is_active"]
    search_fields = ["name"]
    ordering = ["name"]


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "account_type",
        "account_purpose",
        "currency",
        "opening_balance",
        "is_active",
        "created_at",
        "updated_at",
    ]
    list_filter = ["account_type", "account_purpose", "currency", "is_active"]
    search_fields = ["name"]
    ordering = ["name"]


class TransactionAuditLogInline(admin.TabularInline):
    """The audit trail, shown but never editable."""

    model = TransactionAuditLog
    extra = 0
    can_delete = False
    fields = [
        "created_at",
        "performed_by",
        "action",
        "field_name",
        "old_value",
        "new_value",
        "reason",
    ]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    inlines = [TransactionAuditLogInline]
    list_display = [
        "date",
        "transaction_type",
        "payee",
        "amount",
        "currency",
        "source_account",
        "target_account",
        "category",
        "created_by",
        "created_at",
        "updated_at",
    ]
    list_filter = [
        "transaction_type",
        "currency",
        "date",
        "category",
        "source_account",
        "target_account",
        "created_by",
    ]
    search_fields = [
        "payee",
        "description",
        "source_account__name",
        "target_account__name",
        "category__name",
        "created_by__username",
    ]
    ordering = ["-date", "-created_at"]
    readonly_fields = ["created_at", "updated_at"]

    def save_model(self, request, obj, form, change):
        """The admin is a write path too, so it records audit rows as well.

        Without this, a change made in the admin would leave no trace, which
        would defeat the point of having an audit trail at all.
        """
        if not getattr(obj, "created_by", None):
            obj.created_by = request.user

        if change:
            previous = Transaction.objects.get(pk=obj.pk)
            super().save_model(request, obj, form, change)
            changes = audit.diff_transactions(previous, obj)
            audit.record_changes(obj, request.user, changes, "Changed in admin")
        else:
            super().save_model(request, obj, form, change)
            audit.record_created(obj, request.user)

    def has_delete_permission(self, request, obj=None):
        """Transactions are voided, never deleted."""
        return False


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = [
        "transaction",
        "original_filename",
        "file_link",
        "uploaded_by",
        "uploaded_at",
    ]
    list_filter = [
        "uploaded_at",
        "uploaded_by",
    ]
    search_fields = [
        "original_filename",
        "transaction__payee",
        "transaction__description",
        "uploaded_by__username",
    ]
    readonly_fields = [
        "uploaded_at",
    ]

    @admin.display(description="File")
    def file_link(self, receipt):
        """A working link to the stored file. Listing only the filename gave
        reviewers no way to actually open the receipt.
        """
        if not receipt.file:
            return "-"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Open</a>', receipt.file.url
        )


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ["currency", "rate_to_base", "effective_date", "created_at"]
    list_filter = ["currency", "effective_date"]
    ordering = ["-effective_date", "currency"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(TransactionAuditLog)
class TransactionAuditLogAdmin(admin.ModelAdmin):
    """Read-only everywhere. Audit rows are append-only by design."""

    list_display = [
        "created_at",
        "transaction",
        "action",
        "field_name",
        "old_value",
        "new_value",
        "performed_by",
    ]
    list_filter = ["action", "performed_by", "created_at"]
    search_fields = [
        "field_name",
        "reason",
        "transaction__payee",
        "performed_by__username",
    ]

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

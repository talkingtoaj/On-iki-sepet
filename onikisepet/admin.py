from django.contrib import admin

from .models import (
    Account,
    AccountChangeRequest,
    AuditLog,
    BankStatementImport,
    BankStatementRow,
    Category,
    Profile,
    Receipt,
    Transaction,
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "role"]
    list_filter = ["role"]
    search_fields = ["user__username", "user__email"]
    ordering = ["user__username"]


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

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            readonly_fields.append("opening_balance")
        return readonly_fields


@admin.register(AccountChangeRequest)
class AccountChangeRequestAdmin(admin.ModelAdmin):
    list_display = [
        "account",
        "proposed_name",
        "status",
        "requested_by",
        "approved_by",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["account__name", "proposed_name", "requested_by__username"]
    ordering = ["-created_at"]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        "date",
        "transaction_type",
        "payee",
        "amount",
        "currency",
        "source_account",
        "target_account",
        "category",
        "approval_status",
        "approved_by",
        "created_by",
        "created_at",
        "updated_at",
    ]
    list_filter = [
        "transaction_type",
        "approval_status",
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
    readonly_fields = ["created_at", "updated_at", "approved_at"]

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if not change:
            from onikisepet.usecases import approval

            if not getattr(obj, "created_by", None):
                obj.created_by = request.user
            approval.apply_initial_approval(obj, request.user)
        super().save_model(request, obj, form, change)


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = [
        "transaction",
        "original_filename",
        "file_type",
        "uploaded_by",
        "uploaded_at",
    ]
    list_filter = [
        "file_type",
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

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BankStatementImport)
class BankStatementImportAdmin(admin.ModelAdmin):
    list_display = [
        "original_filename",
        "status",
        "uploaded_by",
        "uploaded_at",
    ]
    list_filter = ["status", "uploaded_at", "uploaded_by"]
    search_fields = ["original_filename", "uploaded_by__username"]
    readonly_fields = ["uploaded_at"]
    ordering = ["-uploaded_at"]


@admin.register(BankStatementRow)
class BankStatementRowAdmin(admin.ModelAdmin):
    list_display = [
        "bank_statement_import",
        "row_number",
        "date",
        "amount",
        "currency",
        "account",
        "transaction_type",
        "is_skipped",
        "parse_error",
    ]
    list_filter = [
        "transaction_type",
        "currency",
        "is_skipped",
        "bank_statement_import",
    ]
    search_fields = [
        "description",
        "parse_error",
        "bank_statement_import__original_filename",
    ]
    ordering = ["bank_statement_import", "row_number"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        "changed_at",
        "action",
        "content_type",
        "object_id",
        "changed_by",
    ]
    list_filter = ["action", "content_type", "changed_by"]
    readonly_fields = [
        "content_type",
        "object_id",
        "action",
        "changed_by",
        "changed_at",
        "before",
        "after",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

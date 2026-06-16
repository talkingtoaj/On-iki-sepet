from django.contrib import admin

from .models import Account, AuditLog, Category, Receipt, Transaction


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

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if not getattr(obj, "created_by", None):
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = [
        "transaction",
        "original_filename",
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

    def has_delete_permission(self, request, obj=None):
        return False


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

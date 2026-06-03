from importlib import import_module
from decimal import Decimal
from typing import Any, cast

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Model

from onikisepet.models import Category


class CategoryTestMixin:
    APP_LABEL = "onikisepet"
    MODEL_NAME = "Category"

    @classmethod
    def get_category_model(cls) -> type[Category]:
        try:
            model = apps.get_model(cls.APP_LABEL, cls.MODEL_NAME)
        except LookupError as exc:
            raise AssertionError(
                "Category model must be implemented as onikisepet.Category."
            ) from exc

        if model is None:
            raise AssertionError(
                "Category model must be implemented as onikisepet.Category."
            )
        return cast(type[Category], model)

    @classmethod
    def get_category_form_class(cls):
        try:
            forms_module = import_module("onikisepet.forms")
        except ModuleNotFoundError as exc:
            raise AssertionError(
                "Create onikisepet.forms module and define CategoryForm."
            ) from exc

        try:
            return getattr(forms_module, "CategoryForm")
        except AttributeError as exc:
            raise AssertionError(
                "CategoryForm must be defined in onikisepet.forms."
            ) from exc

    @staticmethod
    def _resolve_type_field_name(field_names):
        if "category_type" in field_names:
            return "category_type"
        if "type" in field_names:
            return "type"
        raise AssertionError(
            "Category must define a `category_type` or `type` field."
        )

    @classmethod
    def get_category_type_field_name(cls):
        category_model = cls.get_category_model()
        field_names = {field.name for field in category_model._meta.fields}
        return cls._resolve_type_field_name(field_names)

    @classmethod
    def build_category_kwargs(
        cls,
        *,
        name="Donation",
        category_type="income",
        is_active=True,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "name": name,
            cls.get_category_type_field_name(): category_type,
        }
        if is_active is not None:
            kwargs["is_active"] = is_active
        return kwargs

    @classmethod
    def create_category(
        cls,
        *,
        name="Donation",
        category_type="income",
        is_active=True,
    ) -> Category:
        category_model = cls.get_category_model()
        return cast(
            Category,
            category_model.objects.create(
                **cls.build_category_kwargs(
                    name=name,
                    category_type=category_type,
                    is_active=is_active,
                ),
            ),
        )


class AccountTestMixin:
    APP_LABEL = "onikisepet"
    MODEL_NAME = "Account"

    @classmethod
    def get_account_model(cls) -> type[Model]:
        try:
            model = apps.get_model(cls.APP_LABEL, cls.MODEL_NAME)
        except LookupError as exc:
            raise AssertionError(
                "Account model must be implemented as onikisepet.Account."
            ) from exc

        if model is None:
            raise AssertionError(
                "Account model must be implemented as onikisepet.Account."
            )
        return cast(type[Model], model)

    @classmethod
    def get_account_form_class(cls):
        try:
            forms_module = import_module("onikisepet.forms")
        except ModuleNotFoundError as exc:
            raise AssertionError(
                "Create onikisepet.forms module and define AccountForm."
            ) from exc

        try:
            return getattr(forms_module, "AccountForm")
        except AttributeError as exc:
            raise AssertionError(
                "AccountForm must be defined in onikisepet.forms."
            ) from exc

    @classmethod
    def build_account_kwargs(
        cls,
        *,
        name="Cash Account",
        account_type="cash",
        account_purpose="cash",
        currency="TRY",
        is_active=True,
        opening_balance: Decimal | None = Decimal("0.00"),
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "name": name,
            "account_type": account_type,
            "account_purpose": account_purpose,
            "currency": currency,
        }
        if is_active is not None:
            kwargs["is_active"] = is_active
        if opening_balance is not None:
            kwargs["opening_balance"] = opening_balance
        return kwargs

    @classmethod
    def create_account(
        cls,
        *,
        name="Cash Account",
        account_type="cash",
        account_purpose="cash",
        currency="TRY",
        is_active=True,
        opening_balance: Decimal | None = Decimal("0.00"),
    ) -> Model:
        account_model = cls.get_account_model()
        return cast(
            Model,
            account_model.objects.create(
                **cls.build_account_kwargs(
                    name=name,
                    account_type=account_type,
                    account_purpose=account_purpose,
                    currency=currency,
                    is_active=is_active,
                    opening_balance=opening_balance,
                ),
            ),
        )


class TransactionTestMixin:
    password = "StrongTestPass123!"

    @classmethod
    def get_transaction_model(cls) -> type[Model]:
        try:
            model = apps.get_model("onikisepet", "Transaction")
        except LookupError as exc:
            raise AssertionError(
                "Transaction model must be implemented as onikisepet.Transaction."
            ) from exc

        if model is None:
            raise AssertionError(
                "Transaction model must be implemented as onikisepet.Transaction."
            )
        return cast(type[Model], model)

    @classmethod
    def get_transaction_form_class(cls):
        try:
            forms_module = import_module("onikisepet.forms")
        except ModuleNotFoundError as exc:
            raise AssertionError(
                "Create onikisepet.forms module and define TransactionForm."
            ) from exc

        try:
            return getattr(forms_module, "TransactionForm")
        except AttributeError as exc:
            raise AssertionError(
                "TransactionForm must be defined in onikisepet.forms."
            ) from exc

    @classmethod
    def get_account_model(cls) -> type[Model]:
        try:
            model = apps.get_model("onikisepet", "Account")
        except LookupError as exc:
            raise AssertionError(
                "Account model must be implemented as onikisepet.Account."
            ) from exc
        return cast(type[Model], model)

    @classmethod
    def get_category_model(cls) -> type[Model]:
        try:
            model = apps.get_model("onikisepet", "Category")
        except LookupError as exc:
            raise AssertionError(
                "Category model must be implemented as onikisepet.Category."
            ) from exc
        return cast(type[Model], model)

    @classmethod
    def create_user(cls, username="test_user", *, is_superuser=False, group_name=None):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password=cls.password,
            is_staff=is_superuser,
            is_superuser=is_superuser,
        )
        if group_name:
            group, _ = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)
        return user

    @classmethod
    def create_account(
        cls,
        *,
        name="Cash Account",
        account_type="cash",
        account_purpose="cash",
        currency="TRY",
        opening_balance: Decimal | None = Decimal("0.00"),
    ) -> Model:
        account_model = cls.get_account_model()
        kwargs: dict[str, Any] = {
            "name": name,
            "account_type": account_type,
            "account_purpose": account_purpose,
            "currency": currency,
        }
        if opening_balance is not None:
            kwargs["opening_balance"] = opening_balance

        return cast(
            Model,
            account_model.objects.create(**kwargs),
        )

    @classmethod
    def create_category(cls, *, name="Donation", category_type="income") -> Model:
        category_model = cls.get_category_model()
        return cast(
            Model,
            category_model.objects.create(name=name, category_type=category_type),
        )

    @classmethod
    def build_transaction_kwargs(
        cls,
        *,
        date="2026-05-30",
        amount: Decimal | None = Decimal("10.00"),
        transaction_type="income",
        source_account=None,
        target_account=None,
        category=None,
        description="Test transaction",
        created_by=None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "date": date,
            "transaction_type": transaction_type,
            "description": description,
        }
        if amount is not None:
            kwargs["amount"] = amount
        if source_account is not None:
            kwargs["source_account"] = source_account
        if target_account is not None:
            kwargs["target_account"] = target_account
        if category is not None:
            kwargs["category"] = category
        if created_by is not None:
            kwargs["created_by"] = created_by
        return kwargs

    @classmethod
    def create_transaction(cls, **kwargs) -> Model:
        transaction_model = cls.get_transaction_model()
        return cast(
            Model,
            transaction_model.objects.create(**cls.build_transaction_kwargs(**kwargs)),
        )

    @classmethod
    def get_financial_calculations_module(cls):
        try:
            return import_module("onikisepet.services.financial_calculations")
        except ModuleNotFoundError as exc:
            raise AssertionError(
                "Create onikisepet.services.financial_calculations for transaction totals and balances."
            ) from exc

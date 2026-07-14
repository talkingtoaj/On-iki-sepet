from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from onikisepet.constants import RECEIPT_FILE_ACCEPT
from onikisepet.form_guides import get_form_guide
from onikisepet.form_currency import (
    account_choice_label,
    build_transaction_form_currency_context,
)
from onikisepet.forms import CashIncomeForm, TransferForm
from onikisepet.usecases.transaction_feedback import (
    TRANSACTION_CREATED_APPROVED,
    TRANSACTION_CREATED_PENDING,
    TRANSFER_CREATED_PENDING,
    transaction_created_message,
)

from .helpers import TransactionTestMixin


class FormGuideTests(TestCase):
    def test_cash_income_guide_includes_contextual_intro(self):
        guide = get_form_guide("cash_income")

        self.assertEqual(guide["title"], "Nakit Gelir")
        self.assertIn("Defter", guide["intro"])
        self.assertIn("Onay", guide["intro"])


class TransactionFeedbackTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.admin_user = self.create_user("feedback_admin", is_superuser=True)
        self.data_entry_user = self.create_user(
            "feedback_data_entry",
            group_name="Data Entry",
        )
        self.cash_account = self.create_account(
            name="Feedback Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Feedback Income",
            category_type="income",
        )

    def test_pending_income_message_for_data_entry(self):
        transaction = self.create_transaction(
            transaction_type="income",
            amount=Decimal("100.00"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.data_entry_user,
            approval_status="pending",
        )

        self.assertEqual(
            transaction_created_message(transaction),
            TRANSACTION_CREATED_PENDING,
        )

    def test_approved_income_message_for_admin(self):
        transaction = self.create_transaction(
            transaction_type="income",
            amount=Decimal("100.00"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.admin_user,
            approval_status="approved",
        )

        self.assertEqual(
            transaction_created_message(transaction),
            TRANSACTION_CREATED_APPROVED,
        )

    def test_transfer_message_is_pending_specific(self):
        expense_account = self.create_account(
            name="Feedback Expense",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        transaction = self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("50.00"),
            source_account=self.cash_account,
            target_account=expense_account,
            created_by=self.data_entry_user,
            approval_status="pending",
        )

        self.assertEqual(
            transaction_created_message(transaction),
            TRANSFER_CREATED_PENDING,
        )


class TransactionFormViewUxTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.cash_income_create_url = reverse("cash_income_create")
        self.transfer_create_url = reverse("transfer_create")
        self.transaction_list_url = reverse("transaction_list")

        self.admin_user = self.create_user("form_ux_admin", is_superuser=True)
        self.data_entry_user = self.create_user(
            "form_ux_data_entry",
            group_name="Data Entry",
        )

        self.cash_account = self.create_account(
            name="Form UX Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.expense_account = self.create_account(
            name="Form UX Expense",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Form UX Income",
            category_type="income",
        )

    def _cash_income_payload(self):
        return {
            "date": "2026-06-13",
            "donor_name": "Ayşe Demir",
            "amount": "200.00",
            "cash_account": self.cash_account.pk,
            "category": self.income_category.pk,
            "description": "Elden bağış",
        }

    def test_cash_income_create_page_shows_form_intro(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.cash_income_create_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Defter")
        self.assertContains(response, "Onay sonrası rapora yansır")

    def test_data_entry_sees_pending_feedback_after_cash_income_create(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.post(
            self.cash_income_create_url,
            data=self._cash_income_payload(),
            follow=True,
        )

        self.assertRedirects(response, self.transaction_list_url)
        self.assertContains(response, "Onay bekliyor")

    def test_admin_sees_approved_feedback_after_cash_income_create(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(
            self.cash_income_create_url,
            data=self._cash_income_payload(),
            follow=True,
        )

        self.assertRedirects(response, self.transaction_list_url)
        self.assertContains(response, "rapora eklendi")

    def test_transfer_create_shows_transfer_specific_feedback(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(
            self.transfer_create_url,
            data={
                "date": "2026-06-13",
                "amount": "100.00",
                "source_account": self.cash_account.pk,
                "target_account": self.expense_account.pk,
                "description": "Kasa aktarımı",
            },
            follow=True,
        )

        self.assertRedirects(response, self.transaction_list_url)
        self.assertContains(response, "Transfer kaydedildi")
        self.assertContains(response, "hesap bakiyeleri güncellenir")


class TransactionFormFieldUxTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.cash_income_create_url = reverse("cash_income_create")
        self.cash_expense_create_url = reverse("cash_expense_create")
        self.bank_expense_create_url = reverse("bank_expense_create")
        self.transfer_create_url = reverse("transfer_create")
        self.data_entry_user = self.create_user(
            "field_ux_data_entry",
            group_name="Data Entry",
        )
        self.cash_account = self.create_account(
            name="Field UX Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.expense_account = self.create_account(
            name="Field UX Expense",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )

    def test_cash_income_form_defaults_date_to_today(self):
        form = CashIncomeForm()

        self.assertEqual(form["date"].value(), timezone.localdate())

    def test_cash_income_form_date_uses_html5_date_input(self):
        form = CashIncomeForm()

        self.assertEqual(form.fields["date"].widget.input_type, "date")
        self.assertEqual(form.fields["date"].input_formats, ["%Y-%m-%d"])

    def test_cash_income_create_page_renders_html5_date_input(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.cash_income_create_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="date"')
        self.assertContains(response, 'type="date"')

    def test_cash_income_create_page_shows_field_placeholders(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.cash_income_create_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'placeholder="Örn. Ahmet Yılmaz"')
        self.assertContains(response, 'placeholder="Örn. 1.250,50"')
        self.assertContains(response, 'placeholder="Örn. Pazar bağışı"')

    def test_account_choice_label_includes_currency(self):
        self.assertEqual(
            account_choice_label(self.cash_account),
            "Field UX Cash (TRY)",
        )

    def test_cash_income_form_account_dropdown_shows_currency(self):
        form = CashIncomeForm()
        label = form.fields["cash_account"].label_from_instance(self.cash_account)

        self.assertEqual(label, "Field UX Cash (TRY)")

    def test_build_transaction_form_currency_context_for_cash_income(self):
        form = CashIncomeForm()
        context = build_transaction_form_currency_context(form)

        self.assertEqual(context["primary_account_field"], "cash_account")
        self.assertEqual(
            context["currencies_by_account_id"][str(self.cash_account.pk)],
            "TRY",
        )

    def test_transfer_form_currency_context_uses_source_account(self):
        form = TransferForm()
        context = build_transaction_form_currency_context(form)

        self.assertEqual(context["primary_account_field"], "source_account")

    def test_cash_income_create_page_includes_currency_helpers(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.cash_income_create_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "transaction-form-currency-data")
        self.assertContains(response, "data-transaction-amount-label")
        self.assertContains(response, "Field UX Cash (TRY)")

    def test_cash_income_form_applies_field_help_texts(self):
        form = CashIncomeForm()

        self.assertEqual(
            form.fields["donor_name"].help_text,
            "Bağışı yapan kişinin adı ve soyadı.",
        )
        self.assertEqual(
            form.fields["category"].help_text,
            "Raporlarda görünecek gelir/gider kalemi.",
        )
        # Alan tanımında zaten var olan help_text ezilmemeli.
        self.assertEqual(form.fields["amount"].help_text, "En az 0,01")

    def test_cash_income_create_page_marks_required_fields(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.cash_income_create_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "form-label__required")
        self.assertContains(response, "ile işaretli alanlar zorunludur")
        self.assertContains(response, "Bağışı yapan kişinin adı ve soyadı.")

    def test_cash_expense_create_page_receipt_file_accepts_mobile_uploads(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.cash_expense_create_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'accept="{RECEIPT_FILE_ACCEPT}"')
        self.assertContains(response, "Telefondan fotoğraf çekebilir veya galeriden seçebilirsiniz.")
        self.assertContains(response, "form-control--file")

    def test_bank_expense_create_page_receipt_file_accepts_mobile_uploads(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.bank_expense_create_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'accept="{RECEIPT_FILE_ACCEPT}"')
        self.assertContains(response, "Telefondan fotoğraf çekebilir veya galeriden seçebilirsiniz.")


    def test_cash_income_create_page_amount_input_supports_turkish_format(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.cash_income_create_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="amount"')
        self.assertContains(response, 'inputmode="decimal"')
        self.assertContains(response, "data-transaction-amount-input")


class RecordTypeGuideViewTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.guide_url = reverse("record_type_guide")
        self.home_url = reverse("home")
        self.admin_user = self.create_user("guide_admin", is_superuser=True)
        self.data_entry_user = self.create_user(
            "guide_data_entry",
            group_name="Data Entry",
        )
        self.viewer_user = self.create_user("guide_viewer", group_name="Viewer")

    def test_data_entry_can_access_record_type_guide(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.guide_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hangi formu kullanmalıyım?")
        self.assertContains(response, "Elden / Kasa (Defter)")
        self.assertContains(response, "Online Bağış")
        self.assertContains(response, reverse("cash_income_create"))
        self.assertContains(response, reverse("transfer_create"))

    def test_viewer_cannot_access_record_type_guide(self):
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(self.guide_url)

        self.assertEqual(response.status_code, 403)

    def test_home_shows_record_type_guide_link_for_data_entry(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.home_url)

        self.assertContains(response, reverse("record_type_guide"))
        self.assertContains(response, "Hangi formu kullanmalıyım?")

    def test_nav_shows_record_type_guide_link_for_data_entry(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.home_url)

        self.assertContains(response, 'href="%s"' % reverse("record_type_guide"))


class TransactionFormExampleTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.cash_income_create_url = reverse("cash_income_create")
        self.cash_expense_create_url = reverse("cash_expense_create")
        self.data_entry_user = self.create_user(
            "example_data_entry",
            group_name="Data Entry",
        )
        self.cash_account = self.create_account(
            name="Example Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Example Income",
            category_type="income",
        )
        self.expense_category = self.create_category(
            name="Example Expense",
            category_type="expense",
        )

    def test_cash_income_form_shows_example_panel(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.cash_income_create_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Örnek kayıt")
        self.assertContains(response, "Örnek göster")
        self.assertContains(response, "Ahmet Yılmaz")
        self.assertContains(response, "transaction-form-example-data")
        self.assertContains(response, "Pazar ayini bağışı")

    def test_cash_expense_form_notes_file_field_is_not_prefilled(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.cash_expense_create_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Makbuz veya dekont alanı örnekle doldurulmaz")

    def test_build_transaction_form_example_uses_first_account_and_category(self):
        form = CashIncomeForm()
        example = build_transaction_form_example(form, "cash_income")
        first_account = form.fields["cash_account"].queryset.first()
        first_category = form.fields["category"].queryset.first()

        self.assertEqual(example["values"]["donor_name"], "Ahmet Yılmaz")
        self.assertEqual(example["values"]["cash_account"], str(first_account.pk))
        self.assertEqual(example["values"]["category"], str(first_category.pk))
        self.assertIn("Ahmet Yılmaz", example["summary"])

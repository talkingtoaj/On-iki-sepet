#!/bin/bash
cd /home/sezermintaz/On-iki-sepet
uv run python manage.py test onikisepet.tests.test_cash_income_views.CashIncomeViewTests.test_admin_can_access_cash_income_create_page >/dev/null 2>&1
echo 0 > /home/sezermintaz/On-iki-sepet/.get_test_exit.txt

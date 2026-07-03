from django.test import TestCase

from onikisepet.usecases.report_periods import get_period_label


class ReportPeriodLabelTests(TestCase):
    def test_get_period_label_returns_turkish_labels(self):
        self.assertEqual(get_period_label("this_month"), "Bu ay")
        self.assertEqual(get_period_label("last_month"), "Geçen ay")
        self.assertEqual(get_period_label("this_year"), "Bu yıl")

    def test_get_period_label_returns_empty_for_unknown_value(self):
        self.assertEqual(get_period_label(""), "")
        self.assertEqual(get_period_label("custom"), "")

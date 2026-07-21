from django import template

from onikisepet.usecases import bank_import as bank_import_ops

register = template.Library()


@register.filter
def workflow_status(row):
    return bank_import_ops.get_row_workflow_status(row)

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse

from onikisepet import messages as msg

from .permissions import can_access_application, can_manage_users


def application_access_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not can_access_application(request.user):
            return redirect(reverse("pending_access"))
        return view_func(request, *args, **kwargs)

    return _wrapped


def superuser_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not can_manage_users(request.user):
            return HttpResponseForbidden(msg.PERMISSION_MANAGE_USERS)
        return view_func(request, *args, **kwargs)

    return _wrapped

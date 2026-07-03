from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from onikisepet.decorators import superuser_required
from onikisepet.permissions import can_access_application
from onikisepet.user_forms import UserCreateForm, UserUpdateForm

User = get_user_model()


def _show_password_reset_panel(request, form):
    if request.method != "POST":
        return False
    if request.POST.get("password_reset_enabled") == "1":
        return True
    if request.POST.get("new_password1") or request.POST.get("new_password2"):
        return True
    if form.non_field_errors():
        return True
    if form.errors.get("new_password1") or form.errors.get("new_password2"):
        return True
    return False


@login_required
def pending_access(request):
    if can_access_application(request.user):
        return redirect("home")
    return render(request, "onikisepet/pending_access.html")


@superuser_required
def user_list(request):
    users = (
        User.objects.filter(is_superuser=False)
        .prefetch_related("groups")
        .order_by("username")
    )
    return render(
        request,
        "onikisepet/user_list.html",
        {"users": users},
    )


@superuser_required
def user_create(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("user_list")
    else:
        form = UserCreateForm()

    return render(
        request,
        "onikisepet/user_form.html",
        {
            "form": form,
            "page_title": "Kullanıcı oluştur",
            "submit_label": "Oluştur",
        },
    )


@superuser_required
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk, is_superuser=False)
    if request.method == "POST":
        form = UserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect("user_list")
    else:
        form = UserUpdateForm(instance=user)

    return render(
        request,
        "onikisepet/user_form.html",
        {
            "form": form,
            "page_title": f"Kullanıcı düzenle: {user.username}",
            "submit_label": "Kaydet",
            "edited_user": user,
            "show_password_reset": _show_password_reset_panel(request, form),
        },
    )

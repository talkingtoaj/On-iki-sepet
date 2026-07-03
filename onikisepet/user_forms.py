from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django import forms

from onikisepet.forms import StyledFormMixin
from onikisepet.permissions import APPROVER_GROUP, DATA_ENTRY_GROUP, VIEWER_GROUP
from onikisepet.usecases.profile_sync import sync_user_profile_from_groups

User = get_user_model()

APPLICATION_GROUPS = (DATA_ENTRY_GROUP, VIEWER_GROUP, APPROVER_GROUP)


def application_group_queryset():
    return Group.objects.filter(name__in=APPLICATION_GROUPS).order_by("name")


class UserCreateForm(StyledFormMixin, forms.ModelForm):
    password1 = forms.CharField(
        label="Şifre",
        widget=forms.PasswordInput,
        strip=False,
    )
    password2 = forms.CharField(
        label="Şifre (tekrar)",
        widget=forms.PasswordInput,
        strip=False,
    )
    groups = forms.ModelMultipleChoiceField(
        label="Gruplar",
        queryset=Group.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["groups"].queryset = application_group_queryset()

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Şifreler eşleşmiyor.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            user.groups.set(self.cleaned_data.get("groups", []))
            sync_user_profile_from_groups(user)
        return user


class UserUpdateForm(StyledFormMixin, forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(
        label="Gruplar",
        queryset=Group.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    new_password1 = forms.CharField(
        label="Yeni şifre",
        widget=forms.PasswordInput,
        required=False,
        strip=False,
    )
    new_password2 = forms.CharField(
        label="Yeni şifre (tekrar)",
        widget=forms.PasswordInput,
        required=False,
        strip=False,
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["groups"].queryset = application_group_queryset()
        if self.instance.pk:
            self.fields["groups"].initial = self.instance.groups.all()

    def clean(self):
        cleaned_data = super().clean()
        if self.data.get("password_reset_enabled") != "1":
            cleaned_data["new_password1"] = ""
            cleaned_data["new_password2"] = ""
            return cleaned_data

        password1 = cleaned_data.get("new_password1")
        password2 = cleaned_data.get("new_password2")
        if password1 or password2:
            if password1 != password2:
                raise forms.ValidationError("Yeni şifreler eşleşmiyor.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=commit)
        user.groups.set(self.cleaned_data.get("groups", []))
        sync_user_profile_from_groups(user)
        new_password = self.cleaned_data.get("new_password1")
        if new_password:
            user.set_password(new_password)
            user.save(update_fields=["password"])
        return user

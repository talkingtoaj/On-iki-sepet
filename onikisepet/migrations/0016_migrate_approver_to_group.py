from django.db import migrations, models

APPROVER_GROUP = "Approver"
DATA_ENTRY_GROUP = "Data Entry"


def migrate_approver_profiles_to_group(apps, schema_editor):
    Profile = apps.get_model("onikisepet", "Profile")
    Group = apps.get_model("auth", "Group")

    approver_profiles = Profile.objects.filter(role="approver").select_related("user")
    if not approver_profiles.exists():
        return

    approver_group, _ = Group.objects.get_or_create(name=APPROVER_GROUP)
    data_entry_group, _ = Group.objects.get_or_create(name=DATA_ENTRY_GROUP)

    for profile in approver_profiles:
        profile.role = "data_entry"
        profile.save(update_fields=["role"])
        user = profile.user
        user.groups.add(approver_group)
        if not user.groups.filter(name=DATA_ENTRY_GROUP).exists():
            user.groups.add(data_entry_group)


def reverse_approver_profiles_to_role(apps, schema_editor):
    Profile = apps.get_model("onikisepet", "Profile")
    Group = apps.get_model("auth", "Group")

    approver_group = Group.objects.filter(name=APPROVER_GROUP).first()
    if approver_group is None:
        return

    for user in approver_group.user_set.all():
        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            continue
        if profile.role == "data_entry":
            profile.role = "approver"
            profile.save(update_fields=["role"])


class Migration(migrations.Migration):

    dependencies = [
        ("onikisepet", "0015_transaction_reverses_transaction"),
    ]

    operations = [
        migrations.RunPython(
            migrate_approver_profiles_to_group,
            reverse_approver_profiles_to_role,
        ),
        migrations.AlterField(
            model_name="profile",
            name="role",
            field=models.CharField(
                choices=[
                    ("viewer", "Viewer"),
                    ("data_entry", "Data Entry"),
                ],
                default="viewer",
                max_length=20,
            ),
        ),
    ]

from django.db import migrations, models


def existing_users_are_already_onboarded(apps, schema_editor):
    User = apps.get_model("api", "User")
    User.objects.all().update(onboarding_completed=True, onboarding_step=0)


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0006_superusers_are_administrators"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="preferred_language",
            field=models.CharField(choices=[("en", "English"), ("lg", "Luganda"), ("nyn", "Runyankole"), ("te", "Ateso"), ("sw", "Swahili")], default="en", max_length=8),
        ),
        migrations.AddField(model_name="user", name="farming_method", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="user", name="irrigation_method", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="user", name="farming_experience_years", field=models.PositiveSmallIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="user", name="farming_interests", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name="user", name="farming_goals", field=models.TextField(blank=True)),
        migrations.AddField(model_name="user", name="personalize_assistant", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="user", name="preferred_notifications", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="user", name="onboarding_completed", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="user", name="onboarding_step", field=models.PositiveSmallIntegerField(default=0)),
        migrations.RunPython(existing_users_are_already_onboarded, migrations.RunPython.noop),
    ]

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0008_harvest_offline_idempotency"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="harvestrecord",
            name="unique_recorded_harvest_client_key",
        ),
        migrations.RemoveField(model_name="harvestrecord", name="client_key"),
        migrations.RemoveField(model_name="user", name="preferred_language"),
        migrations.RemoveField(model_name="user", name="farming_method"),
        migrations.RemoveField(model_name="user", name="irrigation_method"),
        migrations.RemoveField(model_name="user", name="farming_experience_years"),
        migrations.RemoveField(model_name="user", name="farming_interests"),
        migrations.RemoveField(model_name="user", name="farming_goals"),
        migrations.RemoveField(model_name="user", name="personalize_assistant"),
        migrations.RemoveField(model_name="user", name="preferred_notifications"),
        migrations.RemoveField(model_name="user", name="onboarding_completed"),
        migrations.RemoveField(model_name="user", name="onboarding_step"),
    ]

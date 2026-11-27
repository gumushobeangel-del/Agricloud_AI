import django.db.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0007_farmer_preferences_and_onboarding"),
    ]

    operations = [
        migrations.AddField(
            model_name="harvestrecord",
            name="client_key",
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.AddConstraint(
            model_name="harvestrecord",
            constraint=models.UniqueConstraint(condition=django.db.models.Q(client_key__isnull=False), fields=("recorded_by", "client_key"), name="unique_recorded_harvest_client_key"),
        ),
    ]

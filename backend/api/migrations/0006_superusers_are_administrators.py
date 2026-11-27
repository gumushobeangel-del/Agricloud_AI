from django.db import migrations


def promote_superusers(apps, schema_editor):
    User = apps.get_model("api", "User")
    User.objects.filter(is_superuser=True).update(role="admin", is_staff=True)


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0005_marketprice_cropyieldbenchmark_harvestrecord"),
    ]

    operations = [
        migrations.RunPython(promote_superusers, migrations.RunPython.noop),
    ]

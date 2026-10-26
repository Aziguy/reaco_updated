import re

from django.db import migrations

PREFIX = re.compile(r"^(centre commercial|hypermarch[ée]|supermarch[ée])\s+", re.IGNORECASE)


def normalize(brand):
    brand = PREFIX.sub("", re.sub(r"\.\s+", ".", " ".join(brand.split())))
    if brand.isupper() and len(brand) > 3:
        return brand.title()
    return brand[:1].upper() + brand[1:]


def forwards(apps, schema_editor):
    Store = apps.get_model("pricing", "Store")
    for store in Store.objects.exclude(brand=""):
        brand = normalize(store.brand)
        if brand != store.brand:
            Store.objects.filter(pk=store.pk).update(brand=brand)


class Migration(migrations.Migration):
    dependencies = [("pricing", "0001_initial")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]

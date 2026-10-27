from django.db import migrations, models

# First matching word of the free text origin wins.
ORIGINS = [
    ("france", "france"), ("maghreb", "maghreb"), ("maroc", "maghreb"), ("liban", "maghreb"),
    ("proche-orient", "maghreb"), ("inde", "india"), ("vietnam", "asia"), ("chine", "asia"),
    ("japon", "asia"), ("thaïlande", "asia"), ("tex-mex", "americas"), ("mexique", "americas"),
    ("états-unis", "americas"), ("amérique", "americas"), ("sénégal", "africa"),
    ("cameroun", "africa"), ("côte d'ivoire", "africa"), ("nigeria", "africa"),
    ("grèce", "europe"), ("italie", "europe"), ("espagne", "europe"), ("europe", "europe"),
]  # fmt: skip


def forwards(apps, schema_editor):
    Recipe = apps.get_model("recipes", "Recipe")
    for recipe in Recipe.objects.filter(cuisine="").exclude(origin=""):
        origin = recipe.origin.lower()
        cuisine = next((value for word, value in ORIGINS if word in origin), "")
        if cuisine:
            Recipe.objects.filter(pk=recipe.pk).update(cuisine=cuisine)


class Migration(migrations.Migration):
    dependencies = [("recipes", "0007_field_labels")]

    operations = [
        migrations.AddField(
            model_name="recipe",
            name="cuisine",
            field=models.CharField(
                blank=True,
                choices=[
                    ("france", "France"),
                    ("europe", "Europe"),
                    ("maghreb", "Maghreb et Moyen-Orient"),
                    ("africa", "Afrique"),
                    ("asia", "Asie"),
                    ("india", "Inde"),
                    ("americas", "Amériques"),
                ],
                max_length=20,
                verbose_name="cuisine",
            ),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]

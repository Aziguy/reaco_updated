from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import PriceObservation, Store


@admin.register(Store)
class StoreAdmin(ModelAdmin):
    list_display = ("name", "brand", "city", "postcode", "country_code")
    list_filter = ("country_code", "brand")
    search_fields = ("name", "brand", "city", "postcode")


@admin.register(PriceObservation)
class PriceObservationAdmin(ModelAdmin):
    list_display = (
        "ingredient",
        "product_name",
        "store",
        "price",
        "unit_price",
        "base_unit",
        "observed_on",
    )
    list_filter = ("base_unit", "is_discounted", "ingredient")
    search_fields = ("product_name", "product_code", "store__name")
    raw_id_fields = ("store",)
    date_hierarchy = "observed_on"

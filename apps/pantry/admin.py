from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import PantryItem


@admin.register(PantryItem)
class PantryItemAdmin(ModelAdmin):
    list_display = ("name", "user", "quantity", "unit", "expires_on", "status")
    list_filter = ("status",)
    search_fields = ("name", "brand", "barcode", "user__email")
    raw_id_fields = ("user", "ingredient")

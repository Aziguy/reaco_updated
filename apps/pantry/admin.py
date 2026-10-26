from django.contrib import admin

from .models import PantryItem


@admin.register(PantryItem)
class PantryItemAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "quantity", "unit", "expires_on", "status")
    list_filter = ("status",)
    search_fields = ("name", "brand", "barcode", "user__email")
    raw_id_fields = ("user", "ingredient")

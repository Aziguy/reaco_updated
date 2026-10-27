from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import ShoppingItem, ShoppingList


class ShoppingItemInline(TabularInline):
    model = ShoppingItem
    raw_id_fields = ("ingredient",)
    exclude = ("recipes",)
    extra = 0


@admin.register(ShoppingList)
class ShoppingListAdmin(ModelAdmin):
    list_display = ("name", "user", "is_archived", "updated_at")
    search_fields = ("name", "user__email")
    raw_id_fields = ("user",)
    inlines = (ShoppingItemInline,)

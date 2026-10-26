from django.contrib import admin

from .models import ShoppingItem, ShoppingList


class ShoppingItemInline(admin.TabularInline):
    model = ShoppingItem
    raw_id_fields = ("ingredient",)
    exclude = ("recipes",)
    extra = 0


@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "is_archived", "updated_at")
    search_fields = ("name", "user__email")
    raw_id_fields = ("user",)
    inlines = (ShoppingItemInline,)

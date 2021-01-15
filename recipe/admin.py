from django.contrib import admin
from django.utils.html import format_html
from . models import Drive, Categorie, Ingredient, Drive_Ingredient, Recipe

# Register your models here.
class DriveAdmin(admin.ModelAdmin):
    def thumbnail(self, object):
        return format_html('<img src="{}" width="40" style="border-radius: 50px;" />'.format(object.image.url))

    thumbnail.short_description = 'Image'
    list_display = ('id', 'thumbnail', 'name', 'address',)
    list_display_links = ('id', 'thumbnail', 'name',)
    search_fields = ('name', 'address',)
    list_filter = ('name',)


class IngredientAdmin(admin.ModelAdmin):
    def thumbnail(self, object):
    	return format_html('<img src="{}" width="40" style="border-radius: 50px;" />'.format(object.image.url))

    thumbnail.short_description = 'Image'
    list_display = ('id', 'thumbnail', 'name', 'created_date',)
    list_display_links = ('id', 'thumbnail', 'name', 'created_date',)
    search_fields = ('name', 'created_date',)
    list_filter = ('name','created_date',)


class RecipeAdmin(admin.ModelAdmin):
    def thumbnail(self, object):
        return format_html('<img src="{}" width="40" style="border-radius: 50px;" />'.format(object.recipe_photo.url))

    thumbnail.short_description = 'Image'
    list_display = ('id', 'thumbnail', 'name', 'diet', 'portion', 'created_date',)
    list_display_links = ('id', 'thumbnail', 'name', 'created_date',)
    search_fields = ('name', 'diet', 'portion')
    list_filter = ('name', 'is_feature', 'cooking_time', 'preparation')


admin.site.register(Drive, DriveAdmin)
admin.site.register(Categorie)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Drive_Ingredient)
admin.site.register(Recipe, RecipeAdmin)
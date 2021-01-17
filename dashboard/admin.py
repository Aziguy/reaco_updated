from django.contrib import admin
from django.utils.html import format_html
from . models import Dashboard

# Register your models here.
class DashboardAdmin(admin.ModelAdmin):
	def thumbnail(self, object):
		return format_html('<img src="{}" width="40" style="border-radius: 50px;" />'.format(object.recipe_photo))
	
	thumbnail.short_description = 'Image'
	list_display = ('id', 'thumbnail', 'first_name', 'last_name', 'recipe_name', 'create_date')
	list_display_links = ('id', 'thumbnail','first_name', 'last_name', 'recipe_name',)
	search_fields = ('first_name', 'last_name', 'recipe_name',)
	list_per_page = 25

admin.site.register(Dashboard, DashboardAdmin)
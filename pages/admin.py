from django.contrib import admin
from django.utils.html import format_html
from . models import Slider, Info, Team, Service, AboutDesc

# Register your models here.

class TeamAdmin(admin.ModelAdmin):
    def thumbnail(self, object):
        return format_html('<img src="{}" width="40" style="border-radius: 50px;" />'.format(object.photo.url))

    thumbnail.short_description = 'Photo'

    list_display = ('id', 'thumbnail', 'first_name', 'job_title', 'created_date')
    list_display_links = ('id', 'thumbnail', 'first_name',)
    search_fields = ('first_name', 'last_name', 'job_title')
    list_filter = ('job_title',)

admin.site.register(Info)
admin.site.register(Slider)
admin.site.register(Team, TeamAdmin)
admin.site.register(Service)
admin.site.register(AboutDesc)
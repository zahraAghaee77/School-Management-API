import mapwidgets
from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin
from django.contrib.gis.db import models as gis_models
from mapwidgets.widgets import GoogleMapPointFieldWidget

from .models import *

# @admin.register(School)
# class SchoolAdmin(admin.ModelAdmin):
#     list_display = ("name", "manager")
#     formfield_overrides = {gis_models.PointField: {"widget": GoogleMapPointFieldWidget}}


# Register your models here.
@admin.register(School)
class ShopAdmin(OSMGeoAdmin):
    list_display = ("name", "location", "manager")


admin.site.register(Class)
admin.site.register(Lesson)

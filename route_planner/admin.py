from django.contrib import admin

from .models import LocationCache, RouteCache, TruckStop


@admin.register(TruckStop)
class TruckStopAdmin(admin.ModelAdmin):
    list_display = ("opis_id", "name", "city", "state", "retail_price", "latitude", "longitude")
    list_filter = ("state",)
    search_fields = ("name", "city", "state", "address", "opis_id")


@admin.register(LocationCache)
class LocationCacheAdmin(admin.ModelAdmin):
    list_display = ("query", "formatted_address", "latitude", "longitude", "created_at")
    search_fields = ("query", "formatted_address")


@admin.register(RouteCache)
class RouteCacheAdmin(admin.ModelAdmin):
    list_display = ("cache_key", "start_label", "finish_label", "distance_miles", "created_at")
    search_fields = ("cache_key", "start_label", "finish_label")

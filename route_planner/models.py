from django.db import models


class TruckStop(models.Model):
    opis_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=16)
    rack_id = models.CharField(max_length=32)
    retail_price = models.DecimalField(max_digits=10, decimal_places=8)
    source_price_count = models.PositiveIntegerField(default=1)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    geocoded_address = models.CharField(max_length=255, blank=True)
    geocode_confidence = models.CharField(max_length=64, blank=True)
    raw_row = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["state", "city", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.city}, {self.state})"


class LocationCache(models.Model):
    query = models.CharField(max_length=255, unique=True)
    formatted_address = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.query


class RouteCache(models.Model):
    cache_key = models.CharField(max_length=64, unique=True)
    start_label = models.CharField(max_length=255)
    finish_label = models.CharField(max_length=255)
    distance_miles = models.FloatField()
    duration_minutes = models.FloatField()
    geometry = models.JSONField(default=list)
    bbox = models.JSONField(default=list, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.start_label} -> {self.finish_label}"

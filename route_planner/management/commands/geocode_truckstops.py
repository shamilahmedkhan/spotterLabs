from django.core.management.base import BaseCommand

from route_planner.models import TruckStop
from route_planner.services.clients import CensusGeocoderClient


class Command(BaseCommand):
    help = "Geocode imported truck stops with the US Census batch geocoder."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Optional limit for geocoding a subset of truck stops.",
        )

    def handle(self, *args, **options):
        queryset = TruckStop.objects.filter(latitude__isnull=True).order_by("id")
        if options["limit"]:
            queryset = queryset[: options["limit"]]
        truck_stops = list(queryset)
        if not truck_stops:
            self.stdout.write(self.style.SUCCESS("No truck stops need geocoding."))
            return

        client = CensusGeocoderClient()
        rows = [
            {
                "id": str(stop.id),
                "address": stop.address,
                "city": stop.city,
                "state": stop.state,
                "zip": "",
            }
            for stop in truck_stops
        ]
        results = client.batch_geocode(rows)

        updated = 0
        for stop in truck_stops:
            geocoded = results.get(str(stop.id))
            if not geocoded:
                continue
            stop.latitude = geocoded.latitude
            stop.longitude = geocoded.longitude
            stop.geocoded_address = geocoded.formatted_address
            stop.geocode_confidence = geocoded.confidence
            updated += 1

        TruckStop.objects.bulk_update(
            truck_stops,
            ["latitude", "longitude", "geocoded_address", "geocode_confidence"],
            batch_size=1000,
        )
        self.stdout.write(self.style.SUCCESS(f"Geocoded {updated} truck stops."))

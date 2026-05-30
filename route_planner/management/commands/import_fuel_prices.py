import csv
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from statistics import median

import geonamescache
from django.core.management.base import BaseCommand, CommandError

from route_planner.models import TruckStop


def canonicalize_row(row: dict[str, str]) -> dict[str, str]:
    canonical: dict[str, str] = {}
    for key, value in row.items():
        normalized_key = key.strip()
        if normalized_key.endswith("OPIS Truckstop ID"):
            normalized_key = "OPIS Truckstop ID"
        canonical[normalized_key] = value
    return canonical


def normalize_text(value: str) -> str:
    return " ".join(value.strip().split()).lower()


def build_city_index() -> dict[tuple[str, str], dict]:
    cache = geonamescache.GeonamesCache()
    index: dict[tuple[str, str], dict] = {}
    for city in cache.get_cities().values():
        if city.get("countrycode") != "US":
            continue
        key = (normalize_text(city["name"]), city["admin1code"].upper())
        current = index.get(key)
        if current is None or int(city.get("population") or 0) > int(current.get("population") or 0):
            index[key] = city
    return index


class Command(BaseCommand):
    help = "Import and normalize the provided fuel price CSV."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="fuel-prices-for-be-assessment.csv",
            help="Path to the CSV file.",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"])
        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        grouped: dict[str, dict] = {}
        prices_by_station: dict[str, list[float]] = defaultdict(list)
        city_index = build_city_index()

        with file_path.open(newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                normalized_row = canonicalize_row(row)
                opis_id = normalized_row["OPIS Truckstop ID"].strip()
                grouped.setdefault(opis_id, normalized_row)
                prices_by_station[opis_id].append(float(normalized_row["Retail Price"]))

        TruckStop.objects.all().delete()
        records = []
        matched_cities = 0
        for opis_id, row in grouped.items():
            city_key = (normalize_text(row["City"]), row["State"].upper())
            city_match = city_index.get(city_key)
            if city_match:
                matched_cities += 1
            records.append(
                TruckStop(
                    opis_id=int(opis_id),
                    name=row["Truckstop Name"].strip(),
                    address=row["Address"].strip(),
                    city=row["City"].strip(),
                    state=row["State"].strip(),
                    rack_id=row["Rack ID"].strip(),
                    retail_price=Decimal(str(median(prices_by_station[opis_id]))),
                    source_price_count=len(prices_by_station[opis_id]),
                    latitude=city_match["latitude"] if city_match else None,
                    longitude=city_match["longitude"] if city_match else None,
                    geocoded_address=f'{row["City"].strip()}, {row["State"].strip()}' if city_match else "",
                    geocode_confidence="city-centroid" if city_match else "",
                    raw_row=row,
                )
            )

        TruckStop.objects.bulk_create(records, batch_size=1000)
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(records)} normalized truck stops from {file_path.name}. "
                f"Assigned city-centroid coordinates to {matched_cities} records."
            )
        )

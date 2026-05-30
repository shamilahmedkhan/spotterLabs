import csv
import io
from dataclasses import dataclass

import requests
from django.conf import settings

from route_planner.exceptions import ExternalServiceError


@dataclass
class GeocodedPoint:
    latitude: float
    longitude: float
    formatted_address: str
    confidence: str = ""
    raw_payload: dict | list | None = None


@dataclass
class RouteResult:
    distance_miles: float
    duration_minutes: float
    geometry: list[list[float]]
    bbox: list[float]
    raw_payload: dict


class CensusGeocoderClient:
    def __init__(self) -> None:
        self.base_url = settings.CENSUS_GEOCODER["BASE_URL"].rstrip("/")
        self.benchmark = settings.CENSUS_GEOCODER["BENCHMARK"]

    def geocode(self, query: str) -> GeocodedPoint:
        response = requests.get(
            f"{self.base_url}/locations/onelineaddress",
            params={
                "address": query,
                "benchmark": self.benchmark,
                "format": "json",
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        matches = payload.get("result", {}).get("addressMatches", [])
        if not matches:
            raise ExternalServiceError(f"No geocoding match found for '{query}'.")

        match = matches[0]
        coordinates = match["coordinates"]
        return GeocodedPoint(
            latitude=coordinates["y"],
            longitude=coordinates["x"],
            formatted_address=match.get("matchedAddress", query),
            confidence=match.get("matchType", ""),
            raw_payload=payload,
        )

    def batch_geocode(self, rows: list[dict]) -> dict[str, GeocodedPoint]:
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        for row in rows:
            writer.writerow(
                [
                    row["id"],
                    row["address"],
                    row["city"],
                    row["state"],
                    row.get("zip", ""),
                ]
            )

        response = requests.post(
            f"{self.base_url}/locations/addressbatch",
            files={"addressFile": ("truckstops.csv", buffer.getvalue(), "text/csv")},
            data={
                "benchmark": self.benchmark,
                "format": "csv",
            },
            timeout=120,
        )
        response.raise_for_status()

        results: dict[str, GeocodedPoint] = {}
        reader = csv.reader(io.StringIO(response.text))
        for item in reader:
            if len(item) < 7:
                continue
            row_id = item[0]
            matched_address = item[4]
            lon = item[5]
            lat = item[6]
            if not lon or not lat:
                continue
            results[row_id] = GeocodedPoint(
                latitude=float(lat),
                longitude=float(lon),
                formatted_address=matched_address,
                confidence=item[3] if len(item) > 3 else "",
                raw_payload={"row": item},
            )
        return results


class NominatimGeocoderClient:
    def __init__(self) -> None:
        self.base_url = settings.NOMINATIM["BASE_URL"].rstrip("/")
        self.user_agent = settings.NOMINATIM["USER_AGENT"]

    def geocode(self, query: str) -> GeocodedPoint:
        response = requests.get(
            f"{self.base_url}/search",
            params={
                "q": query,
                "format": "jsonv2",
                "limit": 1,
                "countrycodes": "us",
            },
            headers={"User-Agent": self.user_agent},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload:
            raise ExternalServiceError(f"No geocoding match found for '{query}'.")

        match = payload[0]
        return GeocodedPoint(
            latitude=float(match["lat"]),
            longitude=float(match["lon"]),
            formatted_address=match.get("display_name", query),
            confidence=match.get("type", ""),
            raw_payload=payload,
        )


class OpenRouteServiceClient:
    def __init__(self) -> None:
        self.base_url = settings.OPENROUTESERVICE["BASE_URL"].rstrip("/")
        self.api_key = settings.OPENROUTESERVICE["API_KEY"]
        if not self.api_key:
            raise ExternalServiceError("OPENROUTESERVICE_API_KEY is not configured.")

    def get_route(self, start: tuple[float, float], finish: tuple[float, float]) -> RouteResult:
        response = requests.post(
            f"{self.base_url}/v2/directions/driving-car/geojson",
            headers={
                "Authorization": self.api_key,
                "Content-Type": "application/json",
            },
            json={
                "coordinates": [
                    [start[1], start[0]],
                    [finish[1], finish[0]],
                ],
                "instructions": False,
                "preference": "recommended",
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        feature = payload["features"][0]
        summary = feature["properties"]["summary"]
        return RouteResult(
            distance_miles=summary["distance"] / 1609.344,
            duration_minutes=summary["duration"] / 60,
            geometry=feature["geometry"]["coordinates"],
            bbox=payload.get("bbox", []),
            raw_payload=payload,
        )


class OSRMRoutingClient:
    def __init__(self) -> None:
        self.base_url = settings.OSRM["BASE_URL"].rstrip("/")

    def get_route(self, start: tuple[float, float], finish: tuple[float, float]) -> RouteResult:
        response = requests.get(
            (
                f"{self.base_url}/route/v1/driving/"
                f"{start[1]},{start[0]};{finish[1]},{finish[0]}"
            ),
            params={
                "overview": "full",
                "geometries": "geojson",
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        routes = payload.get("routes", [])
        if not routes:
            raise ExternalServiceError("No route could be found for the provided locations.")

        route = routes[0]
        return RouteResult(
            distance_miles=route["distance"] / 1609.344,
            duration_minutes=route["duration"] / 60,
            geometry=route["geometry"]["coordinates"],
            bbox=[],
            raw_payload=payload,
        )


def build_routing_client():
    if settings.OPENROUTESERVICE["API_KEY"]:
        return OpenRouteServiceClient()
    return OSRMRoutingClient()

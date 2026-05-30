import hashlib

from django.conf import settings

from route_planner.exceptions import ExternalServiceError, OptimizationError
from route_planner.models import LocationCache, RouteCache, TruckStop
from route_planner.services.clients import NominatimGeocoderClient, build_routing_client
from route_planner.services.fuel_optimizer import FuelStopCandidate, optimize_fuel_stops
from route_planner.services.geo import (
    expand_bounding_box,
    haversine_miles,
    project_point_onto_route,
    route_bounding_box,
    simplify_route,
)


def normalize_query(query: str) -> str:
    return " ".join(query.strip().lower().split())


class RoutePlannerService:
    def __init__(self) -> None:
        self.geocoder = NominatimGeocoderClient()
        self.routing = build_routing_client()
        self.mpg = settings.FUEL_ROUTING["MPG"]
        self.max_range_miles = settings.FUEL_ROUTING["MAX_RANGE_MILES"]
        self.route_corridor_miles = settings.FUEL_ROUTING["ROUTE_CORRIDOR_MILES"]
        self.origin_search_limit_miles = settings.FUEL_ROUTING["ORIGIN_SEARCH_LIMIT_MILES"]
        self.route_simplify_tolerance_miles = settings.FUEL_ROUTING[
            "ROUTE_SIMPLIFY_TOLERANCE_MILES"
        ]

    def geocode_location(self, query: str) -> LocationCache:
        normalized = normalize_query(query)
        cached = LocationCache.objects.filter(query=normalized).first()
        if cached:
            return cached

        point = self.geocoder.geocode(query)
        return LocationCache.objects.create(
            query=normalized,
            formatted_address=point.formatted_address,
            latitude=point.latitude,
            longitude=point.longitude,
            raw_payload=point.raw_payload or {},
        )

    def get_route(
        self,
        start_label: str,
        finish_label: str,
        start_coords: tuple[float, float],
        finish_coords: tuple[float, float],
    ) -> RouteCache:
        cache_key = hashlib.sha256(
            (
                f"{round(start_coords[0], 5)},{round(start_coords[1], 5)}|"
                f"{round(finish_coords[0], 5)},{round(finish_coords[1], 5)}"
            ).encode("utf-8")
        ).hexdigest()
        cached = RouteCache.objects.filter(cache_key=cache_key).first()
        if cached:
            return cached

        route = self.routing.get_route(start_coords, finish_coords)
        return RouteCache.objects.create(
            cache_key=cache_key,
            start_label=start_label,
            finish_label=finish_label,
            distance_miles=route.distance_miles,
            duration_minutes=route.duration_minutes,
            geometry=route.geometry,
            bbox=route.bbox,
            raw_payload=route.raw_payload,
        )

    def build_plan(self, start: str, finish: str) -> dict:
        if TruckStop.objects.filter(latitude__isnull=False, longitude__isnull=False).count() == 0:
            raise ExternalServiceError(
                "Truck stops have not been geocoded yet. Run the import and geocoding commands first."
            )

        start_location = self.geocode_location(start)
        finish_location = self.geocode_location(finish)
        route = self.get_route(
            start_label=start_location.formatted_address,
            finish_label=finish_location.formatted_address,
            start_coords=(start_location.latitude, start_location.longitude),
            finish_coords=(finish_location.latitude, finish_location.longitude),
        )

        route_points = [(coord[1], coord[0]) for coord in route.geometry]
        simplified_route_points = simplify_route(
            route_points,
            self.route_simplify_tolerance_miles,
        )
        stops = self._load_candidate_stops(route_points)
        if not stops:
            raise ExternalServiceError("No geocoded truck stops are available.")

        origin_stop = self._find_origin_stop(start_location.latitude, start_location.longitude, stops)
        corridor_candidates = self._find_corridor_candidates(simplified_route_points, stops)

        candidate_map: dict[int, FuelStopCandidate] = {origin_stop.station_id: origin_stop}
        for item in corridor_candidates:
            existing = candidate_map.get(item.station_id)
            if existing is None or item.price < existing.price:
                candidate_map[item.station_id] = item

        candidates = list(candidate_map.values())
        if not any(stop.progress_miles >= route.distance_miles - self.max_range_miles for stop in candidates):
            raise OptimizationError("No feasible fuel stop sequence found close enough to the destination.")

        optimization = optimize_fuel_stops(
            stops=candidates,
            total_distance_miles=route.distance_miles,
            mpg=self.mpg,
            max_range_miles=self.max_range_miles,
        )
        return {
            "route": {
                "start": {
                    "label": start_location.formatted_address,
                    "latitude": start_location.latitude,
                    "longitude": start_location.longitude,
                },
                "finish": {
                    "label": finish_location.formatted_address,
                    "latitude": finish_location.latitude,
                    "longitude": finish_location.longitude,
                },
                "distance_miles": round(route.distance_miles, 2),
                "duration_minutes": round(route.duration_minutes, 2),
                "geometry": {
                    "type": "LineString",
                    "coordinates": route.geometry,
                },
                "bbox": route.bbox,
            },
            "fuel_plan": optimization["fuel_stops"],
            "summary": {
                "total_cost_usd": optimization["total_cost"],
                "total_gallons_purchased": optimization["total_gallons"],
                "estimated_mpg": self.mpg,
                "maximum_range_miles": self.max_range_miles,
                "stop_count": len(optimization["fuel_stops"]),
            },
            "assumptions": {
                "pricing_strategy": "Median retail price per OPIS truck stop ID from the provided CSV.",
                "origin_strategy": "The plan uses the nearest truck stop to the origin as the first purchasable fuel point.",
                "route_corridor_miles": self.route_corridor_miles,
                "route_simplify_tolerance_miles": self.route_simplify_tolerance_miles,
                "simplified_route_points": len(simplified_route_points),
                "original_route_points": len(route_points),
            },
        }

    def _load_candidate_stops(self, route_points: list[tuple[float, float]]) -> list[TruckStop]:
        min_lat, max_lat, min_lon, max_lon = expand_bounding_box(
            route_bounding_box(route_points),
            self.route_corridor_miles,
        )
        return list(
            TruckStop.objects.filter(
                latitude__isnull=False,
                longitude__isnull=False,
                latitude__range=(min_lat, max_lat),
                longitude__range=(min_lon, max_lon),
            )
        )

    def _find_origin_stop(
        self,
        start_lat: float,
        start_lon: float,
        stops: list[TruckStop],
    ) -> FuelStopCandidate:
        nearest = min(
            stops,
            key=lambda item: haversine_miles(start_lat, start_lon, item.latitude, item.longitude),
        )
        distance = haversine_miles(start_lat, start_lon, nearest.latitude, nearest.longitude)
        return FuelStopCandidate(
            station_id=nearest.opis_id,
            name=nearest.name,
            city=nearest.city,
            state=nearest.state,
            address=nearest.address,
            latitude=nearest.latitude,
            longitude=nearest.longitude,
            price=float(nearest.retail_price),
            progress_miles=0.0,
            corridor_distance_miles=distance,
            is_origin_stop=True,
        )

    def _find_corridor_candidates(
        self,
        route_points: list[tuple[float, float]],
        stops: list[TruckStop],
    ) -> list[FuelStopCandidate]:
        candidates: list[FuelStopCandidate] = []
        for stop in stops:
            projection = project_point_onto_route(stop.latitude, stop.longitude, route_points)
            if projection.corridor_distance_miles > self.route_corridor_miles:
                continue
            candidates.append(
                FuelStopCandidate(
                    station_id=stop.opis_id,
                    name=stop.name,
                    city=stop.city,
                    state=stop.state,
                    address=stop.address,
                    latitude=stop.latitude,
                    longitude=stop.longitude,
                    price=float(stop.retail_price),
                    progress_miles=projection.progress_miles,
                    corridor_distance_miles=projection.corridor_distance_miles,
                )
            )
        return candidates
